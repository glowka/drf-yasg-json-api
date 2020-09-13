from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework import mixins
from rest_framework import routers
from rest_framework import viewsets
from rest_framework_json_api import parsers
from rest_framework_json_api import renderers
from rest_framework_json_api import serializers

from drf_yasg_json_api.deprecation import DrfYasgJsonApiDeprecationWarning
from tests import base
from tests import compatibility
from tests import models as test_models


def test_fallback_to_rest_api():
    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        swagger_schema = base.BasicSwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert list(response_schema.keys()) == ['id', 'name', 'archived', 'members']


def test_deprecate_universal_inline_serializer(recwarn):
    import drf_yasg.inspectors
    import drf_yasg_json_api.inspectors

    class SwaggerAutoSchema(drf_yasg_json_api.inspectors.SwaggerAutoSchema):
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

    class ProjectSerializer(serializers.ModelSerializer):
        class Meta:
            model = test_models.Project
            fields = ('id', 'name', 'archived', 'members')

    class ProjectViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
        queryset = test_models.Project.objects.all()
        serializer_class = ProjectSerializer
        renderer_classes = [renderers.JSONRenderer]
        parser_classes = [parsers.JSONParser]
        swagger_schema = SwaggerAutoSchema

    router = routers.DefaultRouter()
    router.register(r'projects', ProjectViewSet, **compatibility._basename_or_base_name('projects'))

    generator = OpenAPISchemaGenerator(info=openapi.Info(title="", default_version=""), patterns=router.urls)

    swagger = generator.get_schema(request=None, public=True)

    response_schema = swagger['paths']['/projects/{id}/']['get']['responses']['200']['schema']['properties']
    assert 'id' in response_schema['data']['properties']
    assert 'type' in response_schema['data']['properties']
    assert 'attributes' in response_schema['data']['properties']

    recwarn.pop(DrfYasgJsonApiDeprecationWarning)
