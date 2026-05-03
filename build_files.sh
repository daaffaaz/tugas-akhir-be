#!/bin/bash

pip install --break-system-packages -r requirements/base.txt

python manage.py build_faiss_index --verbosity 1

DJANGO_SETTINGS_MODULE=config.settings.production python manage.py collectstatic --no-input
