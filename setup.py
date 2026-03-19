from os.path import dirname, join

import setuptools

LONG_DESCRIPTION = """
# Celery_misc. Библиотека утилитарных модулей для Celery на Python

Помогает избавиться от дублирования кода и решает рутинные задачи при работе с Celery.
"""


def long_description():
    try:
        return open(join(dirname(__file__), 'README.md')).read()
    except IOError:
        return LONG_DESCRIPTION


setuptools.setup(
    name='celery-misc',
    version='1.0.5',
    author='Anton Gorinenko',
    author_email='anton.gorinenko@gmail.com',
    description='Python async tools for Celery',
    long_description=long_description(),
    keywords='python, utils, celery',
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages('.', exclude=['tests', 'django_start', 'docs']),
    classifiers=[
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'celery',
        'Django',
        'django-json-widget',
        'uuid6'
    ],
    extras_require={
        'test': [
            'pytest',
            'python-dotenv',
            'envparse',
            'pytest-asyncio',
            'pytest-mock',
            'pytest-env'
        ]
    },
    python_requires='>=3.10',
)
