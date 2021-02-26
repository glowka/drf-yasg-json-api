0.8.1 (2021-02-26)
------------------ 
- Fix adding x-read-only property by XPropertiesFilter to be compatible with Multipart/FormData parser


0.8.0 (2020-09-13)
------------------

- Add support for generating schema from `responses` argument of 
`swagger_auto_schema`
- Add explicit support for `django==3.1` and `djangorestframework-jsonapi==3.2`
- Deprecate `InlineSerializerInspector` and `InlineSerializerSmartInspector` in favor
  of `JSONAPISerializerInspector` and `JSONAPISerializerSmartInspector`
  - to generate docs for JSON API views use `JSONAPISerializerInspector` 
    (or `JSONAPISerializerSmartInspector` to use *smart* feature described in README) 
  - to generate docs for **non** JSON API views use `drf-yasg` basic `ReferencingSerializerInspector`
    (or `InlineSerializerInspector` if you're using inline schema)
  - to generate docs for both JSON API and **non** JSON API use `drf-yasg-json-api` inspector followed
    by `drf-yasg` inspector, see default configuration in README 
  
0.7.1 (2020-06-16)
------------------

- Extend support of string-based `included_serializers` to handle 
  indirect recursion

0.7.0 (2020-06-13)
------------------

- Add support for string-based `included_serializers`
- Warn about missing `get_serializer` for view's list action

0.6.0 (2020-04-11)
------------------

- Add support for pagination
- Fix and refine resource type extraction from related fields

0.5.0 (2020-04-11)
------------------

- Split inspector files and move them to separate `inspectors` directory,
  `view_inspectors` import path still available for backward compatibility

0.4.0 (2020-04-08)
------------------

- Add support for manual (property based) relation extraction

0.3.0 (2020-04-08)
------------------

- Fix SerializerMethodResourceRelatedField bug

0.2.0 (2020-04-08)
------------------

- Refine names before posting information about package in public

0.1.0 (2020-04-08)
------------------

Initial public release 
