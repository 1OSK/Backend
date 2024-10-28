import logging
from django.conf import settings
from minio import Minio
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.response import Response

# Создаем логгер
logger = logging.getLogger('myapp')  # Замените 'myapp' на имя вашего приложения

def process_file_upload(file_object: InMemoryUploadedFile, client, image_name):
    try:
        # Загружаем объект в MinIO
        client.put_object(settings.AWS_STORAGE_BUCKET_NAME, image_name, file_object, file_object.size)
        return f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{image_name}"
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла {image_name}: {e}")  # Логируем ошибку
        return {"error": str(e)}

def add_pic(new_stock, pic):
    client = Minio(
        endpoint=settings.AWS_S3_ENDPOINT_URL.replace('http://', ''),  # Удаляем 'http://' из URL
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        secure=settings.MINIO_USE_SSL
    )
    
    if not pic:
        logger.warning("Нет файла для изображения.")
        return {"error": "Нет файла для изображения."}

    img_obj_name = f"{new_stock.id}.png"
    
    try:
        # Загрузка изображения в бакет
        client.put_object(
            bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
            object_name=img_obj_name,
            data=pic,
            length=pic.size
        )
        image_url = f"{settings.AWS_S3_ENDPOINT_URL}/{settings.AWS_STORAGE_BUCKET_NAME}/{img_obj_name}"
        new_stock.image_url = image_url  # Сохраняем URL изображения
        new_stock.save()

        logger.info(f"Изображение успешно загружено: {image_url}")
        return {"message": "Изображение успешно загружено.", "image_url": image_url}
    except Exception as e:
        logger.error(f"Ошибка при загрузке изображения {img_obj_name}: {e}")
        return {"error": str(e)}