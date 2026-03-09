from envparse import env


PAGE_SIZE = env.int('PAGE_SIZE', default=20)
MAX_PAGE_SIZE = env.int('MAX_PAGE_SIZE', default=2000)

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'PAGE_SIZE': PAGE_SIZE,
    'MAX_PAGE_SIZE': MAX_PAGE_SIZE,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle'
    ],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseFormParser',
        'djangorestframework_camel_case.parser.CamelCaseMultiPartParser',
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
    ),
    'JSON_UNDERSCOREIZE': {
        "ignore_fields": ("meta",),
    },
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler'
}
