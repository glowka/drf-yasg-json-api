### drf-yasg-json-api - Swagger generator for JSON API

[![build-status-image]][travis]
[![coverage-status-image]][codecov]
[![pypi-version]][pypi]

Automated generation of real Swagger/OpenAPI 2.0 schemas for **JSON API** Django Rest Framework endpoints.


#### Compatible with

- Django REST Framework JSON API: 2.4-2.8, 3.0, 3.1
- Drf-yasg: 1.4, 1.5, 1.6, 1.7.0, 1.7.1


- Django REST Framework: 3.7, 3.8, 3.9, 3.10, 3.11
- Django: 2.0, 2.1, 2.2, 3.0
- Python: 3.5-3.8

### Installation

```
pip install -U drf_yasg_json_api

```

### Quickstart

Assuming you are using drf-yasg configuration like below (which is drf-yasg default):
```

SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'drf_yasg.inspectors.SwaggerAutoSchema',

    'DEFAULT_FIELD_INSPECTORS': [
        'drf_yasg.inspectors.CamelCaseJSONFilter',
        'drf_yasg.inspectors.RecursiveFieldInspector',
        'drf_yasg.inspectors.ReferencingSerializerInspector',
        'drf_yasg.inspectors.ChoiceFieldInspector',
        'drf_yasg.inspectors.FileFieldInspector',
        'drf_yasg.inspectors.DictFieldInspector',
        'drf_yasg.inspectors.JSONFieldInspector',
        'drf_yasg.inspectors.HiddenFieldInspector',
        'drf_yasg.inspectors.RelatedFieldInspector',
        'drf_yasg.inspectors.SerializerMethodFieldInspector',
        'drf_yasg.inspectors.SimpleFieldInspector',
        'drf_yasg.inspectors.StringDefaultFieldInspector',
    ],
    'DEFAULT_FILTER_INSPECTORS': [
        'drf_yasg.inspectors.CoreAPICompatInspector',
    ],
}
```

Apply following changes
```
SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'drf_yasg_json_api.view_inspectors.SwaggerJSONAPISchema',  # Replaces drf_yasg default

    'DEFAULT_FIELD_INSPECTORS': [
        'drf_yasg_json_api.inspectors.JSONAPIFormatFilter',  # Replaces CamelCaseJSONFilter
        'drf_yasg.inspectors.RecursiveFieldInspector',
        'drf_yasg_json_api.inspectors.AttributesEnhancingFilter',  # Added 
        'drf_yasg_json_api.inspectors.JSONAPISerializerInspector',  # Replaces ReferencingSerializerInspector
        'drf_yasg_json_api.inspectors.JSONAPIIDFieldInspector', # Added
        'drf_yasg.inspectors.ChoiceFieldInspector',
        'drf_yasg.inspectors.FileFieldInspector',
        'drf_yasg.inspectors.DictFieldInspector',
        'drf_yasg.inspectors.JSONFieldInspector',
        'drf_yasg.inspectors.HiddenFieldInspector',
        'drf_yasg_json_api.inspectors.JSONAPIM2MFieldInspector',  # Added 
        'drf_yasg.inspectors.RelatedFieldInspector',
        'drf_yasg.inspectors.SerializerMethodFieldInspector',
        'drf_yasg.inspectors.SimpleFieldInspector',
        'drf_yasg.inspectors.StringDefaultFieldInspector',

    ],
    'DEFAULT_FILTER_INSPECTORS': [
        'drf_yasg_json_api.inspectors.JSONAPIDjangoFilterInspector',
        'drf_yasg.inspectors.CoreAPICompatInspector', # Added
    ],
}
```

[build-status-image]: https://secure.travis-ci.org/glowka/drf-yasg-json-api.svg?branch=master
[travis]: https://travis-ci.org/glowka/drf-yasg-json-api?branch=master
[coverage-status-image]: https://img.shields.io/codecov/c/github/glowka/drf-yasg-json-api/master.svg
[codecov]: https://codecov.io/github/glowka/drf-yasg-json-api?branch=master
[pypi-version]: https://img.shields.io/pypi/v/drf_yasg_json_api.svg
[pypi]: https://pypi.org/project/drf_yasg_json_api/

