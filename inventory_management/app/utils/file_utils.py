import os
import uuid
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

def validate_file(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")

    ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = {".jpg", ".jpeg", ".png", ".pdf"}
    allowed_mimes = {"image/jpeg", "image/png", "application/pdf"}

    if ext not in allowed_extensions or file.content_type not in allowed_mimes:
        raise HTTPException(status_code=400, detail="Unsupported file type or extension.")

    return ext

def save_upload_to_disk(file: UploadFile, subfolder: str = "products") -> tuple[str, str, int]:
    ext = validate_file(file)
    unique_filename = f"{uuid.uuid4()}{ext}"

    upload_dir = os.path.abspath("uploads")
    target_folder = os.path.join(upload_dir, subfolder)
    os.makedirs(target_folder, exist_ok=True)

    file_path = os.path.join(target_folder, unique_filename)

    file_size = 0
    max_size = 5 * 1024 * 1024  # 5 MB

    with open(file_path, "wb") as buffer:
        while chunk := file.file.read(1024 * 1024):
            file_size += len(chunk)
            if file_size > max_size:
                buffer.close()
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise HTTPException(status_code=413, detail="File exceeds 5MB limit.")
            buffer.write(chunk)

    relative_path = os.path.relpath(file_path, upload_dir)
    return unique_filename, relative_path, file_size

def delete_file_from_disk(relative_path: str):
    if not relative_path:
        return
    full_path = os.path.join("uploads", relative_path)
    if os.path.exists(full_path):
        os.remove(full_path)