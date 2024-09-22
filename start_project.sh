#!/bin/bash

# 1. Убедиться, что Docker Desktop запущен
if ! docker info > /dev/null 2>&1; then
  echo "Запустите Docker Desktop и попробуйте снова."
  exit 1
fi

# 2. Активировать виртуальную среду
cd venv/bin/
source activate
# 3. Запуск Docker Compose
docker compose -f datacenter/docker/docker-compose.yml up -d

# 4. Запуск Django сервера
cd datacenter
python manage.py runserver