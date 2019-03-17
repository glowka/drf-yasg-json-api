def is_json_api_response(renderer_classes):
    from rest_framework_json_api.renderers import JSONRenderer as JSONAPIRenderer
    return any(issubclass(renderer, JSONAPIRenderer) for renderer in renderer_classes)


def is_json_api_request(parser_classes):
    from rest_framework_json_api.parsers import JSONParser as JSONAPIParser
    return any(issubclass(parser, JSONAPIParser) for parser in parser_classes)


def unless_swagger(view, expression, default=()):
    if hasattr(view, 'swagger_fake_view'):
        return default
    else:
        return expression()


def get_related_model(model, source):
    if source == '*':
        return model

    descriptor = getattr(model, source)

    try:
        return descriptor.rel.related_model if descriptor.reverse else descriptor.rel.model
    except Exception:
        try:
            return descriptor.field.remote_field.model
        except Exception:
            return None
