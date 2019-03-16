import logging
from collections import OrderedDict

from django.db import models
from django.utils import six
from drf_extra_fields.fields import Base64FileField
from drf_extra_fields.fields import Base64ImageField
from drf_yasg import inspectors
from drf_yasg import openapi
from drf_yasg.inspectors.field import get_model_field
from drf_yasg.inspectors.field import get_parent_serializer
from drf_yasg.inspectors.field import get_queryset_field
from drf_yasg.utils import filter_none
from rest_framework import relations
from rest_framework import serializers
from rest_framework.serializers import BaseSerializer
from rest_framework.settings import api_settings
from rest_framework_json_api import utils as json_api_utils
from rest_framework_json_api.utils import format_value
from rest_framework_json_api.utils import get_resource_name
from rest_framework_json_api.utils import get_resource_type_from_model
from rest_framework_json_api.utils import get_resource_type_from_queryset
from rest_framework_json_api.utils import get_resource_type_from_serializer

from docs.utils import get_related_model
from docs.utils import is_json_api_response

logger = logging.getLogger(__name__)


class JSONAPISerializerInspector(inspectors.InlineSerializerInspector):

    def get_schema_included(self, serializer):
        return self.probe_field_inspectors(serializer, openapi.Schema, self.use_definitions, included=True)

    def field_to_swagger_object(self, field, swagger_object_type, use_references, included=False, **kwargs):
        if not self.is_json_api(field):
            return inspectors.NotHandled

        SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, use_references, **kwargs)

        resource_name = get_resource_type_from_serializer(field) if included \
            else get_resource_name(context={'view': self.view})

        return SwaggerType(
            type=openapi.TYPE_OBJECT,
            properties=self.build_json_resource_obj(field, resource_name, SwaggerType, ChildSwaggerType, use_references)
        )

    def build_json_resource_obj(self, serializer, resource_name, SwaggerType, ChildSwaggerType, use_references):
        fields = json_api_utils.get_serializer_fields(serializer)

        id_ = fields.get('id')
        if id_ is None and self.method.lower() == 'get':
            logging.warning('{view}.{serializer} does not contain id field as every resource should'.format(
                view=self.view.__class__.__name__, serializer=serializer.__class__.__name__
            ))

        attributes = self.extract_attributes(fields, ChildSwaggerType, use_references)
        relationships = self.extract_relationships(fields, ChildSwaggerType, use_references)

        resource_data = [
            ('type', SwaggerType(type=openapi.TYPE_STRING, pattern=resource_name)),
            ('id', self.probe_field_inspectors(id_, ChildSwaggerType, use_references)) if id_ else ('id', None),
            ('attributes', SwaggerType(type=openapi.TYPE_OBJECT, properties=attributes) if attributes else None),
            ('relationships', SwaggerType(type=openapi.TYPE_OBJECT, properties=relationships)
                if relationships else None),
        ]

        return filter_none(OrderedDict(resource_data))

    def extract_attributes(self, fields, ChildSwaggerType, use_references):
        attrs = {}
        for field_name, field in six.iteritems(fields):
            # ID is always provided in the root of JSON API so remove it from attributes
            if field_name == 'id':
                continue
            # don't output a key for write only fields
            if fields[field_name].write_only:
                continue
            # Skip fields with relations
            if isinstance(field, (relations.RelatedField, relations.ManyRelatedField, BaseSerializer)):
                continue

            attrs.update({
                field_name: self.probe_field_inspectors(field, ChildSwaggerType, use_references)
            })

        return attrs

    def extract_relationships(self, fields, ChildSwaggerType, use_references):
        data = OrderedDict()

        for field_name, field in six.iteritems(fields):
            many = False
            id_field = field

            if field_name == api_settings.URL_FIELD_NAME:
                continue

            # Skip fields without relations
            if not isinstance(field, (relations.RelatedField, relations.ManyRelatedField)):
                continue

            if isinstance(id_field, serializers.ManyRelatedField):
                id_field = id_field.child_relation
                many = True

            target_field = getattr(id_field, 'slug_field', 'pk')

            # Get model
            if hasattr('id_field', 'get_queryset'):
                field_queryset = get_resource_type_from_queryset(id_field.get_queryset())
                model, model_field = get_queryset_field(field_queryset, target_field)
            else:
                # if the RelatedField has a queryset, try to get the related model field from there
                parent_serializer = get_parent_serializer(id_field)

                serializer_meta = getattr(parent_serializer, 'Meta', None)
                this_model = getattr(serializer_meta, 'model', None)

                source = getattr(id_field, 'source', '') or id_field.field_name
                if not source and isinstance(id_field.parent, serializers.ManyRelatedField):
                    source = getattr(id_field.parent, 'source', '') or id_field.parent.field_name

                model = get_related_model(this_model, source)

            # Resource name from model
            resource_name = get_resource_type_from_model(model)

            # Swagger type evaluation passed to inspectors
            if getattr(id_field, 'pk_field', None):
                # a PrimaryKeyRelatedField can have a `pk_field` attribute which is a
                # serializer field that will convert the PK value
                swagger_id_field = self.probe_field_inspectors(id_field.pk_field, ChildSwaggerType, use_references)
            else:
                swagger_id_field = self.probe_field_inspectors(id_field, ChildSwaggerType, use_references)

            relation_record = openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'type': openapi.Schema(type=openapi.TYPE_STRING, pattern=resource_name),
                    'id': swagger_id_field
                }
            )

            if many:
                relation_record = openapi.Schema(type=openapi.TYPE_ARRAY, items=relation_record)

            data[field_name] = openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'data': relation_record
                }
            )

        return data

    def is_json_api(self, field):
        return field and field.parent is None and is_json_api_response(self.view.renderer_classes)


