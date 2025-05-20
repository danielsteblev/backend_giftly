FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Добавьте это вручную, если rest_framework не указан в requirements.txt:
RUN pip install djangorestframework

# Копируем исходники
COPY . .

# Делаем скрипт запуска исполняемым
RUN chmod +x /app/entrypoint.sh

# Запуск приложения
ENTRYPOINT ["/app/entrypoint.sh"]