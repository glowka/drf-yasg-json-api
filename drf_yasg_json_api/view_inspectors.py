from collections import OrderedDict

from drf_yasg import openapi
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.utils import filter_none
from drf_yasg.utils import guess_response_status
from drf_yasg.utils import is_list_view
from rest_framework_json_api.utils import format_value
from rest_framework_json_api.utils import get_resource_type_from_serializer

from .utils import is_json_api_request
from .utils import is_json_api_response


class SwaggerJSONAPISchema(SwaggerAutoSchema):
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
                properties=OrderedDict({
                    'data': self.get_default_response_data(default_serializer),
                    'included': self.get_default_response_included(default_serializer)
                })
            )

        return filter_none(OrderedDict({str(default_status): default_schema}))

    def get_default_response_data(self, default_serializer):
        default_data_schema = ''
        if default_serializer and not isinstance(default_serializer, openapi.Schema):
            default_data_schema = self.serializer_to_schema(default_serializer) or ''

        if is_list_view(self.path, self.method, self.view) and self.method.lower() == 'get':
            default_data_schema = openapi.Schema(type=openapi.TYPE_ARRAY, items=default_data_schema)

        return default_data_schema

    def get_default_response_included(self, default_serializer):
        included_paths, included_serializers = self._get_included_paths(default_serializer)
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
            paths, serializers = self._get_included_paths(field)
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

    def _get_included_paths(self, field):
        candidates = [([], field)]
        included_paths = []
        sub_serializers = set()
        while candidates:
            path, serializer = candidates.pop()
            if path:
                included_paths.append(".".join(path))
            if not hasattr(serializer, 'included_serializers'):
                continue
            for name, sub_serializer in serializer.included_serializers.items():
                candidates.append((path + [self._format_key(name)], sub_serializer))
                sub_serializers.add(sub_serializer)

        return included_paths, sub_serializers

    def _format_key(self, s):
        return format_value(s)