class JSONAPIM2MFieldInspector(inspectors.SimpleFieldInspector):
    def field_to_swagger_object(self, field, **kwargs):

        if not isinstance(field.parent, serializers.ManyRelatedField) or \
                not is_json_api_response(self.view.renderer_classes):
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


class JSONAPIIDFieldInspector(inspectors.SimpleFieldInspector):
    def field_to_swagger_object(self, field, **kwargs):

        if not isinstance(field, serializers.IntegerField) or not is_json_api_response(self.view.renderer_classes):
            return inspectors.NotHandled

        parent_serializer = get_parent_serializer(field)
        serializer_meta = getattr(parent_serializer, 'Meta', None)
        model = getattr(serializer_meta, 'model', None)

        if model is None:
            return inspectors.NotHandled

        source = getattr(field, 'source', '') or field.field_name

        # Use source but mean field_name
        model_field = get_model_field(model, source)

        if (isinstance(model_field, models.IntegerField) and model_field.primary_key) or \
                isinstance(model_field, models.AutoField):

            SwaggerType, ChildSwaggerType = self._get_partial_types(field, **kwargs)
            return SwaggerType(type=openapi.TYPE_STRING, format=openapi.FORMAT_INT32)

        return inspectors.NotHandled


class JSONAPIFormatFilter(inspectors.FieldInspector):

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
        if isinstance(result, openapi.Schema.OR_REF) and is_json_api_response(self.view.renderer_classes):
            schema = openapi.resolve_ref(result, self.components)
            self.format_schema(schema)

        return result


class AttributesEnhancingFilter(inspectors.FieldInspector):

    def add_write_only(self, result, obj):
        if obj.write_only:
            setattr(result, 'x-write_only', True)

    def fix_read_only(self, result, obj):
        # drf_yasg is very cautious about setting read_only, only leaves are allowed to be read only,
        # but in some cases it misbehaves and obvious leaf cases are omitted too, so we fix this
        if result.type in (openapi.TYPE_STRING, openapi.TYPE_INTEGER, openapi.TYPE_BOOLEAN) and obj.read_only:
            setattr(result, 'read_only', True)

    def process_result(self, result, method_name, obj, **kwargs):

        self.add_write_only(result, obj)
        self.fix_read_only(result, obj)

        return result


class Base64FileFieldInspector(inspectors.FieldInspector):
    """Provides conversions for ``FileField``\\ s."""

    def field_to_swagger_object(self, field, swagger_object_type, use_references, **kwargs):
        SwaggerType, ChildSwaggerType = self._get_partial_types(field, swagger_object_type, use_references, **kwargs)

        if isinstance(field, (Base64ImageField, Base64FileField)):
            if swagger_object_type == openapi.Schema:
                # FileField.to_representation returns URL or file name
                result = SwaggerType(type=openapi.TYPE_STRING, format=openapi.FORMAT_BASE64)
                return result

        return inspectors.NotHandled
