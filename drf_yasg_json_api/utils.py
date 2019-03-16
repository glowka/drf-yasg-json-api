def is_json_api_response(renderer_classes):
    from rest_framework_json_api.renderers import JSONRenderer as JSONAPIRenderer
    return any(issubclass(renderer, JSONAPIRenderer) for renderer in renderer_classes)


def unless_swagger(view, expression, default=()):
    if hasattr(view, 'swagger_fake_view'):
        return default
    else:
        return expression()


def get_related_model(model, source):
    descriptor = getattr(model, source)
    try:
        return descriptor.rel.related_model if descriptor.reverse else descriptor.rel.model
    except Exception:
        try:
            return descriptor.field.remote_field.model
        except Exception:
            return None
