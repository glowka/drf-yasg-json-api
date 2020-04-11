import logging

from collections import OrderedDict

from django.utils.functional import cached_property
from drf_yasg import inspectors
from drf_yasg import openapi
from drf_yasg.utils import filter_none
from rest_framework_json_api import pagination

logger = logging.getLogger(__name__)

__all__ = [
    'DjangoFilterInspector',
    'DjangoRestResponsePagination',
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


class DjangoRestResponsePagination(inspectors.PaginatorInspector):

    def get_paginated_response(self, paginator, response_schema):
        assert 'data' in response_schema['properties'], "expected data field in response"
        assert response_schema['properties']['data'].type == openapi.TYPE_ARRAY, "array expected for paged response"
        if not isinstance(paginator, (pagination.JsonApiPageNumberPagination, pagination.JsonApiLimitOffsetPagination)):
            return inspectors.NotHandled

        has_page = isinstance(paginator, pagination.JsonApiPageNumberPagination)
        meta_schema = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=OrderedDict(
                pagination=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties=OrderedDict(filter_none((
                        ('count', openapi.Schema(type=openapi.TYPE_INTEGER)),
                        ('page', openapi.Schema(type=openapi.TYPE_INTEGER) if has_page else None),
                        ('pages', openapi.Schema(type=openapi.TYPE_INTEGER) if has_page else None),
                        ('limit', openapi.Schema(type=openapi.TYPE_INTEGER) if not has_page else None),
                        ('offset', openapi.Schema(type=openapi.TYPE_INTEGER) if not has_page else None),
                    ))),
                )
            )
        )
        links_schema = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=OrderedDict((
                ('first', openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)),
                ('next', openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)),
                ('last', openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)),
                ('prev', openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_URI)),
            )),
        )

        return openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=filter_none(OrderedDict(
                links=links_schema,
                meta=meta_schema,
                data=response_schema.properties['data'],
                included=response_schema.properties.get('included')
            ))
        )
