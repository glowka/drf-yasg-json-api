import logging

from collections import OrderedDict

from drf_yasg import inspectors
from drf_yasg import openapi
from drf_yasg.utils import filter_none
from drf_yasg.utils import guess_response_status
from rest_framework import serializers
from rest_framework.status import is_success
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
        """
        Hook in to generate request schema from view's serializer OR overridden using `request_body` argument of
        of `swagger_auto_schema` decorator.
        """
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

    def get_response_schemas(self, response_serializers):
        """
        Hook in to generate response schemas for all pure (not converted to schema) serializers which can be provided
        using `responses` argument of `swagger_auto_schema` decorator.
        """
        if not is_json_api_response(self.get_renderer_classes()):
            return super().get_response_schemas(response_serializers)

        response_schemas = OrderedDict()
        for status_code, serializer in response_serializers.items():
            if is_success(int(status_code)) and isinstance(serializer, serializers.BaseSerializer):
                response_schemas[status_code] = self.get_overridden_response_schema(serializer)
            else:
                response_schemas[status_code] = serializer

        return super().get_response_schemas(response_schemas)

    def get_overridden_response_schema(self, serializer):
        if getattr(serializer, 'many', False):
            # Use list's item as main serializer, create new instance to make it look like root serializer not child
            serializer = serializer.child.__class__()
            serializer_schema = openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=self.serializer_to_schema(serializer)
            )
        else:
            serializer_schema = self.serializer_to_schema(serializer)

        return openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties=OrderedDict(
                data=serializer_schema,
                included=self.get_included_schema_for_response(serializer)
            )
        )

    def get_default_responses(self):
        """
        Hook in to generate default response schema from view's serializer. Used only when no overriding response is
        provided using `responses` argument of `swagger_auto_schema` decorator.
        """
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
                    data=self.get_data_schema_for_default_response(default_serializer),
                    included=self.get_included_schema_for_response(default_serializer),
                )
            )
            if self.should_page():
                default_schema = self.get_paginated_response(default_schema)

        return filter_none(OrderedDict({str(default_status): default_schema}))

    def get_data_schema_for_default_response(self, default_serializer):
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

    def get_included_schema_for_response(self, serializer):
        included_paths, included_serializers = self._get_included_paths_and_serializers(serializer)
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
        """
        Hook in to add `include` parameter supported by response serializer.

        Supports generating parameter for success response from `responses` using `swagger_auto_schema` decorator
        and (of course) for view's main serializer if it's not overridden by decorator.

        """
        if not is_json_api_response(self.get_renderer_classes()):
            return super().get_query_parameters()

        success_response_serializers = [
            serializer for status_code, serializer in self.get_response_serializers().items()
            if (
                is_success(int(status_code)) and
                isinstance(serializer, serializers.BaseSerializer) and
                hasattr(serializer, 'included_serializers')
            )
        ]

        if not success_response_serializers:
            response_serializer = self.get_default_response_serializer()
        else:
            response_serializer = success_response_serializers[0]
            if len(success_response_serializers) > 1:  # pragma: no cover
                logger.warning(
                    'More than one response serializer for view {view_name} method {method} '
                    'provides included serializers, falling back to first one'.format(
                        view_name=self.view.__class__.__name__, method=self.method
                    )
                )

        return super().get_query_parameters() + self.get_query_parameters_included(response_serializer)

    def get_query_parameters_included(self, serializer):
        parameters = []

        if hasattr(serializer, 'included_serializers'):
            paths, serializers = self._get_included_paths_and_serializers(serializer)
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

    MAX_INCLUDED_PATH_DEPTH = 20

    def _get_included_paths_and_serializers(self, field):
        field_cls = field if isinstance(field, type) else field.__class__
        all_included_paths = []
        all_included_serializers = set()
        serializers_to_visit = [([], [], field_cls)]
        while serializers_to_visit:
            path, parent_serializers, serializer = serializers_to_visit.pop()
            if len(path) > self.MAX_INCLUDED_PATH_DEPTH:  # pragma: no cover
                logger.warning('Exceeded max included path limit ({limit}), ignoring longer paths'.format(
                    limit=self.MAX_INCLUDED_PATH_DEPTH
                ))
                continue

            # Support recursive reference using "self" keyword or indirect recursion using lazy string paths
            if serializer in parent_serializers:
                if parent_serializers[-1] is serializer:
                    all_included_paths.append('{path} [recursive]'.format(path=".".join(path)))
                else:
                    recursive_path = path[parent_serializers.index(serializer):]
                    all_included_paths.append('{path} [recursive through: {recursive_path}]'.format(
                        path=".".join(path), recursive_path=".".join(recursive_path))
                    )
                continue
            if path:
                all_included_paths.append(".".join(path))
            included_serializers = get_included_serializers(serializer)
            for name, sub_serializer in included_serializers.items():
                all_included_serializers.add(sub_serializer)
                serializers_to_visit.append((
                    path + [self._format_key(name)],
                    parent_serializers + [serializer],
                    sub_serializer
                ))

        return all_included_paths, all_included_serializers

    def _format_key(self, s):
        return format_value(s)
