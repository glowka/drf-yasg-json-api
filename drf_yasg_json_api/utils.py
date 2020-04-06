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
    except AttributeError:
        return None

    try:
        return descriptor.rel.related_model if descriptor.reverse else descriptor.rel.model
    except Exception:
        try:
            return descriptor.field.remote_field.model
        except Exception:
            return None


def get_serializer_model_primary_key(serializer):
    if not isinstance(serializer, serializers.ModelSerializer):
        return None
    return [f for f in serializer.Meta.model._meta.fields if f.primary_key][0]


def get_field_by_source(fields: list, source):
    for field in fields:
        if field.source == source:
            return field
    return None
