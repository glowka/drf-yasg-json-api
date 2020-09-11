from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework import mixins
from rest_framework import routers
from rest_framework import viewsets
from rest_framework_json_api import parsers
from rest_framework_json_api import renderers
from rest_framework_json_api import serializers

from tests import base
from tests import compatibility
from tests import models as test_models


class IncludedStringPathMemberSerializer(serializers.ModelSerializer):
    # projects = serializers.ResourceRelatedField(many=True, read_only=True)

    class Meta:
        model = test_models.Member
        fields = ['first_name', 'last_name', 'projects']


def test_included__string_path():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')

        included_serializers = {
            'members': 'tests.test_schema.test_get_included.IncludedStringPathMemberSerializer',
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
    assert 'included' in response_schema
    assert 'members' in response_schema['included']['properties']

    request_parameters_schema = swagger['paths']['/projects/{id}/']['get']['parameters']
    assert request_parameters_schema[0]['name'] == 'include'
    assert request_parameters_schema[0]['description'].endswith(': members')


class IncludedRecursiveMemberSerializer(serializers.ModelSerializer):
    # projects = serializers.ResourceRelatedField(many=True, read_only=True)

    class Meta:
        model = test_models.Member
        fields = ['first_name', 'last_name', 'projects']

    included_serializers = {
        'projects': 'tests.test_schema.test_get_included.IncludedRecursiveProjectSerializer',
    }


class IncludedRecursiveProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = test_models.Project
        fields = ('id', 'name', 'archived', 'members', 'sub_projects')

    included_serializers = {
        'members': 'tests.test_schema.test_get_included.IncludedRecursiveMemberSerializer',
        'sub_projects': 'self',
    }


def test_included__recursive():
    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = IncludedRecursiveProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'included' in response_schema
    assert 'members' in response_schema['included']['properties']
    assert 'projects' in response_schema['included']['properties']
    included_members_schema = response_schema['included']['properties']['members']['properties']
    assert 'projects' in included_members_schema['relationships']['properties']
    included_projects_schema = response_schema['included']['properties']['projects']['properties']
    assert 'sub-projects' in included_projects_schema['relationships']['properties']
    assert 'members' in included_projects_schema['relationships']['properties']

    request_parameters_schema = swagger['paths']['/projects/{id}/']['get']['parameters']
    assert request_parameters_schema[0]['name'] == 'include'
    assert request_parameters_schema[0]['description'].endswith(
        ': sub-projects [recursive], members, members.projects [recursive through: members.projects]'
    )
