from envparse import env

from web_app.settings._redis import REDIS_CONNECTION_STRING

ENV_TYPE = env.str('ENV')

if ENV_TYPE == "DEV":
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_CONNECTION_STRING,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
