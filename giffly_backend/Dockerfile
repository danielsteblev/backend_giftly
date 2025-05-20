FROM python:3.11.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование только requirements.txt сначала
COPY requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Создание директорий для статических и медиа файлов
RUN mkdir -p /app/static /app/media

# Копирование проекта
COPY . .

# Сборка статических файлов
RUN python manage.py collectstatic --noinput

# Запуск приложения
CMD ["gunicorn", "giffly_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--config", "gunicorn_config.py"]