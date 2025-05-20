#!/bin/bash

# Создаем директории для статики и медиа
mkdir -p /app/static /app/media

# Собираем статику
python manage.py collectstatic --noinput

# Запускаем Gunicorn
exec gunicorn giffly_backend.wsgi:application --bind 0.0.0.0:8000 --config gunicorn_config.py 