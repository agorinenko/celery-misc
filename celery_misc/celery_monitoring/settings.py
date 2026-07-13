from celery_misc import django_utils

TASK_REPOSITORY_CACHE_IN_SEC = django_utils.import_from_settings('TASK_REPOSITORY_CACHE_IN_SEC', default=3600)
TASK_REPOSITORY_CACHE_KEY = django_utils.import_from_settings('TASK_REPOSITORY_CACHE_KEY', default='CELERY_MISC_TASK_REPOSITORY')