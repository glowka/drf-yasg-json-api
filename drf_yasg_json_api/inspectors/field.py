import logging
import warnings

from collections import OrderedDict

from django.db import models
from drf_yasg import inspectors
from drf_yasg import openapi
from drf_yasg.inspectors.field import get_model_field
from drf_yasg.inspectors.field import get_parent_serializer
from drf_yasg.utils import filter_none
from rest_framework import relations
from rest_framework import serializers
from rest_framework.serializers import BaseSerializer
from rest_framework.settings import api_settings
from rest_framework_json_api import serializers as dja_serializers
from rest_framework_json_api import utils as json_api_utils
from rest_framework_json_api.utils import format_value
from rest_framework_json_api.utils import get_resource_name
from rest_framework_json_api.utils import get_resource_type_from_model
from rest_framework_json_api.utils import get_resource_type_from_serializer

from drf_yasg_json_api.deprecation import DrfYasgJsonApiDeprecationWarning
from drf_yasg_json_api.utils import get_field_by_source
from drf_yasg_json_api.utils import get_field_related_model
from drf_yasg_json_api.utils import get_serializer_model_primary_key
from drf_yasg_json_api.utils import is_json_api
from drf_yasg_json_api.utils import is_json_api_request
from drf_yasg_json_api.utils import is_json_api_response
from drf_yasg_json_api.utils import is_many_related_field

logger = logging.getLogger(__name__)

__all__ = [
    'InlineSerializerInspector',
    'InlineSerializerSmartInspector',
    'JSONAPISerializerInspector',
    'JSONAPISerializerSmartInspector',
    'IntegerPrimaryKeyRelatedFieldInspector',
    'IntegerIDFieldInspector',
    'ManyRelatedFieldInspector',
    'NamesFormatFilter',
    'XPropertiesFilter'
]


class JSONAPIDeclarationError(ValueError):
    pass


