import drf_yasg.inspectors

from django.db import models
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework import mixins
from rest_framework import routers
from rest_framework import viewsets
from rest_framework_json_api import parsers
from rest_framework_json_api import renderers
from rest_framework_json_api import serializers

import drf_yasg_json_api.inspectors

from drf_yasg_json_api import view_inspectors
from tests import compatibility


class BasicSwaggerAutoSchema(view_inspectors.SwaggerAutoSchema):
    field_inspectors = [
        drf_yasg_json_api.inspectors.NameFormatFilter,
        drf_yasg_json_api.inspectors.InlineSerializerStrippingInspector,
        drf_yasg_json_api.inspectors.IDIntegerFieldInspector,
        drf_yasg_json_api.inspectors.ManyRelatedIDIntegerFieldInspector,
        drf_yasg.inspectors.RelatedFieldInspector,
        drf_yasg.inspectors.SimpleFieldInspector,
        drf_yasg.inspectors.StringDefaultFieldInspector,
    ]


class Member(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)


class Project(models.Model):
    name = models.CharField(max_length=100)
    archived = models.BooleanField()
    members = models.ManyToManyField(Member)


def test_get__fallback_to_rest():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = '__all__'

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert list(response_schema.keys()) == ['id', 'name', 'archived', 'members']


def test_get():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = '__all__'

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == 'string'
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name', 'archived']
    assert 'relationships' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['relationships']['properties'].keys()) == ['members']


def test_get__included():
    class MemberSerializer(serializers.ModelSerializer):
        class Meta:
            model = Member
            fields = '__all__'

    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = '__all__'

        included_serializers = {
            'members': MemberSerializer,
        }

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'included' in response_schema
    assert 'members' in response_schema['included']['properties']
    request_parameters_schema = swagger['paths']['/projects/{id}/']['get']['parameters']
    assert request_parameters_schema[0]['name'] == 'include'
    assert request_parameters_schema[0]['description'].endswith(': members')


def test_post():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = '__all__'

    class ProjectViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

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
            model = Project
            fields = '__all__'

    class ProjectViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    request_body_schema = swagger['paths']['/projects/{id}/']['put']['parameters'][0]['schema']['properties']
    assert 'id' in request_body_schema['data']['properties']
    assert 'type' in request_body_schema['data']['properties']
    assert 'attributes' in request_body_schema['data']['properties']
    assert list(request_body_schema['data']['properties']['attributes']['properties'].keys()) == ['name', 'archived']
    assert 'relationships' in request_body_schema['data']['properties']
    assert list(request_body_schema['data']['properties']['relationships']['properties'].keys()) == ['members']


class OtherMember(models.Model):
    other_id = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)


class OtherProject(models.Model):
    other_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    archived = models.BooleanField()
    members = models.ManyToManyField(OtherMember)


def test_get__other_id():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = OtherProject
            fields = '__all__'

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = OtherProject.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{other_id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == 'string'
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name', 'archived']
    assert 'relationships' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['relationships']['properties'].keys()) == ['members']
    members = response_schema['data']['properties']['relationships']['properties']['members']
    assert members['properties']['data']['items']['properties']['id']['type'] == 'string'


def test_get__id_based_on_pk():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = OtherProject
            fields = ['name']

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = OtherProject.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{other_id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == 'string'
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name']


def test_post__strip_read_only_fields():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = '__all__'
            read_only_fields = ['archived', 'members']

    class ProjectViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    request_body_schema = swagger['paths']['/projects/']['post']['parameters'][0]['schema']['properties']
    assert 'id' not in request_body_schema['data']['properties']
    assert 'type' in request_body_schema['data']['properties']
    assert 'attributes' in request_body_schema['data']['properties']
    assert list(request_body_schema['data']['properties']['attributes']['properties'].keys()) == ['name']
    assert 'relationships' not in request_body_schema['data']['properties']


def test_post__mark_as_required():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = '__all__'
            extra_kwargs = {
                'name': {'required': True},
                'archived': {'required': False},
                'members': {'required': True},
            }

    class ProjectViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    request_body_schema = swagger['paths']['/projects/']['post']['parameters'][0]['schema']['properties']
    assert set(request_body_schema['data']['required']) == {'type', 'attributes', 'relationships'}
    assert request_body_schema['data']['properties']['attributes']['required'] == ['name']
    assert request_body_schema['data']['properties']['relationships']['required'] == ['members']
    members_schema = request_body_schema['data']['properties']['relationships']['properties']['members']
    assert members_schema['required'] == ['data']
    assert set(members_schema['properties']['data']['items']['required']) == {'type', 'id'}


def test_get__strip_write_only():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = '__all__'
            extra_kwargs = {
                'name': {'write_only': False},
                'archived': {'write_only': True},
                'members': {'write_only': True},
            }

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert 'type' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name']
    assert 'relationships' not in response_schema['data']['properties']


def test_post__x_properties():
    class XPropertiesSwaggerAutoSchema(view_inspectors.SwaggerAutoSchema):
        field_inspectors = [
            drf_yasg_json_api.inspectors.NameFormatFilter,
            drf_yasg_json_api.inspectors.XPropertiesFilter,
            drf_yasg_json_api.inspectors.InlineSerializerInspector,
            drf_yasg_json_api.inspectors.IDIntegerFieldInspector,
            drf_yasg_json_api.inspectors.ManyRelatedIDIntegerFieldInspector,
            drf_yasg.inspectors.RelatedFieldInspector,
            drf_yasg.inspectors.SimpleFieldInspector,
            drf_yasg.inspectors.StringDefaultFieldInspector,
        ]

    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = '__all__'
            extra_kwargs = {
                'name': {'read_only': True},
                'archived': {'read_only': True},
                'members': {'write_only': True},
            }

    class ProjectViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = XPropertiesSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

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
