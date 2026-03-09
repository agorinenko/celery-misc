from envparse import env

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env.str("POSTGRES_DB"),
        'USER': env.str("POSTGRES_USER"),
        'PASSWORD': env.str("POSTGRES_PASSWORD"),
        'HOST': env.str("DB_HOST"),
        'PORT': env.int("DB_PORT"),
        'CONN_MAX_AGE': env.int('CONN_MAX_AGE', default=0),
        'CONN_HEALTH_CHECKS': env.int('CONN_HEALTH_CHECKS', default=False)
    }
}
