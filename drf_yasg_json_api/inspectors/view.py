import logging

from collections import OrderedDict

from drf_yasg import inspectors
from drf_yasg import openapi
from drf_yasg.utils import filter_none
from drf_yasg.utils import guess_response_status
from rest_framework_json_api.utils import format_value
from rest_framework_json_api.utils import get_included_serializers
from rest_framework_json_api.utils import get_resource_type_from_serializer

from drf_yasg_json_api.utils import is_json_api_request
from drf_yasg_json_api.utils import is_json_api_response

__all__ = [
    'SwaggerAutoSchema',
]

logger = logging.getLogger(__name__)


class SwaggerAutoSchema(inspectors.SwaggerAutoSchema):
    def get_request_body_schema(self, serializer):
        schema = self.serializer_to_request_schema(serializer)
        if is_json_api_request(self.get_parser_classes()):
            if schema is not None:
                schema = openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties=OrderedDict({
                        'data': schema,
                    })
                )
        return schema

    def get_default_responses(self):
        if not is_json_api_response(self.get_renderer_classes()):
            return super().get_default_responses()

        method = self.method.lower()

        default_status = guess_response_status(method)
        default_schema = ''
        if method in ('get', 'post', 'put', 'patch'):
            default_serializer = self.get_default_response_serializer()

            default_schema = openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties=OrderedDict(
                    data=self.get_default_response_data(default_serializer),
                    included=self.get_default_response_included(default_serializer),
                )
            )
            if self.should_page():
                default_schema = self.get_paginated_response(default_schema)

        return filter_none(OrderedDict({str(default_status): default_schema}))

    def get_default_response_data(self, default_serializer):
        if isinstance(default_serializer, openapi.Schema):
            default_data_schema = default_serializer
        elif default_serializer:
            default_data_schema = self.serializer_to_schema(default_serializer) or ''
        else:
            default_data_schema = ''

        if self.is_list_view() and self.method.lower() == 'get':
            if default_data_schema:
                default_data_schema = openapi.Schema(type=openapi.TYPE_ARRAY, items=default_data_schema)
            else:
                logger.warning(
                    'Missing schema definition for list action of {view_name}, have you defined get_serializer?'.format(
                        view_name=self.view.__class__.__name__
                    )
                )

        return default_data_schema

    def get_default_response_included(self, default_serializer):
        included_paths, included_serializers = self._get_included_paths_and_serializers(default_serializer)
        if not included_serializers:
            return None

        return openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description='note: expect this field to be an array consisting of items of types listed below',
            properties={get_resource_type_from_serializer(serializer): self.serializer_to_included_schema(serializer())
                        for i, serializer in enumerate(included_serializers)}
        )

    def serializer_to_included_schema(self, serializer):
        return self.probe_inspectors(
            self.field_inspectors, 'get_included_schema', serializer, {'field_inspectors': self.field_inspectors}
        )

    def serializer_to_request_schema(self, serializer):
        return self.probe_inspectors(
            self.field_inspectors, 'get_request_schema', serializer, {'field_inspectors': self.field_inspectors},
        )

    def get_query_parameters(self):
        if not is_json_api_response(self.get_renderer_classes()):
            return super().get_query_parameters()

        default_serializer = self.get_default_response_serializer()

        return super().get_query_parameters() + self.get_query_parameters_included(default_serializer)

    def get_query_parameters_included(self, field):
        parameters = []

        if hasattr(field, 'included_serializers'):
            paths, serializers = self._get_included_paths_and_serializers(field)
            parameters.append(openapi.Parameter(
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                name='include',
                description='Include relations in response. Available relations: {relation_paths}'.format(
                    relation_paths=", ".join(paths)
                ),
                format='comma-separated-array'
            ))

        return parameters

    def _get_included_paths_and_serializers(self, field):
        all_included_paths = []
        all_included_serializers = set()
        serializers_to_visit = [([], field)]
        while serializers_to_visit:
            path, serializer = serializers_to_visit.pop()
            # Support recursive reference using "self" keyword
            if path and serializer is (field if isinstance(field, type) else field.__class__):
                all_included_paths.append('{path} [recursive]'.format(path=".".join(path)))
                continue
            if path:
                all_included_paths.append(".".join(path))
            included_serializers = get_included_serializers(serializer)
            for name, sub_serializer in included_serializers.items():
                serializers_to_visit.append((path + [self._format_key(name)], sub_serializer))
                all_included_serializers.add(sub_serializer)

        return all_included_paths, all_included_serializers

    def _format_key(self, s):
        return format_value(s)
