import drf_yasg.inspectors

from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework import mixins
from rest_framework import routers
from rest_framework import viewsets
from rest_framework_json_api import parsers
from rest_framework_json_api import renderers
from rest_framework_json_api import serializers

import drf_yasg_json_api.inspectors

from tests import base
from tests import compatibility
from tests import models as test_models


def test_post():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')

    class ProjectViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    request_body_schema = swagger['paths']['/projects/']['post']['parameters'][0]['schema']['properties']
    assert 'id' not in request_body_schema['data']['properties']
    assert 'type' in request_body_schema['data']['properties']
    assert 'attributes' in request_body_schema['data']['properties']
    assert list(request_body_schema['data']['properties']['attributes']['properties'].keys()) == ['name', 'archived']
    assert 'relationships' in request_body_schema['data']['properties']
    assert list(request_body_schema['data']['properties']['relationships']['properties'].keys()) == ['members']


def test_put():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')

    class ProjectViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    request_body_schema = swagger['paths']['/projects/{id}/']['put']['parameters'][0]['schema']['properties']
    assert 'id' in request_body_schema['data']['properties']
    assert 'type' in request_body_schema['data']['properties']
    assert 'attributes' in request_body_schema['data']['properties']
    assert list(request_body_schema['data']['properties']['attributes']['properties'].keys()) == ['name', 'archived']
    assert 'relationships' in request_body_schema['data']['properties']
    assert list(request_body_schema['data']['properties']['relationships']['properties'].keys()) == ['members']


def test_post__strip_read_only_fields():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')
            read_only_fields = ['archived', 'members']

    class ProjectViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    request_body_schema = swagger['paths']['/projects/']['post']['parameters'][0]['schema']['properties']
    assert 'id' not in request_body_schema['data']['properties']
    assert 'type' in request_body_schema['data']['properties']
    assert 'attributes' in request_body_schema['data']['properties']
    assert list(request_body_schema['data']['properties']['attributes']['properties'].keys()) == ['name']
    assert 'relationships' not in request_body_schema['data']['properties']


def test_post__mark_as_required():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')
            extra_kwargs = {
                'name': {'required': True},
                'archived': {'required': False},
                'members': {'required': True},
            }

    class ProjectViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    request_body_schema = swagger['paths']['/projects/']['post']['parameters'][0]['schema']['properties']
    assert set(request_body_schema['data']['required']) == {'type', 'attributes', 'relationships'}
    assert request_body_schema['data']['properties']['attributes']['required'] == ['name']
    assert request_body_schema['data']['properties']['relationships']['required'] == ['members']
    members_schema = request_body_schema['data']['properties']['relationships']['properties']['members']
    assert members_schema['required'] == ['data']
    assert set(members_schema['properties']['data']['items']['required']) == {'type', 'id'}


def test_post__x_properties():
    class XPropertiesSwaggerAutoSchema(drf_yasg_json_api.inspectors.SwaggerAutoSchema):
        field_inspectors = [
            drf_yasg_json_api.inspectors.NamesFormatFilter,
            drf_yasg_json_api.inspectors.XPropertiesFilter,
            drf_yasg_json_api.inspectors.InlineSerializerInspector,
            drf_yasg_json_api.inspectors.IntegerIDFieldInspector,
            drf_yasg_json_api.inspectors.ManyRelatedFieldInspector,
            drf_yasg.inspectors.RelatedFieldInspector,
            drf_yasg.inspectors.SimpleFieldInspector,
            drf_yasg.inspectors.StringDefaultFieldInspector,
        ]

    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')
            extra_kwargs = {
                'name': {'read_only': True},
                'archived': {'read_only': True},
                'members': {'write_only': True},
            }

    class ProjectViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = XPropertiesSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    request_body_schema = swagger['paths']['/projects/']['post']['parameters'][0]['schema']['properties']
    # TODO: add support for marking whole data/relationships if all children write only
    # assert 'x-writeOnly' in request_body_schema['data']['properties']['relationships']
    members_schema = request_body_schema['data']['properties']['relationships']['properties']['members']['properties']
    assert 'x-writeOnly' in members_schema['data']['items']['properties']['id']

    response_schema = swagger['paths']['/projects/']['post']['responses']['201']['schema']['properties']
    # TODO: add support for marking whole attributes key read_only if all children read only
    # assert 'x-readOnly' in response_schema['data']['properties']['attributes']
    assert 'readOnly' in response_schema['data']['properties']['attributes']['properties']['name']
    assert 'readOnly' in response_schema['data']['properties']['attributes']['properties']['archived']
