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
- [Features](#features)
  - [Main request/response JSON API schema support](#main-requestresponse-json-api-schema-support)
    - [`data` field with `id`, `type`, `relationships`, `attributes` structure](#data-field-with-id-type-relationships-attributes-structure)
    - [`included` field and `include` query param](#included-field-and-include-query-param)
    - [`filter` query param](#filter-query-param)
  - [Additional](#additional)
    - [Stripping `write_only` fields from response and `read_only` from request](#stripping-write_only-fields-from-response-and-read_only-from-request)
    - [Extra `x-writeOnly` and `x-readOnly` properties](#extra-x-writeonly-and-x-readonly-properties)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->


### Compatibility

- Django REST Framework JSON API: `2.8`, `3.0`, `3.1`
- Drf-yasg: `1.6`, `1.7.0`, `1.7.1`


- Django REST Framework: `3.8`, `3.9`, `3.10`, `3.11`
- Django: `2.0`, `2.1`, `2.2`, `3.0`, `3.1`
- Python: `3.6`, `3.7`, `3.8`

### Installation

```
pip install -U drf-yasg-json-api
```

### Quickstart

First follow [drf-yasg quickstart](https://github.com/axnsan12/drf-yasg#1-quickstart),
then extend the configuration in following way.

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
    'DEFAULT_PAGINATOR_INSPECTORS': [
        'drf_yasg.inspectors.DjangoRestResponsePagination',
        'drf_yasg.inspectors.CoreAPICompatInspector',
    ],
}
```

Apply following changes:
```
SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'drf_yasg_json_api.inspectors.SwaggerAutoSchema',  # Overridden

    'DEFAULT_FIELD_INSPECTORS': [
        'drf_yasg_json_api.inspectors.NamesFormatFilter',  # Replaces CamelCaseJSONFilter
        'drf_yasg.inspectors.RecursiveFieldInspector',
        'drf_yasg_json_api.inspectors.XPropertiesFilter',  # Added 
        'drf_yasg_json_api.inspectors.InlineSerializerSmartInspector',  # Replaces ReferencingSerializerInspector
        'drf_yasg_json_api.inspectors.IntegerIDFieldInspector',  # Added
        'drf_yasg.inspectors.ChoiceFieldInspector',
        'drf_yasg.inspectors.FileFieldInspector',
        'drf_yasg.inspectors.DictFieldInspector',
        'drf_yasg.inspectors.JSONFieldInspector',
        'drf_yasg.inspectors.HiddenFieldInspector',
        'drf_yasg_json_api.inspectors.ManyRelatedFieldInspector',  # Added
        'drf_yasg_json_api.inspectors.IntegerPrimaryKeyRelatedFieldInspector',  # Added 
        'drf_yasg.inspectors.RelatedFieldInspector',
        'drf_yasg.inspectors.SerializerMethodFieldInspector',
        'drf_yasg.inspectors.SimpleFieldInspector',
        'drf_yasg.inspectors.StringDefaultFieldInspector',

    ],
    'DEFAULT_FILTER_INSPECTORS': [
        'drf_yasg_json_api.inspectors.DjangoFilterInspector',  # Added (optional), requires django_filter 
        'drf_yasg.inspectors.CoreAPICompatInspector',
    ],
    'DEFAULT_PAGINATOR_INSPECTORS': [
        'drf_yasg_json_api.inspectors.DjangoRestResponsePagination',  # Added
        'drf_yasg.inspectors.DjangoRestResponsePagination',
        'drf_yasg.inspectors.CoreAPICompatInspector',
    ],
}
```

#### Renderers and parsers

JSON API schema of your view's response or request will be generated if you use `django-rest-framework-json-api`'s  
`JSONAPIRenderer` or `JSONAPIParser` respectively. 

But since you have already used them to *render* or *parse*, not just to *generate schema* (haven't you?), 
you probably only need to alter the configuration as described above.    
 
That's it!

### Features

Fields and query params extraction follows Django REST framework JSON API.

#### Main request/response JSON API schema support:
    
- ##### `data` field with `id`, `type`, `relationships`, `attributes` structure

    Schema based on view's main serializer. It accessed through view's `get_serializer` method, 
    *the same way `drf-yasg` does it*.
    
    Use `GenericAPIView` or `APIView` and define `get_serializer` manually. 
    
    Fields and their source: 
    - `id` – `id` field **or** other serializer field that matches the model `pk` 
    field **or** in-the-fly generated serializer field for model `pk`
    - `type` – serializer's model JSON API resource name **or** view's resource name,
     *the same way Django REST framework JSON API does it* 
    - `relationships` – all serializer fields of  `RelatedField` and `ManyRelatedField` class
    - `attributes` – all other serializer fields

- ##### `included` field and `include` query param
   
    Schema based on serializers defined in `included_serializer` attribute of view's main serializer where each one is 
    treated in the same way as view's main serializer (`data` field).
  
- ##### `filter` query param

    If view uses `django_filters.DjangoFilterBackend` as filter backend,
    schema of `filter[]` query param will be generated based on view's `filterset_fields` attribute.   
  
- #####  pagination

    If view uses `JsonApiPageNumberPagination` or `JsonApiLimitOffsetPagination` as `pagination_class`, 
    schema of `links` and `meta`, consistent with those pagination types, will be generated.    

#### Additional

##### Support for `swagger_auto_schema` decorator of `drf-yasg`

JSON API schema is also generated for success responses (statuses 2XX) defined manually using `responses` argument
 of `swagger_auto_schema` decorator.   

##### Stripping `write_only` fields from response and `read_only` from request

`drf_yasg_json_api.inspectors.InlineSerializerSmartInspector` strips fields inaccessible in request/response to
 provide view of fields that are **really** available to use.

You can revert to traditional `drf-yasg` view of all serializer fields in both response and request by replacing this
inspector with `drf_yasg_json_api.inspectors.InlineSerializerInspector` 


##### Extra `x-writeOnly` and `x-readOnly` properties

`drf_yasg_json_api.inspectors.XPropertiesFilter` uses:
 - `x-readOnly` to mark read only fields even if they are nested
 - `x-witeOonly` adds missing support for write only fields


[build-status-image]: https://secure.travis-ci.org/glowka/drf-yasg-json-api.svg?branch=master
[travis]: https://travis-ci.org/glowka/drf-yasg-json-api?branch=master
[coverage-status-image]: https://img.shields.io/codecov/c/github/glowka/drf-yasg-json-api/master.svg
[codecov]: https://codecov.io/github/glowka/drf-yasg-json-api?branch=master
[pypi-version]: https://img.shields.io/pypi/v/drf_yasg_json_api.svg
[pypi]: https://pypi.org/project/drf_yasg_json_api/

