import os
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, status, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db
from services.file_service import FileService
from repositories.file_repository import FileRepository
from schemas.file_metadata import FileMetadataResponse

router = APIRouter(prefix="/api/v1/files", tags=["Files"])

@router.post("/upload", response_model=FileMetadataResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    folder: str = Form("products"),
    db: Session = Depends(get_db)
):
    if folder not in ["products", "suppliers"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid folder category.")
    service = FileService(db)
    return await service.upload_file(file, folder=folder)

@router.get("", response_model=List[FileMetadataResponse])
def get_all_files(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    repo = FileRepository(db)
    return repo.get_all(skip=skip, limit=limit)

@router.get("/{file_id}", response_model=FileMetadataResponse)
def get_file_metadata(file_id: int, db: Session = Depends(get_db)):
    repo = FileRepository(db)
    db_file = repo.get_by_id(file_id)
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return db_file

@router.get("/{file_id}/download")
def download_file(file_id: int, db: Session = Depends(get_db)):
    repo = FileRepository(db)
    db_file = repo.get_by_id(file_id)
    if not db_file or not os.path.exists(db_file.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File or storage record not found.")
    
    return FileResponse(
        path=db_file.file_path,
        media_type=db_file.content_type,
        filename=db_file.original_filename
    )

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: int, db: Session = Depends(get_db)):
    service = FileService(db)
    service.delete_file(file_id)
    return None