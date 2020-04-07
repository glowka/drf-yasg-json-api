import copy
import logging

from collections import OrderedDict

from django.db import models
from django.utils.functional import cached_property
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

from .utils import get_field_by_source
from .utils import get_related_model
from .utils import get_serializer_model_primary_key
from .utils import is_json_api
from .utils import is_json_api_request
from .utils import is_json_api_response

logger = logging.getLogger(__name__)


class JSONAPIDeclarationError(ValueError):
    pass


class InlineSerializerInspector(inspectors.InlineSerializerInspector):

    def get_schema(self, serializer):
        return self.probe_field_inspectors(serializer, openapi.Schema, self.use_definitions, is_request=False)

    def get_request_schema(self, serializer):
        return self.probe_field_inspectors(serializer, openapi.Schema, self.use_definitions, is_request=True)

    def get_included_schema(self, serializer):
        return self.probe_field_inspectors(serializer, openapi.Schema, self.use_definitions, included=True)

    def field_to_swagger_object(self, field, swagger_object_type, use_references, included=False, is_request=None,
                                **kwargs):
        if not self.is_json_api_root_serializer(field, is_request):
            return super().field_to_swagger_object(field, swagger_object_type, use_references, **kwargs)

        SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, use_references, **kwargs)

        resource_name = get_resource_type_from_serializer(field) if included \
            else get_resource_name(context={'view': self.view})

        return self.build_json_resource_schema(field, resource_name, SwaggerType, ChildSwaggerType, use_references,
                                               is_request)

    def build_json_resource_schema(self, serializer, resource_name, SwaggerType, ChildSwaggerType, use_references,
                                   is_request=None):
        fields = json_api_utils.get_serializer_fields(serializer)

        id_ = self.extract_id_field(fields, serializer)
        if id_ is None and not (self.method.lower() == 'post' and is_request):
            logging.warning('{view}.{serializer} does not contain id field as every resource should'.format(
                view=self.view.__class__.__name__, serializer=serializer.__class__.__name__
            ))

        attributes, req_attributes = self.extract_attributes(id_, fields, ChildSwaggerType, use_references, is_request)
        relationships, req_relationships = self.extract_relationships(fields, ChildSwaggerType, use_references,
                                                                      is_request)
        links = self.extract_links(fields, ChildSwaggerType, use_references) if not is_request else None

        schema_fields = filter_none(OrderedDict(
            type=SwaggerType(type=openapi.TYPE_STRING, pattern=resource_name),
            id=self.probe_field_inspectors(id_, ChildSwaggerType, use_references)
            if id_ and not (is_request and id_.read_only) else None,
            attributes=SwaggerType(type=openapi.TYPE_OBJECT, properties=attributes,
                                   required=req_attributes)
            if attributes else None,
            relationships=SwaggerType(type=openapi.TYPE_OBJECT, properties=relationships,
                                      required=req_relationships)
            if relationships else None,
            links=SwaggerType(type=openapi.TYPE_OBJECT, properties=links)
            if links else None
        ))

        if self.is_request_or_unknown(is_request):
            required_properties = ['id', 'type'] if 'id' in schema_fields else ['type']
        else:
            required_properties = None

        return SwaggerType(
            type=openapi.TYPE_OBJECT,
            properties=schema_fields,
            required=required_properties
        )

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
        serializer_id: serializers.Field = id_field_class(**id_field_kwargs, source=model_pk.name)
        serializer_id.bind('id', copy.deepcopy(serializer))
        return serializer_id

    def extract_attributes(self, id_field, fields, ChildSwaggerType, use_references, is_request=None):
        attrs = {}
        required_attrs = []
        for field_name, field in fields.items():
            if is_request and field.read_only:
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
            many = False
            id_field = field

            if is_request and field.read_only:
                continue

            # Self url field
            if field_name == api_settings.URL_FIELD_NAME:
                continue

            # Skip fields without relations
            if not isinstance(field, (relations.RelatedField, relations.ManyRelatedField, serializers.Serializer)):
                continue

            # Unpack relation from many field
            if isinstance(id_field, serializers.ManyRelatedField):
                id_field = id_field.child_relation
                many = True

            resource_name = self.get_resource_name_from_id_field(field_name, id_field)

            # Pass swagger type evaluation to inspectors
            if getattr(id_field, 'pk_field', None):
                # a PrimaryKeyRelatedField can have a `pk_field` attribute which is a
                # serializer field that will convert the PK value
                swagger_id_field = self.probe_field_inspectors(id_field.pk_field, ChildSwaggerType, use_references)
            else:
                swagger_id_field = self.probe_field_inspectors(id_field, ChildSwaggerType, use_references)

            # Produce swagger output
            relation_data = openapi.Schema(**filter_none(OrderedDict(
                type=openapi.TYPE_OBJECT,
                properties={
                    'type': openapi.Schema(**filter_none(OrderedDict(
                        type=openapi.TYPE_STRING, pattern=resource_name,
                        read_only=field.read_only or None
                    ))),
                    'id': swagger_id_field
                },
                required=['id', 'type'] if (self.is_request_or_unknown(is_request)) and not field.read_only else None,
            )))

            if many:
                relation_data = openapi.Schema(type=openapi.TYPE_ARRAY, items=relation_data)

            relation_links = self.get_links_from_id_field(field_name, field)
            if relation_links:
                relation_links = openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties=relation_links
                )

            relationships[field_name] = openapi.Schema(**filter_none(OrderedDict(
                type=openapi.TYPE_OBJECT,
                properties=filter_none({
                    'data': relation_data,
                    'links': relation_links if self.not_request_or_unknown(is_request) else None
                }),
                read_only=field.read_only or None,
                x_read_only=field.read_only or None,
            )))
            if self.is_request_or_unknown(is_request) and field.required and not field.read_only:
                required_relationships.append(field_name)

        return relationships, (required_relationships or None)

    def get_resource_name_from_id_field(self, field_name, id_field):
        parent_serializer = get_parent_serializer(id_field)
        if isinstance(id_field, dja_serializers.ResourceRelatedField):
            return id_field.get_resource_type_from_included_serializer()

        elif isinstance(id_field, serializers.Serializer):
            return json_api_utils.get_resource_type_from_serializer(id_field)

        # Other kinds of fields
        if hasattr(id_field, 'model'):
            model = id_field.model
        elif hasattr(id_field, 'get_queryset') and id_field.get_queryset():
            model = id_field.get_queryset().model
        # If the RelatedField hasn't got a queryset, take model from the serializer and find proper model field
        else:
            serializer_meta = getattr(parent_serializer, 'Meta', None)
            this_model = getattr(serializer_meta, 'model', None)

            source = getattr(id_field, 'source', '') or id_field.field_name
            if not source and isinstance(id_field.parent, serializers.ManyRelatedField):
                source = getattr(id_field.parent, 'source', '') or id_field.parent.field_name

            model = get_related_model(this_model, source)

        # Resource name from model
        if model:
            return get_resource_type_from_model(model)

        raise ValueError(f"Unable to extract resource name for {parent_serializer}.{field_name} serializer field")

    def get_links_from_id_field(self, field_name, id_field):
        links = OrderedDict()
        if isinstance(id_field, dja_serializers.ResourceRelatedField):
            if id_field.related_link_lookup_field is not None:
                links['related'] = openapi.Schema(type=openapi.TYPE_STRING, pattern=openapi.FORMAT_URI, read_only=True)
            if id_field.self_link_view_name is not None:
                links['self'] = openapi.Schema(type=openapi.TYPE_STRING, pattern=openapi.FORMAT_URI, read_only=True)
        return links or None

    def extract_links(self, fields, ChildSwaggerType, use_references):
        self_field_name = api_settings.URL_FIELD_NAME

        return filter_none(OrderedDict(
            self=openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)
            if self_field_name in fields and isinstance(fields[self_field_name], serializers.RelatedField) else None
        ))

    def inline_serializer_from_fields(self, fields_dict, sub_serializer=True):
        attrs = {f_name: copy.deepcopy(field) for f_name, field in fields_dict.items()}
        serializer = type('Attributes', (serializers.Serializer,), attrs)()
        if sub_serializer:
            serializer.bind(field_name='', parent=serializers.Serializer())
        return serializer

    def is_json_api_root_serializer(self, field, is_request=False):
        return field and field.parent is None and isinstance(field, serializers.Serializer) and (
            (not is_request and is_json_api_response(self.view.renderer_classes))
            or ((is_request or is_request is None) and is_json_api_request(self.view.parser_classes))
        )

    def not_request_or_unknown(self, is_request):
        # evaluate None to True as well
        return not is_request

    def is_request_or_unknown(self, is_request):
        return is_request is None or is_request