class JSONAPISerializerInspector(inspectors.InlineSerializerInspector):
    strip_read_fields_from_request = False
    strip_write_fields_from_response = False
    handle_json_api_only = True

    def get_schema(self, serializer):
        return self.probe_field_inspectors(serializer, openapi.Schema, self.use_definitions, is_request=False)

    def get_request_schema(self, serializer):
        return self.probe_field_inspectors(serializer, openapi.Schema, self.use_definitions, is_request=True)

    def get_included_schema(self, serializer):
        return self.probe_field_inspectors(serializer, openapi.Schema, self.use_definitions, included=True)

    def field_to_swagger_object(self, field, swagger_object_type, use_references, included=False, is_request=None,
                                **kwargs):
        if not self.is_json_api_root_serializer(field, is_request):
            if self.handle_json_api_only:
                return inspectors.NotHandled
            else:
                return super().field_to_swagger_object(field, swagger_object_type, use_references, **kwargs)

        if is_request is None and included:
            is_request = False

        if included:
            resource_name = get_resource_type_from_serializer(field)
        else:
            resource_name = get_resource_name(context={'view': self.view})

        SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, use_references, **kwargs)
        return self.build_serializer_schema(field, resource_name, SwaggerType, ChildSwaggerType, use_references,
                                            is_request)

    def build_serializer_schema(self, serializer, resource_name, SwaggerType, ChildSwaggerType, use_references,
                                is_request=None):
        fields = json_api_utils.get_serializer_fields(serializer)
        is_post = self.method.lower() == 'post'

        id_field = self.extract_id_field(fields, serializer)
        if id_field is None and not (is_request and is_post):
            logging.warning('{view}.{serializer} does not contain id field as every resource should'.format(
                view=self.view.__class__.__name__, serializer=serializer.__class__.__name__
            ))

        attributes, req_attrs = self.extract_attributes(id_field, fields, ChildSwaggerType, use_references, is_request)
        relationships, req_rels = self.extract_relationships(fields, ChildSwaggerType, use_references, is_request)
        links = self.extract_links(fields, ChildSwaggerType, use_references) if not is_request else None

        schema_fields = filter_none(OrderedDict(
            type=self.build_type_schema(resource_name),
            id=self.probe_field_inspectors(id_field, ChildSwaggerType, use_references)
            if id_field and not (self.strip_read_fields_from_request and is_request and is_post) else None,
            attributes=openapi.Schema(type=openapi.TYPE_OBJECT, properties=attributes, required=req_attrs)
            if attributes else None,
            relationships=openapi.Schema(type=openapi.TYPE_OBJECT, properties=relationships, required=req_rels)
            if relationships else None,
            links=openapi.Schema(type=openapi.TYPE_OBJECT, properties=links)
            if links else None
        ))

        required_properties = None
        if self.is_request_or_unknown(is_request):
            required_properties = filter_none([
                'type',
                'id' if 'id' in schema_fields else None,
                'attributes' if req_attrs else None,
                'relationships' if req_rels else None,
            ])

        return SwaggerType(
            type=openapi.TYPE_OBJECT,
            properties=schema_fields,
            required=required_properties
        )

    def build_type_schema(self, resource_name, read_only=None):
        return openapi.Schema(**filter_none(OrderedDict(
            type=openapi.TYPE_STRING, pattern=resource_name, read_only=read_only or None
        )))

    def extract_id_field(self, fields, serializer: serializers.Serializer):
        # Included in fields and explicitly named "id"
        if 'id' in fields:
            serializer_id = fields['id']
            model_pk = get_serializer_model_primary_key(serializer)
            if model_pk and model_pk.name != 'id' and get_field_by_source(fields.values(), model_pk.name):
                raise JSONAPIDeclarationError('if serializer includes primary key it cannot define other field as id')
            return serializer_id

        if not isinstance(serializer, serializers.ModelSerializer):
            return None

        # Included in fields, but not as "id", find by model primary key
        model_pk = get_serializer_model_primary_key(serializer)
        serializer_id = get_field_by_source(fields.values(), model_pk.name)
        if serializer_id:
            return serializer_id

        # Not included in fields, create "temporary" field based on model primary key
        id_field_class, id_field_kwargs = serializer.build_standard_field('id', model_pk)
        serializer_id: serializers.Field = id_field_class(**id_field_kwargs,
                                                          source=model_pk.name if model_pk.name != 'id' else None)
        # NOTE: emulating binding, this is one-way binding
        # This field is safe to use and pass anywhere, but it won't be visible from serializer
        serializer_id.bind('id', serializer)
        return serializer_id

    def extract_attributes(self, id_field, fields, ChildSwaggerType, use_references, is_request=None):
        attrs = {}
        required_attrs = []
        for field_name, field in fields.items():
            if self.should_strip_from_schema(field, is_request):
                continue
            # ID is always provided in the root of JSON API so remove it from attributes
            if id_field and field_name == id_field.field_name:
                continue
            # Skip fields with relations
            if isinstance(field, (relations.RelatedField, relations.ManyRelatedField, BaseSerializer)):
                continue

            attrs[field_name] = self.probe_field_inspectors(field, ChildSwaggerType, use_references)
            if self.is_request_or_unknown(is_request) and field.required and not field.read_only:
                required_attrs.append(field_name)
        return attrs, (required_attrs or None)

    def extract_relationships(self, fields, ChildSwaggerType, use_references, is_request=None):
        relationships = OrderedDict()
        required_relationships = []
        for field_name, field in fields.items():
            self.maybe_fix_broken_parent_relation(field)

            if self.should_strip_from_schema(field, is_request):
                continue
            # Self url field
            if field_name == api_settings.URL_FIELD_NAME:
                continue
            # Skip fields without relations
            if not isinstance(field, (relations.RelatedField, relations.ManyRelatedField, serializers.Serializer)):
                continue

            # Produce swagger output
            relation_data_schema = openapi.Schema(**filter_none(OrderedDict(
                type=openapi.TYPE_OBJECT,
                properties=OrderedDict(
                    id=self.probe_field_inspectors(field, ChildSwaggerType, use_references),
                    type=self.build_type_schema(
                        self.get_resource_name_from_related_id_field(field_name, field),
                        read_only=field.read_only
                    ),
                ),
                required=['id', 'type'] if (self.is_request_or_unknown(is_request)) and not field.read_only else None,
            )))

            if is_many_related_field(field):
                relation_data_schema = openapi.Schema(type=openapi.TYPE_ARRAY, items=relation_data_schema)

            relation_links_schema = self.get_links_from_id_field(field_name, field)
            if relation_links_schema:
                relation_links_schema = openapi.Schema(type=openapi.TYPE_OBJECT, properties=relation_links_schema)

            is_relation_required = self.is_request_or_unknown(is_request) and field.required and not field.read_only

            relationships[field_name] = openapi.Schema(**filter_none(OrderedDict(
                type=openapi.TYPE_OBJECT,
                properties=filter_none({
                    'data': relation_data_schema,
                    'links': relation_links_schema if self.not_request_or_unknown(is_request) else None
                }),
                required=['data'] if is_relation_required else None,
                read_only=field.read_only or None,
                x_read_only=field.read_only or None,
            )))
            if is_relation_required:
                required_relationships.append(field_name)

        return relationships, (required_relationships or None)

    def extract_links(self, fields, ChildSwaggerType, use_references):
        self_field_name = api_settings.URL_FIELD_NAME

        return filter_none(OrderedDict(
            self=openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)
            if self_field_name in fields and isinstance(fields[self_field_name], serializers.RelatedField) else None
        ))

    def get_resource_name_from_related_id_field(self, field_name, id_field):
        # Unpack ManyRelatedField from many wrapper
        id_field = getattr(id_field, 'child_relation', None) or id_field

        # Not very frequent case but different from others
        if isinstance(id_field, serializers.Serializer):
            return json_api_utils.get_resource_type_from_serializer(id_field)
        # Most cases
        else:
            # Try to get from included serializers
            parent_serializer = get_parent_serializer(id_field)
            if isinstance(id_field, dja_serializers.ResourceRelatedField):
                resource_name = id_field.get_resource_type_from_included_serializer()
                if resource_name:
                    return resource_name

            related_model = get_field_related_model(id_field)
            if related_model:
                return get_resource_type_from_model(related_model)

        raise ValueError(f"Unable to extract resource name for {parent_serializer}.{field_name} serializer field")

    def get_links_from_id_field(self, field_name, id_field):
        links = OrderedDict()
        if isinstance(id_field, dja_serializers.ResourceRelatedField):
            if id_field.related_link_lookup_field is not None:
                links['related'] = openapi.Schema(type=openapi.TYPE_STRING, pattern=openapi.FORMAT_URI, read_only=True)
            if id_field.self_link_view_name is not None:
                links['self'] = openapi.Schema(type=openapi.TYPE_STRING, pattern=openapi.FORMAT_URI, read_only=True)
        return links or None

    def is_json_api_root_serializer(self, field, is_request=False):
        return field and field.parent is None and isinstance(field, serializers.Serializer) and (
            (not is_request and is_json_api_response(self.view.renderer_classes))
            or ((is_request or is_request is None) and is_json_api_request(self.view.parser_classes))
        )

    def should_strip_from_schema(self, field, is_request):
        return (self.strip_read_fields_from_request and is_request and field.read_only) or \
               (self.strip_write_fields_from_response and is_request is False and field.write_only)

    def not_request_or_unknown(self, is_request):
        # evaluate None to True as well
        return not is_request

    def is_request_or_unknown(self, is_request):
        # evaluate None to True as well
        return is_request is None or is_request

    def maybe_fix_broken_parent_relation(self, candidate_field):
        """
        SerializerMethodResourceRelatedField is a bit hacky and breaks field.parent.parent...serializer chain when used
        with many=True. To avoid multiple exception in random inspectors, we just check every relation if fix is needed.
        """
        child_field = getattr(candidate_field, 'child_relation', None)
        if child_field and not getattr(child_field, 'parent', None):
            setattr(child_field, 'parent', candidate_field)


