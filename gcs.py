
import os
import log
logger = log.get_logger()  # 로거

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="./config/gogole_credential.json"
    
from google.cloud import storage

bucket_name = os.environ.get("GOOGLE_BUCKET_NAME")
storage_client = storage.Client()
bucket = storage_client.get_bucket(bucket_name)

def upload(path_dir, filename, queue, formatted_date, delete=True):
    full_path = os.path.join(path_dir, queue, formatted_date, filename)
    blob = bucket.blob(f"raw/{queue}/{formatted_date}/{filename}")
    blob.upload_from_filename(full_path)

    logger.info(f"File {filename} uploaded to {blob.public_url}.")
    if delete:
        post_upload(full_path)

def upload_many(path_dir, filenames, queue, formatted_date):
    for filename in filenames:
        upload(path_dir, filename, queue, formatted_date)

def post_upload(full_path):
    try:
        os.remove(full_path)
    except FileNotFoundError:
        logger.error(f"경로 {full_path}에 파일이 존재하지 않습니다.")
    except Exception as e:
        logger.error(f"파일 삭제 중 오류가 발생했습니다: {e}")

"""TEST"""

# source_file_name = "sample.json"
# destination_blob_name = "sample1.json"

# upload(source_file_name, destination_blob_name)
