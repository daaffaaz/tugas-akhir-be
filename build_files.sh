#!/bin/bash

pip install --break-system-packages -r requirements.txt

DJANGO_SETTINGS_MODULE=config.settings.production python manage.py collectstatic --no-input
