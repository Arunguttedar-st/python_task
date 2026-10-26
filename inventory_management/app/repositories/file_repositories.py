from sqlalchemy.orm import Session
from app.models.file_metadata import FileMetadata

class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, original_filename: str, stored_filename: str, file_path: str, content_type: str, file_size: int):
        db_file = FileMetadata(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            content_type=content_type,
            file_size=file_size
        )
        self.db.add(db_file)
        self.db.commit()
        self.db.refresh(db_file)
        return db_file

    def get_by_id(self, file_id: int):
        return self.db.query(FileMetadata).filter(FileMetadata.id == file_id).first()

    def get_all(self, skip: int = 0, limit: int = 100):
        return self.db.query(FileMetadata).offset(skip).limit(limit).all()

    def delete(self, file_metadata: FileMetadata):
        self.db.delete(file_metadata)
        self.db.commit()