import logging

from django.utils.functional import cached_property
from drf_yasg import inspectors

logger = logging.getLogger(__name__)

__all__ = [
    'DjangoFilterInspector',
]


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
