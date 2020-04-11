import operator

from unittest import mock

import drf_yasg.inspectors
import pytest

from django.db import models
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework import mixins
from rest_framework import routers
from rest_framework import viewsets
from rest_framework_json_api import django_filters
from rest_framework_json_api import filters
from rest_framework_json_api import pagination
from rest_framework_json_api import parsers
from rest_framework_json_api import relations
from rest_framework_json_api import renderers
from rest_framework_json_api import serializers

import drf_yasg_json_api.inspectors

from tests import compatibility


class BasicSwaggerAutoSchema(drf_yasg_json_api.inspectors.SwaggerAutoSchema):
    field_inspectors = [
        drf_yasg_json_api.inspectors.NamesFormatFilter,
        drf_yasg_json_api.inspectors.InlineSerializerSmartInspector,
        drf_yasg_json_api.inspectors.IntegerIDFieldInspector,
        drf_yasg_json_api.inspectors.IntegerPrimaryKeyRelatedFieldInspector,
        drf_yasg_json_api.inspectors.ManyRelatedFieldInspector,
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
    members = models.ManyToManyField(Member, related_name='projects')
    owner_member = models.ForeignKey(Member, on_delete=models.DO_NOTHING)


def test_get__fallback_to_rest():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = ('id', 'name', 'archived', 'members')

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
            fields = ('id', 'name', 'archived', 'members')

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
    assert response_schema['data']['properties']['type']['pattern'] == 'projects'
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name', 'archived']
    assert 'relationships' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['relationships']['properties'].keys()) == ['members']
    members_schema = response_schema['data']['properties']['relationships']['properties']['members']['properties']
    assert members_schema['data']['items']['properties']['id']['type'] == 'string'
    assert members_schema['data']['items']['properties']['type']['pattern'] == 'members'


def test_get__pagination():
    class SwaggerAutoSchemaWithPagination(BasicSwaggerAutoSchema):
        paginator_inspectors = [
            drf_yasg_json_api.inspectors.DjangoRestResponsePagination,
            drf_yasg.inspectors.DjangoRestResponsePagination,
            drf_yasg.inspectors.CoreAPICompatInspector,
        ]

    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = ('id', 'name', 'archived', 'members')

    class ProjectViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = SwaggerAutoSchemaWithPagination
        pagination_class = pagination.JsonApiPageNumberPagination

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

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


def test_get__included():
    class MemberSerializer(serializers.ModelSerializer):
        # projects = serializers.ResourceRelatedField(many=True, read_only=True)

        class Meta:
            model = Member
            fields = ['first_name', 'last_name', 'projects']

    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = ('id', 'name', 'archived', 'members')

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
    included_members_schema = response_schema['included']['properties']['members']['properties']
    assert 'projects' in included_members_schema['relationships']['properties']

    request_parameters_schema = swagger['paths']['/projects/{id}/']['get']['parameters']
    assert request_parameters_schema[0]['name'] == 'include'
    assert request_parameters_schema[0]['description'].endswith(': members')


def test_post():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = ('id', 'name', 'archived', 'members')

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
            fields = ('id', 'name', 'archived', 'members')

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


class MemberWithCustomID(models.Model):
    custom_id = models.BigIntegerField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)


class ProjectWithCustomID(models.Model):
    custom_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    archived = models.BooleanField()
    members = models.ManyToManyField(MemberWithCustomID, related_name='projects')
    owner_member = models.ForeignKey(MemberWithCustomID, on_delete=models.DO_NOTHING, related_name='owned_projects')


