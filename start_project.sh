#!/bin/bash

# 1. Убедиться, что Docker Desktop запущен
if ! docker info > /dev/null 2>&1; then
  echo "Запустите Docker Desktop и попробуйте снова."
  exit 1
fi

# 2. Активировать виртуальную среду
VENV_PATH="/Users/ilinkonstantin/Documents/GitHub/Backend/venv/bin"
if [ -d "$VENV_PATH" ]; then
  cd "$VENV_PATH"
  source activate
else
  echo "Виртуальная среда не найдена по пути $VENV_PATH"
  exit 1
fi

# 3. Запуск Docker Compose
DOCKER_COMPOSE_PATH="/Users/ilinkonstantin/Documents/GitHub/Backend/datacenter/docker/docker-compose.yml"
if [ -f "$DOCKER_COMPOSE_PATH" ]; then
  docker compose -f "$DOCKER_COMPOSE_PATH" up -d
else
  echo "Файл Docker Compose не найден по пути $DOCKER_COMPOSE_PATH"
  exit 1
fi

# 4. Запуск Django сервера
DJANGO_PATH="/Users/ilinkonstantin/Documents/GitHub/Backend/datacenter"
if [ -d "$DJANGO_PATH" ]; then
  cd "$DJANGO_PATH"
  python manage.py runserver
else
  echo "Путь к Django проекту не найден: $DJANGO_PATH"
  exit 1
fi