import operator

from unittest import mock

import drf_yasg.inspectors

from django.conf.urls import url
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins
from rest_framework import routers
from rest_framework import views
from rest_framework import viewsets
from rest_framework_json_api import django_filters
from rest_framework_json_api import filters
from rest_framework_json_api import pagination
from rest_framework_json_api import parsers
from rest_framework_json_api import renderers
from rest_framework_json_api import serializers

import drf_yasg_json_api.inspectors

from tests import base
from tests import compatibility
from tests import models as test_models


def test_get():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == 'string'
    assert 'type' in response_schema['data']['properties']
    assert response_schema['data']['properties']['type']['pattern'] == 'projects'
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name', 'archived']
    assert 'relationships' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['relationships']['properties'].keys()) == ['members']
    members_schema = response_schema['data']['properties']['relationships']['properties']['members']['properties']
    assert members_schema['data']['items']['properties']['id']['type'] == 'string'
    assert members_schema['data']['items']['properties']['type']['pattern'] == 'members'


def test_pagination():
    class SwaggerAutoSchemaWithPagination(base.BasicSwaggerAutoSchema):
        paginator_inspectors = [
            drf_yasg_json_api.inspectors.DjangoRestResponsePagination,
            drf_yasg.inspectors.DjangoRestResponsePagination,
            drf_yasg.inspectors.CoreAPICompatInspector,
        ]

    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')

    class ProjectViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = SwaggerAutoSchemaWithPagination
        pagination_class = pagination.JsonApiPageNumberPagination

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    request_parameters_schema = swagger['paths']['/projects/']['get']['parameters']
    assert set(map(operator.itemgetter('name'), request_parameters_schema)) == {'page[number]', 'page[size]'}

    response_schema = swagger['paths']['/projects/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['items']['properties']
    assert 'type' in response_schema['data']['items']['properties']
    assert 'attributes' in response_schema['data']['items']['properties']
    assert 'relationships' in response_schema['data']['items']['properties']
    assert 'links' in response_schema
    assert set(response_schema['links']['properties'].keys()) == {'first', 'next', 'last', 'prev'}
    assert 'meta' in response_schema
    assert 'pagination' in response_schema['meta']['properties']
    pagination_response_schema = response_schema['meta']['properties']['pagination']['properties']
    assert set(pagination_response_schema.keys()) == {'page', 'pages', 'count'}


@mock.patch('drf_yasg_json_api.inspectors.view.logger')
def test_list_missing_serializer_warning(logger):
    class ProjectView(views.APIView):
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema

        def get(*args, **kwargs):
            pass

    urlpatterns = [
        url('projects/', ProjectView.as_view())
    ]

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=urlpatterns)

    swagger = generator.get_schema(request=None, public=True)

    assert swagger['paths']['/projects/']['get']
    assert len(logger.warning.mock_calls) == 2
    logger.warning.assert_called_with('Missing schema definition for list action of ProjectView, '
                                      'have you defined get_serializer?')


def test_strip_write_only():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')
            extra_kwargs = {
                'name': {'write_only': False},
                'archived': {'write_only': True},
                'members': {'write_only': True},
            }

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert 'type' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name']
    assert 'relationships' not in response_schema['data']['properties']


@mock.patch('rest_framework.settings.api_settings.URL_FIELD_NAME', 'obj_url')
def test_data_links_self():

    class ProjectSerializer(serializers.ModelSerializer):
        obj_url = serializers.HyperlinkedIdentityField(view_name='any')

        class Meta:
            model = test_models.Project
            fields = ('id', 'obj_url')

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']

    assert 'id' in response_schema['data']['properties']
    assert 'type' in response_schema['data']['properties']
    assert 'links' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['links']['properties'].keys()) == ['self']


def test_filter():
    class FilterSwaggerAutoSchema(base.BasicSwaggerAutoSchema):
        filter_inspectors = [drf_yasg_json_api.inspectors.DjangoFilterInspector]

    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')

    class ProjectViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = FilterSwaggerAutoSchema

        filter_backends = (filters.QueryParameterValidationFilter, django_filters.DjangoFilterBackend)
        filterset_fields = {
            'archived': ('exact',),
        }

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    request_parameters_schema = swagger['paths']['/projects/']['get']['parameters']
    assert request_parameters_schema[0]['name'] == 'filter[archived]'


def test_non_model():
    class ProjectSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        name = serializers.CharField()

    class ProjectViewSet(viewsets.ViewSet):
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema
        resource_name = 'projects'
        serializer_class = ProjectSerializer

        def get_serializer(self, *args, **kwargs):
            return self.serializer_class(*args, **kwargs)

        def retrieve(self, request):
            pass

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'properties' in response_schema['data']
    assert 'id' in response_schema['data']['properties']
    assert 'type' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name']


def test_non_model_many():
    class ProjectSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        name = serializers.CharField()

    class ProjectViewSet(viewsets.ViewSet):
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema
        resource_name = 'projects'
        serializer_class = ProjectSerializer

        def get_serializer(self, *args, **kwargs):
            return self.serializer_class(*args, **kwargs)

        def list(self, request):
            pass

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/']['get']['responses']['200']['schema']['properties']
    assert 'items' in response_schema['data']
    assert 'id' in response_schema['data']['items']['properties']
    assert 'type' in response_schema['data']['items']['properties']
    assert list(response_schema['data']['items']['properties']['attributes']['properties'].keys()) == ['name']


def test_non_model__responses_override():
    class ProjectSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        name = serializers.CharField()

    class ProjectViewSet(viewsets.ViewSet):
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema
        resource_name = 'projects'

        @swagger_auto_schema(responses={200: ProjectSerializer()})
        def retrieve(self, request):
            pass

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'properties' in response_schema['data']
    assert 'id' in response_schema['data']['properties']
    assert 'type' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name']


def test_non_model_many__responses_override():
    class ProjectSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        name = serializers.CharField()

    class ProjectViewSet(viewsets.ViewSet):
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema
        resource_name = 'projects'

        @swagger_auto_schema(responses={200: ProjectSerializer(many=True)})
        def list(self, request):
            pass

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/']['get']['responses']['200']['schema']['properties']
    assert 'items' in response_schema['data']
    assert 'id' in response_schema['data']['items']['properties']
    assert 'type' in response_schema['data']['items']['properties']
    assert list(response_schema['data']['items']['properties']['attributes']['properties'].keys()) == ['name']
