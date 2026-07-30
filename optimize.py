import os
import json
import hashlib
from io import BytesIO
from PIL import Image, ImageOps
from os.path import relpath

RAW_PATH = "raw_photos"
OUTPUT_PATH = "static/photos"
CACHE_FILE = "data/cache.json"
JSON_OUTPUT = "data/photos.json"

def calculate_md5(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

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
            web_url = f"/photos/{target_filename}"

            if file_hash in cache_data and os.path.exists(target_path):
                skipped_count += 1
                new_cache[file_hash] = target_filename
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

                processed_count += 1
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
