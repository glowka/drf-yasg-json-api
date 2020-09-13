import drf_yasg.inspectors

import drf_yasg_json_api.inspectors


class BasicSwaggerAutoSchema(drf_yasg_json_api.inspectors.SwaggerAutoSchema):
    field_inspectors = [
        drf_yasg_json_api.inspectors.NamesFormatFilter,
        drf_yasg_json_api.inspectors.JSONAPISerializerSmartInspector,
        drf_yasg.inspectors.ReferencingSerializerInspector,
        drf_yasg_json_api.inspectors.IntegerIDFieldInspector,
        drf_yasg_json_api.inspectors.IntegerPrimaryKeyRelatedFieldInspector,
        drf_yasg_json_api.inspectors.ManyRelatedFieldInspector,
        drf_yasg.inspectors.RelatedFieldInspector,
        drf_yasg.inspectors.SimpleFieldInspector,
        drf_yasg.inspectors.StringDefaultFieldInspector,
    ]
