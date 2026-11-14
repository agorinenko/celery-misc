import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        CELERY_EAGER=True,
        DATABASES={},
        INSTALLED_APPS=[],
    )
    django.setup()
