import django


def pytest_configure(config):
    from django.conf import settings

    settings.configure(
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            }
        },
        SITE_ID=1,
        SECRET_KEY='not very secret in tests',
        USE_I18N=True,
        USE_L10N=True,
        STATIC_URL='/static/',
        ROOT_URLCONF='tests.urls',
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
                'OPTIONS': {
                    "debug": True,  # We want template errors to raise
                }
            },
        ],
        MIDDLEWARE=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ),
        INSTALLED_APPS=(
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.staticfiles',
            'tests',
        ),
        PASSWORD_HASHERS=(
            'django.contrib.auth.hashers.MD5PasswordHasher',
        ),
        SWAGGER_SETTINGS={
            'DEFAULT_AUTO_SCHEMA_CLASS': 'drf_yasg_json_api.view_inspectors.SwaggerJSONAPISchema',

            'DEFAULT_FIELD_INSPECTORS': [
                'drf_yasg_json_api.inspectors.NameFormatFilter',
                'drf_yasg.inspectors.RecursiveFieldInspector',
                'drf_yasg_json_api.inspectors.XPropertiesFilter',
                'drf_yasg_json_api.inspectors.InlineSerializerInspector',
                'drf_yasg_json_api.inspectors.IDFieldInspector',
                'drf_yasg.inspectors.ChoiceFieldInspector',
                'drf_yasg.inspectors.FileFieldInspector',
                'drf_yasg.inspectors.DictFieldInspector',
                'drf_yasg.inspectors.JSONFieldInspector',
                'drf_yasg.inspectors.HiddenFieldInspector',
                'drf_yasg_json_api.inspectors.ManyRelatedFieldInspector',
                'drf_yasg.inspectors.RelatedFieldInspector',
                'drf_yasg.inspectors.SerializerMethodFieldInspector',
                'drf_yasg.inspectors.SimpleFieldInspector',
                'drf_yasg.inspectors.StringDefaultFieldInspector',

            ],
            'DEFAULT_FILTER_INSPECTORS': [
                'drf_yasg_json_api.inspectors.DjangoFilterInspector',
                'drf_yasg.inspectors.CoreAPICompatInspector',
            ],
        }
    )

    django.setup()
