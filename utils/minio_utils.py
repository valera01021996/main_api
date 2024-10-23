import os
import io
from datetime import timedelta
from minio import Minio
from config import BUCKET_NAME, MINIO_ACCESS_KEY, MINIO_SECRET_KEY


minio_client = Minio(
    "minio.tsc.uz:9000",
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)


def upload_to_minio(local_file_path, generated_file_name):
    with open(local_file_path, 'rb') as file_data:
        file_stat = os.stat(local_file_path)
        minio_client.put_object(BUCKET_NAME, generated_file_name, io.BytesIO(file_data.read()),
                                length=file_stat.st_size)
    url = minio_client.presigned_get_object(BUCKET_NAME, generated_file_name, expires=timedelta(hours=2))
    return url