class JSONAPISerializerSmartInspector(JSONAPISerializerInspector):
    strip_read_fields_from_request = True
    strip_write_fields_from_response = True


class InlineSerializerInspector(JSONAPISerializerInspector):
    handle_json_api_only = False

    def __init__(self, *args, **kwargs):
        warnings.warn(
            f'{self.__class__.__name__} is deprecated, use drf_yasg_json_api.inspectors.JSONAPISerializerInspector '
            'instead to render docs for JSON API views and optionally '
            'drf_yasg.inspectors.ReferencingSerializerInspector/InlineSerializerInspector to render docs for '
            'non JSON API views',
            DrfYasgJsonApiDeprecationWarning
        )
        super().__init__(*args, **kwargs)


class InlineSerializerSmartInspector(JSONAPISerializerSmartInspector):
    handle_json_api_only = False

    def __init__(self, *args, **kwargs):
        warnings.warn(
            f'{self.__class__.__name__} is deprecated, use drf_yasg_json_api.inspectors.JSONAPISerializerSmartInspector'
            ' instead to render docs for JSON API views and optionally '
            'drf_yasg.inspectors.ReferencingSerializerInspector/InlineSerializerInspector to render docs for '
            'non JSON API views',
            DrfYasgJsonApiDeprecationWarning
        )
        super().__init__(*args, **kwargs)


class IntegerFieldInspectorMixin:
    int64_fields = (models.BigIntegerField, models.BigAutoField)

    def get_format(self, model_field):
        return openapi.FORMAT_INT64 if isinstance(model_field, self.int64_fields) else openapi.FORMAT_INT32


