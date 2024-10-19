# minio.py
from django.conf import settings
from minio import Minio
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework.response import Response

def process_file_upload(file_object: InMemoryUploadedFile, client, image_name):
    try:
        client.put_object('something', image_name, file_object, file_object.size)
        return f"http://{settings.AWS_S3_ENDPOINT_URL}/{image_name}"
    except Exception as e:
        return {"error": str(e)}

def add_pic(new_stock, pic):
    client = Minio(
        endpoint=settings.AWS_S3_ENDPOINT_URL,
        access_key=settings.AWS_ACCESS_KEY_ID,
        secret_key=settings.AWS_SECRET_ACCESS_KEY,
        secure=settings.MINIO_USE_SSL
    )
    
    if not pic:
        return Response({"error": "Нет файла для изображения."})

    img_obj_name = f"{new_stock.id}.png"
    result = process_file_upload(pic, client, img_obj_name)

    if 'error' in result:
        return Response(result)

    new_stock.image_url = result  # или new_stock.url, в зависимости от вашего поля
    new_stock.save()

<<<<<<< Updated upstream
    return Response({"message": "Изображение успешно загружено."})
=======
    return {"message": "Изображение успешно загружено.", "image_url": result} 
>>>>>>> Stashed changes
