import itertools

from typing import Optional

from django.db import models
from drf_yasg.inspectors.field import get_parent_serializer
from rest_framework import serializers


def is_json_api(view):
    return is_json_api_response(view.renderer_classes) or is_json_api_request(view.parser_classes)


def is_json_api_response(renderer_classes):
    from rest_framework_json_api.renderers import JSONRenderer as JSONAPIRenderer
    return any(issubclass(renderer, JSONAPIRenderer) for renderer in renderer_classes)


def is_json_api_request(parser_classes):
    from rest_framework_json_api.parsers import JSONParser as JSONAPIParser
    return any(issubclass(parser, JSONAPIParser) for parser in parser_classes)


def get_related_model(model, source):
    if source == '*':
        return model

    descriptor = model
    try:
        for attr in source.split('.'):
            descriptor = getattr(descriptor, attr)
    except AttributeError:  # pragma: no cover
        return None

    try:
        is_forward = descriptor.field in itertools.chain(model._meta.fields, model._meta.many_to_many)
    except AttributeError:  # pragma: no cover
        return None

    if is_forward:
        return descriptor.field.related_model
    else:
        return descriptor.field.model


def get_serializer_model_primary_key(serializer):
    if not isinstance(serializer, serializers.ModelSerializer):
        return None  # pragma: no cover
    return [f for f in serializer.Meta.model._meta.fields if f.primary_key][0]


def get_field_by_source(fields: list, source):
    for field in fields:
        if field.source == source:
            return field
    return None


def get_field_related_model(field) -> Optional[models.Model]:
    # Try extracting directly from field
    related_model = _get_field_model(field)
    # If failed try to extract by traversing model and model fields
    if related_model is None:
        parent_serializer = get_parent_serializer(field)
        serializer_meta = getattr(parent_serializer, 'Meta', None)
        model = getattr(serializer_meta, 'model', None)
        if model is not None:
            related_model = get_related_model(model, source=get_field_source(field))
    return related_model


def _get_field_model(field: serializers.Field) -> Optional[models.Model]:
    field_model = getattr(field, 'model', None)
    if field_model:
        return field_model

    try:
        return field.queryset.model
    except AttributeError:  # pragma: no cover
        return None


def is_many_related_field(field):
    # The check for child relation attribute covers ManyRelationField as well as other possible cases like
    # hacky SerializerMethodResourceRelatedField
    return getattr(field, 'child_relation', None)


def get_field_source(field: serializers.Field):
    source = field.source or field.field_name
    # If no source and parent is not serializer it is child_field of other field
    if not source and not isinstance(field.parent, serializers.BaseSerializer):
        return field.parent.source or field.parent.field_name
    return source