@pytest.mark.parametrize(
    'read_only', (
        True,
        False,
    )
)
def test_get__auto_related_resource(read_only):
    """
    Correctly select id from non default pk field for both model and related models
    """
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = ProjectWithCustomID
            fields = ('custom_id', 'name', 'archived', 'members', 'owner_member')
            read_only_fields = ['members', 'owner_member'] if read_only else []

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = ProjectWithCustomID.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{custom_id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == 'string'
    assert response_schema['data']['properties']['id']['format'] == 'int32'
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name', 'archived']
    assert 'relationships' in response_schema['data']['properties']
    relationships_schema = response_schema['data']['properties']['relationships']['properties']
    assert list(relationships_schema.keys()) == ['members', 'owner-member']
    members_schema = relationships_schema['members']['properties']
    assert members_schema['data']['items']['properties']['id']['type'] == 'string'
    assert members_schema['data']['items']['properties']['id']['format'] == 'int64'
    assert members_schema['data']['items']['properties']['type']['pattern'] == 'member-with-custom-ids'
    owner_member_schema = relationships_schema['owner-member']['properties']
    assert owner_member_schema['data']['properties']['id']['type'] == 'string'
    assert owner_member_schema['data']['properties']['id']['format'] == 'int64'
    assert owner_member_schema['data']['properties']['type']['pattern'] == 'member-with-custom-ids'


@pytest.mark.parametrize(
    'read_only', (
        True,
        False,
    )
)
def test_get__auto_related_resource__reverse(read_only):
    """
    Correctly select id from non default pk field for both model and related models
    """
    class MemberSerializer(serializers.ModelSerializer):
        class Meta:
            model = MemberWithCustomID
            fields = ('custom_id', 'first_name', 'last_name', 'projects', 'owned_projects')
            read_only_fields = ['projects', 'owned_projects'] if read_only else []

    class MemberViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = MemberWithCustomID.objects.all()
        serializer_class = MemberSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'members', MemberViewSet, **compatibility._basename_or_base_name('members'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/members/{custom_id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == 'string'
    assert response_schema['data']['properties']['id']['format'] == 'int64'
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['first-name', 'last-name']
    assert 'relationships' in response_schema['data']['properties']
    relationships_schema = response_schema['data']['properties']['relationships']['properties']
    assert list(relationships_schema.keys()) == ['projects', 'owned-projects']
    assert relationships_schema['projects']['properties']['data']['items']['properties']['id']['type'] == 'string'
    assert relationships_schema['projects']['properties']['data']['items']['properties']['id']['format'] == 'int32'
    assert relationships_schema['owned-projects']['properties']['data']['items']['properties']['id']['type'] == 'string'
    assert relationships_schema['owned-projects']['properties']['data']['items']['properties']['id']['format'] == \
        'int32'


class ProjectWithCustomIDAndExtraProperties(ProjectWithCustomID):
    @property
    def one_member(self):
        return

    @property
    def many_members(self):
        return


@pytest.mark.parametrize(
    'serializer_field,expect_array', (
        (relations.SerializerMethodResourceRelatedField(model=MemberWithCustomID, source='get_member', read_only=True),
         False),
        (relations.SerializerMethodResourceRelatedField(model=MemberWithCustomID, source='get_members', read_only=True,
                                                        many=True),
         True),
        (relations.ResourceRelatedField(model=MemberWithCustomID, source='one_member', read_only=True),
         False),
        (relations.ResourceRelatedField(model=MemberWithCustomID, source='many_members', read_only=True, many=True),
         True),
        (relations.SerializerMethodResourceRelatedField(queryset=MemberWithCustomID.objects.all(), source='get_member'),
         False),
        # Once again: bug of SerializerMethodResourceRelatedField – currently give args invalid for this field class
        # (relations.SerializerMethodResourceRelatedField(queryset=MemberWithCustomID.objects.all(),
        #                                                 source='get_members', many=True),
        #  True),
        (relations.ResourceRelatedField(queryset=MemberWithCustomID.objects.all(), source='one_member'),
         False),
        (relations.ResourceRelatedField(queryset=MemberWithCustomID.objects.all(), source='many_members', many=True),
         True),
    )
)
def test_get__manual_related_resource(serializer_field, expect_array):
    """
    Support off combinations of related resources fields – they do supply models or don't.
    """
    class ProjectSerializer(serializers.ModelSerializer):
        member_relation = serializer_field

        class Meta:
            model = ProjectWithCustomIDAndExtraProperties
            fields = ['name', 'archived', 'member_relation']

        def get_member(self):
            pass

        def get_members(self):
            pass

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = ProjectWithCustomID.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{custom_id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == "string"
    assert response_schema['data']['properties']['id']['format'] == "int32"
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name', 'archived']
    assert 'relationships' in response_schema['data']['properties']
    relation_schema = response_schema['data']['properties']['relationships']['properties']['member-relation']

    if expect_array:
        assert 'items' in relation_schema['properties']['data']
        data_schema = relation_schema['properties']['data']['items']['properties']
    else:
        assert 'properties' in relation_schema['properties']['data']
        data_schema = relation_schema['properties']['data']['properties']

    assert data_schema['id']['type'] == 'string'
    assert data_schema['id']['format'] == 'int64'


def test_get__id_based_on_pk():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = ProjectWithCustomID
            fields = ['name']

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = ProjectWithCustomID.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(None, True)

    response_schema = swagger['paths']['/projects/{custom_id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == 'string'
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name']


def test_post__strip_read_only_fields():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = ('id', 'name', 'archived', 'members')
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
            fields = ('id', 'name', 'archived', 'members')
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
            fields = ('id', 'name', 'archived', 'members')
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


@mock.patch('rest_framework.settings.api_settings.URL_FIELD_NAME', 'obj_url')
def test_get__data_links_self():

    class ProjectSerializer(serializers.ModelSerializer):
        obj_url = serializers.HyperlinkedIdentityField(view_name='any')

        class Meta:
            model = Project
            fields = ('id', 'obj_url')

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
    assert 'links' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['links']['properties'].keys()) == ['self']


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
            model = Project
            fields = ('id', 'name', 'archived', 'members')
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


def test_get__filter():
    class FilterSwaggerAutoSchema(BasicSwaggerAutoSchema):
        filter_inspectors = [drf_yasg_json_api.inspectors.DjangoFilterInspector]

    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = ('id', 'name', 'archived', 'members')

    class ProjectViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
        queryset = Project.objects.all()
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

    swagger = generator.get_schema(None, True)

    request_parameters_schema = swagger['paths']['/projects/']['get']['parameters']
    assert request_parameters_schema[0]['name'] == 'filter[archived]'
