## drf-yasg-json-api - ***drf-yasg*** meets ***JSON API***

[![build-status-image]][travis]
[![coverage-status-image]][codecov]
[![pypi-version]][pypi]

Automated generation of Swagger/OpenAPI 2.0 ***JSON API*** specifications from Django Rest Framework endpoints.

This package makes [drf-yasg Yet Another Swagger Generator](https://github.com/axnsan12/drf-yasg) and 
[Django REST framework JSON API](https://github.com/django-json-api/django-rest-framework-json-api) play together.

#### Table of Contents
<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->


- [Compatibility](#compatibility)
- [Installation](#installation)
- [Quickstart](#quickstart)
  - [Extending drg-yasg configuration](#extending-drg-yasg-configuration)
  - [Renderers and parsers](#renderers-and-parsers)
- [Supported features](#supported-features)
  - [`data` field – `id`, `type`, `relationships`, `attributes` structure](#data-field--id-type-relationships-attributes-structure)
  - [`included` field and `include` query param](#included-field-and-include-query-param)
  - [`filter` query param](#filter-query-param)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->


### Compatibility

- Django REST Framework JSON API: `2.4`, `2.5`, `2.6`, `2.7`, `2.8`, `3.0`, `3.1`
- Drf-yasg: `1.4`, `1.5`, `1.6`, `1.7.0`, `1.7.1`


- Django REST Framework: `3.7`, `3.8`, `3.9`, `3.10`, `3.11`
- Django: `2.0`, `2.1`, `2.2`, `3.0`
- Python: `3.5`, `3.6`, `3.7`, `3.8`

### Installation

```
pip install -U drf_yasg_json_api
```

### Quickstart


#### Extending drg-yasg configuration
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

Apply following changes:
```
SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'drf_yasg_json_api.view_inspectors.SwaggerJSONAPISchema',  # Overridden

    'DEFAULT_FIELD_INSPECTORS': [
        'drf_yasg_json_api.inspectors.NameFormatFilter',  # Replaces CamelCaseJSONFilter
        'drf_yasg.inspectors.RecursiveFieldInspector',
        'drf_yasg_json_api.inspectors.XPropertiesFilter',  # Added 
        'drf_yasg_json_api.inspectors.InlineSerializerInspector',  # Replaces ReferencingSerializerInspector
        'drf_yasg_json_api.inspectors.IDFieldInspector',  # Added
        'drf_yasg.inspectors.ChoiceFieldInspector',
        'drf_yasg.inspectors.FileFieldInspector',
        'drf_yasg.inspectors.DictFieldInspector',
        'drf_yasg.inspectors.JSONFieldInspector',
        'drf_yasg.inspectors.HiddenFieldInspector',
        'drf_yasg_json_api.inspectors.ManyRelatedFieldInspector',  # Added 
        'drf_yasg.inspectors.RelatedFieldInspector',
        'drf_yasg.inspectors.SerializerMethodFieldInspector',
        'drf_yasg.inspectors.SimpleFieldInspector',
        'drf_yasg.inspectors.StringDefaultFieldInspector',

    ],
    'DEFAULT_FILTER_INSPECTORS': [
        'drf_yasg_json_api.inspectors.DjangoFilterInspector',  # Added (optional), requires django_filter 
        'drf_yasg.inspectors.CoreAPICompatInspector',
    ],
}
```

#### Renderers and parsers

JSON API schema of your view's response or request will be generated if you use `django-rest-framework-json-api`'s  
`JSONAPIRenderer` or `JSONAPIParser` respectively. 

But since you have already used them to *render* or *parse*, not just to *generate schema* (haven't you?), 
you probably only need to alter the configuration as described above.    
 
### Supported features

Fields and query params extraction follows Django REST framework JSON API.

The request/response schema will consist of:
    
- #### `data` field – `id`, `type`, `relationships`, `attributes` structure

    Schema based on view's main serializer:
    - `id` – `id` field or other serializer field that matches the model `pk` field
    - `type` – serializer's model JSON API resource name
    - `relationships` – all serializer fields of  `RelatedField` and `ManyRelatedField` class
    - `attributes` – all other serializer fields

- #### `included` field and `include` query param
   
    Schema based on serializers defined in `included_serializer` attribute of view's main serializer where each one is 
    treated in the same way as view's main serializer (`data` field).
  
- #### `filter` query param

    If view uses `django_filters.DjangoFilterBackend` as filter backend,
    schema of `filter[]` query param will be generated based on view's `filterset_fields` attribute.   


[build-status-image]: https://secure.travis-ci.org/glowka/drf-yasg-json-api.svg?branch=master
[travis]: https://travis-ci.org/glowka/drf-yasg-json-api?branch=master
[coverage-status-image]: https://img.shields.io/codecov/c/github/glowka/drf-yasg-json-api/master.svg
[codecov]: https://codecov.io/github/glowka/drf-yasg-json-api?branch=master
[pypi-version]: https://img.shields.io/pypi/v/drf_yasg_json_api.svg
[pypi]: https://pypi.org/project/drf_yasg_json_api/

