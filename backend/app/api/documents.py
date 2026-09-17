import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import delete

from app.core.database import get_db
from app.core.permissions import require_admin
from app.models.document import Document
from app.models.user import User
from app.services.document_processor import extract_text_from_file

from app.services.chunker import split_text
from app.models.document_chunk import DocumentChunk


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

@router.post("/{document_id}/process")
def process_document(
    document_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    try:
        # Step 1: Mark document as processing
        document.status = "PROCESSING"
        db.commit()

        # Step 2: Extract text
        extracted_text = extract_text_from_file(
            document.file_path,
            document.file_type
        )

        if not extracted_text.strip():
            document.status = "FAILED"
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text could be extracted from the document"
            )

        # Step 3: Store extracted text
        document.extracted_text = extracted_text

        # Step 4: Split text into chunks
        chunks = split_text(
            extracted_text,
            chunk_size=1000,
            chunk_overlap=200
        )

        if not chunks:
            document.status = "FAILED"
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No chunks could be created from the document"
            )

        # Remove existing chunks if document is being reprocessed
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).delete(
            synchronize_session=False
        )


        # Step 5: Save chunks
        for index, chunk in enumerate(chunks):
            document_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                character_count=len(chunk)
            )

            db.add(document_chunk)

        # Step 6: Update document status
        document.status = "CHUNKED"

        db.commit()
        db.refresh(document)

        return {
            "message": "Document processed and chunked successfully",
            "document_id": document.id,
            "filename": document.filename,
            "status": document.status,
            "characters_extracted": len(extracted_text),
            "chunks_created": len(chunks)
        }

    except HTTPException:
        raise

    except Exception as error:
        db.rollback()

        document.status = "FAILED"
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(error)}"
        )