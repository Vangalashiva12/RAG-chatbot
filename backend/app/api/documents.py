import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_admin
from app.models.document import Document
from app.models.user import User


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


ALLOWED_FILE_TYPES = {
    ".pdf",
    ".docx",
    ".txt",
    ".csv",
    ".md",
    ".pptx"
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    file_extension = os.path.splitext(file.filename)[1].lower()

    if file_extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_FILE_TYPES)}"
        )

    file_content = await file.read()

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 10 MB limit"
        )

    upload_directory = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "uploads"
        )
    )

    os.makedirs(upload_directory, exist_ok=True)

    unique_filename = f"{uuid.uuid4()}{file_extension}"

    file_path = os.path.join(
        upload_directory,
        unique_filename
    )

    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    document = Document(
        filename=file.filename,
        file_path=file_path,
        file_type=file_extension,
        file_size=len(file_content),
        uploaded_by=current_admin.id,
        status="UPLOADED"
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return {
        "message": "Document uploaded successfully",
        "document_id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "status": document.status
    }