from django.db import models
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework import mixins
from rest_framework import routers
from rest_framework import viewsets
from rest_framework_json_api import parsers
from rest_framework_json_api import renderers
from rest_framework_json_api import serializers

from tests import compatibility


class Member(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)


class Project(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(Member)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = '__all__'


def test_get__fallback_to_rest():

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer

    projects_router = routers.DefaultRouter()
    projects_router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=projects_router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert list(response_schema.keys()) == ['id', 'name', 'members']


def test_get():

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]

    projects_router = routers.DefaultRouter()
    projects_router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=projects_router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == 'string'
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name']
    assert 'relationships' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['relationships']['properties'].keys()) == ['members']


def test_get__included():
    class IncludedProjectSerializer(ProjectSerializer):
        included_serializers = {
            'members': MemberSerializer,
        }

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = IncludedProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]

    projects_router = routers.DefaultRouter()
    projects_router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=projects_router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'included' in response_schema
    assert 'Member' in response_schema['included']['properties']
    request_parameters_schema = swagger['paths']['/projects/{id}/']['get']['parameters']
    assert request_parameters_schema[0]['name'] == 'include'
    assert request_parameters_schema[0]['description'].endswith(': members')


def test_post():

    class ProjectViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]

    projects_router = routers.DefaultRouter()
    projects_router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=projects_router.urls)

    swagger = generator.get_schema(None, True)

    request_body_schema = swagger['paths']['/projects/']['post']['parameters'][0]['schema']['properties']
    assert 'id' not in request_body_schema['data']['properties']
    assert 'type' in request_body_schema['data']['properties']
    assert 'attributes' in request_body_schema['data']['properties']
    assert list(request_body_schema['data']['properties']['attributes']['properties'].keys()) == ['name']
    assert 'relationships' in request_body_schema['data']['properties']
    assert list(request_body_schema['data']['properties']['relationships']['properties'].keys()) == ['members']


class OtherMember(models.Model):
    other_id = models.IntegerField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)


class OtherProject(models.Model):
    other_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(OtherMember)


class OtherProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = OtherProject
        fields = '__all__'


def test_get__other_id():

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = OtherProject.objects.all()
        serializer_class = OtherProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]

    projects_router = routers.DefaultRouter()
    projects_router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=projects_router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{other_id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == 'string'
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name']
    assert 'relationships' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['relationships']['properties'].keys()) == ['members']
    members = response_schema['data']['properties']['relationships']['properties']['members']
    assert members['properties']['data']['items']['properties']['id']['type'] == 'string'
