from functools import wraps


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


def return_for_swagger(value_for_swagger):
    """
    Decorator for methods like get_queryset which needs to be called by drf_yasg for introspection purposes.
    In such cases request may lack some attributes (e.g. from middleware) and so the easiest option is to
    provide decorator which will return dedicated value for drf_yasg: for example proper queryset but empty.
    """
    def decorator(view_method):
        @wraps(view_method)
        def _wrapped_view(self, *args, **kwargs):
            return view_method(self, *args, **kwargs) if not hasattr(self, 'swagger_fake_view') else value_for_swagger
        return _wrapped_view
    return decorator


def supply_args_for_swagger(*args, **kwargs):
    """
    Decorator for methods like get_queryset which needs to be called by drf_yasg for introspection purposes.
    In such cases request may lack some attributes (e.g. from middleware), so one technique is to provide additional
    args for call which is initiated by swagger.
    """
    def decorator(view_method):
        @wraps(view_method)
        def _wrapped_view(self):
            return view_method(self) if not hasattr(self, 'swagger_fake_view') else view_method(self, *args, **kwargs)
        return _wrapped_view
    return decorator


def is_swagger(view):
    return hasattr(view, 'swagger_fake_view')


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