class ManyRelatedFieldInspector(inspectors.SimpleFieldInspector):
    """
    Many related field in pure REST is an array, but here in JSON API it is just single field.
    This single field is used as `id` which is part of an `type` + `id` object which is then put in array.
    """

    def field_to_swagger_object(self, field, **kwargs):

        if not isinstance(field.parent, serializers.ManyRelatedField) or not is_json_api(self.view):
            return inspectors.NotHandled

        parent_serializer = get_parent_serializer(field)
        serializer_meta = getattr(parent_serializer, 'Meta', None)
        model = getattr(serializer_meta, 'model', None)

        if model is None:
            return inspectors.NotHandled

        source = getattr(field.parent, 'source', '') or field.parent.field_name

        field_model = get_related_model(model, source)
        if field_model is None:
            return inspectors.NotHandled

        model_field = get_model_field(field_model, 'pk')

        if isinstance(model_field, (models.IntegerField, models.AutoField)):
            SwaggerType, ChildSwaggerType = self._get_partial_types(field, **kwargs)
            return SwaggerType(type=openapi.TYPE_STRING, format=openapi.FORMAT_INT32)

        return inspectors.NotHandled


class IDFieldInspector(inspectors.FieldInspector):
    def field_to_swagger_object(self, field, swagger_object_type, **kwargs):
        if not is_json_api(self.view):
            return inspectors.NotHandled

        parent_serializer = get_parent_serializer(field)
        serializer_meta = getattr(parent_serializer, 'Meta', None)
        model = getattr(serializer_meta, 'model', None)
        if model is None:
            return inspectors.NotHandled

        field_name = getattr(field, 'source', None) or field.field_name
        model_field = get_model_field(model, field_name)
        if model_field is None:
            return inspectors.NotHandled

        if (isinstance(model_field, models.IntegerField) and model_field.primary_key) or \
                isinstance(model_field, models.AutoField):
            SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, **kwargs)
            return SwaggerType(type=openapi.TYPE_STRING, format=openapi.FORMAT_INT32)

        return inspectors.NotHandled


class NameFormatFilter(inspectors.FieldInspector):

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
        if result.type in (openapi.TYPE_STRING, openapi.TYPE_INTEGER, openapi.TYPE_BOOLEAN) and obj.read_only:
            result.read_only = True
        # For non-leaf nodes make read only visible by adding x prefix to avoid conflict with OpenApi 2 validation
        elif obj.read_only:
            result.x_read_only = True

    def process_result(self, result, method_name, obj, **kwargs):
        if result is not None:
            self.add_write_only(result, obj)
            self.fix_read_only(result, obj)
        return result


class DjangoFilterInspector(inspectors.CoreAPICompatInspector):
    @cached_property
    def django_filters(self):
        from rest_framework_json_api import django_filters
        return django_filters

    def get_filter_parameters(self, filter_backend):
        if not isinstance(filter_backend, self.django_filters.DjangoFilterBackend):
            return inspectors.NotHandled
        return super().get_filter_parameters(filter_backend)

    def coreapi_field_to_parameter(self, field):
        parameter = super().coreapi_field_to_parameter(field)
        parameter.name = f'filter[{parameter.name}]'
        return parameter
