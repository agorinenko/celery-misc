import os

# pylint: disable=all
bind = '0.0.0.0:8000'
workers = int(os.getenv('WORKERS_COUNT', default=3))
timeout = int(os.getenv('WORKERS_TIMEOUT', default=30))