class IntegerIDFieldInspector(IntegerFieldInspectorMixin, inspectors.FieldInspector):
    """
    Force string type on ID field that on model level is integer. Since we get here just an integer, we look for:
     - Primary Key of model that is models.IntegerField
     - Serializer field named "id" that is serializers.IntegerField
    """

    def field_to_swagger_object(self, field, swagger_object_type, **kwargs):
        if not isinstance(field, serializers.IntegerField) or not is_json_api(self.view):
            return inspectors.NotHandled

        stringify_id = False
        integer_format = None

        parent_serializer = get_parent_serializer(field)
        serializer_meta = getattr(parent_serializer, 'Meta', None)
        model = getattr(serializer_meta, 'model', None)
        if model is not None:
            field_name = getattr(field, 'source', None) or field.field_name
            model_field = get_model_field(model, field_name)
            # Check for primary key only if sure it is pure Field (not FieldCacheMixin or anything)
            if (
                model_field is not None and
                isinstance(model_field, (models.IntegerField, models.AutoField)) and
                model_field.primary_key
            ):
                stringify_id = True
                integer_format = self.get_format(model_field)

        elif field.field_name == 'id' and isinstance(field, serializers.IntegerField):
            stringify_id = True

        if not stringify_id:
            return inspectors.NotHandled

        SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, **kwargs)
        return SwaggerType(type=openapi.TYPE_STRING, format=integer_format)


class IntegerPrimaryKeyRelatedFieldInspector(IntegerFieldInspectorMixin, inspectors.FieldInspector):
    """
    Force string type on PrimaryRelatedField that refers to model with integer primary key.
    """

    def field_to_swagger_object(self, field, swagger_object_type, **kwargs):
        if not isinstance(field, serializers.PrimaryKeyRelatedField) or not is_json_api(self.view):
            return inspectors.NotHandled

        if is_many_related_field(field):
            return inspectors.NotHandled

        related_model = get_field_related_model(field)
        if related_model:
            related_model_pk_field = get_model_field(related_model, 'pk')
            if isinstance(related_model_pk_field, (models.IntegerField, models.AutoField)):
                SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, **kwargs)
                return SwaggerType(type=openapi.TYPE_STRING, format=self.get_format(related_model_pk_field))

        return inspectors.NotHandled


class ManyRelatedFieldInspector(inspectors.SimpleFieldInspector):
    """
    Unwrap ManyRelatedField child relation as array node has already been added by SerializerInspector.
    """

    def field_to_swagger_object(self, field, swagger_object_type, **kwargs):
        if is_many_related_field(field) and is_json_api(self.view):
            return self.probe_field_inspectors(field.child_relation, swagger_object_type, **kwargs)

        return inspectors.NotHandled


class NamesFormatFilter(inspectors.FieldInspector):

    def format_string(self, s):
        return format_value(s)

    def format_schema(self, schema):
        """Recursively format property names for the given schema according to``JSON_API_FORMAT_KEYS`` setting.
        The target schema object must be modified in-place.

        :param openapi.Schema schema: the :class:`.Schema` object
        """
        if getattr(schema, 'properties', {}):
            schema.properties = OrderedDict(
                (self.format_string(key), self.format_schema(openapi.resolve_ref(val, self.components)) or val)
                for key, val in schema.properties.items()
            )

            if getattr(schema, 'required', []):
                schema.required = [self.format_string(p) for p in schema.required]

    def process_result(self, result, method_name, obj, **kwargs):
        if isinstance(result, openapi.Schema.OR_REF) and is_json_api(self.view):
            schema = openapi.resolve_ref(result, self.components)
            self.format_schema(schema)

        return result


class XPropertiesFilter(inspectors.FieldInspector):

    def add_write_only(self, result, obj):
        if obj.write_only:
            result.x_write_only = True

    def fix_read_only(self, result, obj):
        # drf_yasg is very cautious about setting read_only, only leaf nodes are allowed to be read only,
        # but in some cases it goes too far and some leaf nodes cases are omitted too.
        # This workaround fixes obvious cases – types that are always leaf nodes
        if obj.read_only:
            if isinstance(result, openapi.Schema) \
                    and result.type in (openapi.TYPE_STRING, openapi.TYPE_INTEGER, openapi.TYPE_BOOLEAN):
                result.read_only = True
            # For non-leaf nodes make read only visible by adding x prefix to avoid conflict with OpenApi 2 validation
            else:
                result.x_read_only = True

    def process_result(self, result, method_name, obj, **kwargs):
        if result is not None:
            self.add_write_only(result, obj)
            self.fix_read_only(result, obj)
        return result
