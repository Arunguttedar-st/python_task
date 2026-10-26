import os
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
from app.repositories.file_repository import FileRepository
from app.utils.file_utils import save_upload_to_disk, delete_file_from_disk

class FileService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FileRepository(db)

    def upload_file(self, file: UploadFile, subfolder: str = "products"):
        stored_filename, relative_path, file_size = save_upload_to_disk(file, subfolder)
        try:
            return self.repo.create(
                original_filename=file.filename,
                stored_filename=stored_filename,
                file_path=relative_path,
                content_type=file.content_type,
                file_size=file_size
            )
        except Exception as e:
            delete_file_from_disk(relative_path)
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    def get_file_metadata(self, file_id: int):
        file_meta = self.repo.get_by_id(file_id)
        if not file_meta:
            raise HTTPException(status_code=404, detail="File not found.")
        return file_meta

    def list_files(self, skip: int = 0, limit: int = 100):
        return self.repo.get_all(skip, limit)

    def get_file_path_for_download(self, file_id: int):
        file_meta = self.get_file_metadata(file_id)
        full_path = os.path.join("uploads", file_meta.file_path)
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Storage file missing.")
        return full_path, file_meta.original_filename, file_meta.content_type

    def delete_file(self, file_id: int):
        file_meta = self.get_file_metadata(file_id)
        delete_file_from_disk(file_meta.file_path)
        self.repo.delete(file_meta)
        return {"detail": "File deleted successfully."}