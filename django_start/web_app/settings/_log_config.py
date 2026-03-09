import os
from pathlib import Path

from envparse import env

from web_app.settings.utils import parse_str_to_list

LOG_LEVEL = env.str('LOGGING_DEFAULT_LEVEL', default='DEBUG')
LOGGING_DEFAULT_HANDLER = parse_str_to_list('LOGGING_DEFAULT_HANDLER', default=['console'])
ENV_TYPE = env.str('ENV', default='DEV')

LOG_DIR = os.path.join(Path(__file__).parents[2], 'log')
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

log_sql = env.bool('LOG_SQL', default=False)
if log_sql:
    django_db_log_cfg = {
        'handlers': ['sql_console'],
        'level': 'DEBUG',
        'propagate': False,
    }
else:
    django_db_log_cfg = {
        'handlers': ['null'],
        'level': 'WARNING'
    }

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        }
    },
    'formatters': {
        'sql': {
            'format': '[SQL] %(duration).3f sec | %(sql)s',
        },
        'default': {
            'format': '%(levelname)s %(name)s %(asctime)s %(module)s %(message)s',
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 7,
            'filename': f'{LOG_DIR}/{ENV_TYPE}.log',
            'formatter': 'default',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
        'sql_console': {
            'class': 'logging.StreamHandler',
            'formatter': 'sql'
        },
        'null': {
            'class': 'logging.NullHandler',
        }
    },
    'loggers': {
        'django.db.backends': django_db_log_cfg,
        '': {
            'handlers': LOGGING_DEFAULT_HANDLER,
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django.template': {
            'handlers': LOGGING_DEFAULT_HANDLER,
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': LOGGING_DEFAULT_HANDLER,
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django': {
            'handlers': LOGGING_DEFAULT_HANDLER,
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'py.warnings': {
            'handlers': LOGGING_DEFAULT_HANDLER,
            'level': 'WARNING',
            'propagate': False,
        },
        'django.utils.autoreload': {
            'level': 'WARNING',  # или 'ERROR' или 'CRITICAL'
            'handlers': LOGGING_DEFAULT_HANDLER,
            # 'propagate': False,
        },
    }
}
