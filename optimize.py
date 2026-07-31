import os
import json
import hashlib
import boto3
from botocore.config import Config
from io import BytesIO
from PIL import Image, ImageOps
from os.path import relpath

RAW_PATH = "raw_photos"
OUTPUT_PATH = "static/photos"
CACHE_FILE = "data/cache.json"
JSON_OUTPUT = "data/photos.json"

R2_ACCOUNT_ID = "9fa88ac9f06117d72c8cd0e22600be35"
R2_ACCESS_KEY = "5a69cb268a40e337939d7e6f35e1217c"
R2_SECRET_KEY = "82dcacadcd39a622174e74f48cf1e086b46c8a33bf9751fbb1d80ddd43a4bb8f"
BUCKET_NAME = "guyee-fotosite"

R2_PUBLIC_DOMAIN = "https://pub-1835983be9494648986014e022bfe242.r2.dev"

def calculate_md5(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def get_r2_client():
    endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    return boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        config=Config(signature_version='s3v4')
    )

def upload_single_file_to_r2(s3_client, local_path, r2_key):
    try:
        s3_client.upload_file(
            local_path,
            BUCKET_NAME,
            r2_key,
            ExtraArgs={'ContentType': 'image/webp'}
        )
        print(f"Uploading to R2: {r2_key}")
        return True
    except Exception as e:
        print(f"Fail to upload to R2 {r2_key}: {e}")
        return False

def process_photos():
    os.makedirs(RAW_PATH, exist_ok=True)
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    cache_data = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        except Exception:
            cache_data = {}
    photo_list = []
    new_cache = {}
    processed_count = 0
    skipped_count = 0
    uploaded_count = 0

    print("connecting Cloudflare R2 ...")
    s3_client = get_r2_client()

    print("start checking raw_photos ...")

    for root, dirs, files in os.walk(RAW_PATH):
        rel_path = relpath(root, RAW_PATH)
        category = "all" if rel_path == "." else rel_path.replace("\\", "/")

        for filename in files:
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                continue
            file_path = os.path.join(root, filename)

            try:
                file_hash = calculate_md5(file_path)
            except Exception as e:
                print(f"fail to read {filename}: {e}")
                continue

            target_filename = f"{file_hash}.webp"
            target_path = os.path.join(OUTPUT_PATH, target_filename)

            r2_key = f"photos/{target_filename}"

            if R2_PUBLIC_DOMAIN.strip():
                domain = R2_PUBLIC_DOMAIN.rstrip('/')
                web_url = f"{domain}/{r2_key}"
            else:
                web_url = f"/{r2_key}"

            if file_hash in cache_data and os.path.exists(target_path):
                skipped_count += 1
                new_cache[file_hash] = target_filename
                
                upload_single_file_to_r2(s3_client, target_path, r2_key)
                uploaded_count += 1

                photo_list.append({
                    "name": target_filename,
                    "url": web_url,
                    "category": category
                })
                continue

            print(f"new added and zipping {category} - {filename}")
            try:
                with Image.open(file_path) as img:
                    img = ImageOps.exif_transpose(img)
                    img.thumbnail((1200, 1200))

                    img.save(target_path, format="WEBP", quality = 80)

                upload_single_file_to_r2(s3_client, target_path, r2_key)

                processed_count += 1
                uploaded_count += 1
                new_cache[file_hash] = target_filename
                photo_list.append({
                    "name": target_filename,
                    "url": web_url,
                    "category": category
                })
            except Exception as e:
                print(f" fail to zip {filename} {e}")

    with open(CACHE_FILE, "w", encoding = "utf-8") as f:
        json.dump(new_cache, f, indent=4)

    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(photo_list, f, indent=4)

    print(f"\n✨ Done! Processed: {processed_count}, Skipped: {skipped_count}")

if __name__ == "__main__":
    process_photos()        
