import pytest

from django.db import models
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework import mixins
from rest_framework import routers
from rest_framework import viewsets
from rest_framework_json_api import parsers
from rest_framework_json_api import relations
from rest_framework_json_api import renderers
from rest_framework_json_api import serializers

from tests import base
from tests import compatibility


class MemberWithCustomID(models.Model):
    custom_id = models.BigIntegerField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    class Meta:
        app_label = 'tests'


class ProjectWithCustomID(models.Model):
    custom_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    archived = models.BooleanField()
    members = models.ManyToManyField(MemberWithCustomID, related_name='projects')
    owner_member = models.ForeignKey(MemberWithCustomID, on_delete=models.DO_NOTHING, related_name='owned_projects')

    class Meta:
        app_label = 'tests'


@pytest.mark.parametrize(
    'read_only', (
        True,
        False,
    )
)
def test_related_resource(read_only):
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
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

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
def test_related_resource__reverse(read_only):
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
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'members', MemberViewSet, **compatibility._basename_or_base_name('members'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

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

    class Meta:
        app_label = 'tests'

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
        (relations.ResourceRelatedField(queryset=MemberWithCustomID.objects.all(), source='one_member'),
         False),
        (relations.ResourceRelatedField(queryset=MemberWithCustomID.objects.all(), source='many_members', many=True),
         True),
    )
)
def test_force_related_resource(serializer_field, expect_array):
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
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

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


def test_id_based_on_pk():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = ProjectWithCustomID
            fields = ['name']

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = ProjectWithCustomID.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/{custom_id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert response_schema['data']['properties']['id']['type'] == 'string'
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']
    assert list(response_schema['data']['properties']['attributes']['properties'].keys()) == ['name']
