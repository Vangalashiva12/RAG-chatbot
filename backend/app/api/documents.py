import hashlib
import os
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import require_admin
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.services.chunker import split_text
from app.services.document_processor import extract_text_from_file
from app.services.embedding_service import embedding_service
from app.services.search_service import semantic_search
from app.services.document_ingestion_services import ingest_document


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


# ============================================================
# Configuration
# ============================================================

ALLOWED_FILE_TYPES = {
    ".pdf",
    ".docx",
    ".txt",
    ".csv",
    ".md",
    ".pptx"
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ============================================================
# Response Schemas
# ============================================================

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    uploaded_by: int
    status: str

    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    uploaded_by: int
    status: str
    extracted_text: str | None
    chunk_count: int

    class Config:
        from_attributes = True


# ============================================================
# Upload Document
# ============================================================

@router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # --------------------------------------------------------
    # 1. Validate filename
    # --------------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    # --------------------------------------------------------
    # 2. Validate file extension
    # --------------------------------------------------------

    file_extension = os.path.splitext(
        file.filename
    )[1].lower()

    if file_extension not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file type. "
                f"Allowed types: {', '.join(ALLOWED_FILE_TYPES)}"
            )
        )

    # --------------------------------------------------------
    # 3. Read uploaded file
    # --------------------------------------------------------

    file_content = await file.read()

    # --------------------------------------------------------
    # 4. Validate file size
    # --------------------------------------------------------

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 10 MB limit"
        )

    # --------------------------------------------------------
    # 5. Generate SHA-256 file hash
    # --------------------------------------------------------

    file_hash = hashlib.sha256(
        file_content
    ).hexdigest()

    # --------------------------------------------------------
    # 6. Check for duplicate document
    # --------------------------------------------------------

    existing_document = (
        db.query(Document)
        .filter(
            Document.file_hash == file_hash
        )
        .first()
    )

    if existing_document:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Document already exists as "
                f"'{existing_document.filename}' "
                f"(document_id={existing_document.id})"
            )
        )

    # --------------------------------------------------------
    # 7. Create upload directory
    # --------------------------------------------------------

    upload_directory = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "uploads"
        )
    )

    os.makedirs(
        upload_directory,
        exist_ok=True
    )

    # --------------------------------------------------------
    # 8. Generate unique physical filename
    # --------------------------------------------------------

    unique_filename = (
        f"{uuid.uuid4()}{file_extension}"
    )

    file_path = os.path.join(
        upload_directory,
        unique_filename
    )

    # --------------------------------------------------------
    # 9. Save physical file
    # --------------------------------------------------------

    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    # --------------------------------------------------------
    # 10. Create database record
    # --------------------------------------------------------

    document = Document(
        filename=file.filename,
        file_path=file_path,
        file_type=file_extension,
        file_size=len(file_content),
        file_hash=file_hash,
        uploaded_by=current_admin.id,
        status="UPLOADED"
    )

    # --------------------------------------------------------
    # 11. Save database record
    # --------------------------------------------------------

    db.add(document)
    db.commit()
    db.refresh(document)

    background_tasks.add_task(
        ingest_document,
        document.id
    )


    # --------------------------------------------------------
    # 12. Return response
    # --------------------------------------------------------

    return {
        "message": "Document uploaded successfully",
        "document_id": document.id,
        "filename": document.filename,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "status": document.status
    }


# ============================================================
# List Documents
# ============================================================

@router.get(
    "/",
    response_model=list[DocumentResponse]
)
def list_documents(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    documents = (
        db.query(Document)
        .order_by(
            Document.created_at.desc()
        )
        .all()
    )

    return documents


# ============================================================
# Search Documents
# IMPORTANT:
# This route must come BEFORE /{document_id}
# ============================================================

@router.get("/search")
def search_documents(
    query: str,
    top_k: int = 5,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )

    if top_k < 1 or top_k > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be between 1 and 20"
        )

    try:
        results = semantic_search(
            query=query,
            db=db,
            top_k=top_k
        )

        return {
            "query": query,
            "results": [
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "character_count": chunk.character_count
                }
                for chunk in results
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(error)}"
        )


# ============================================================
# Get Document Details
# ============================================================

@router.get(
    "/{document_id}",
    response_model=DocumentDetailResponse
)
def get_document(
    document_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    chunk_count = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document.id
        )
        .count()
    )

    return DocumentDetailResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        uploaded_by=document.uploaded_by,
        status=document.status,
        extracted_text=document.extracted_text,
        chunk_count=chunk_count
    )


# ============================================================
# Process Document
# ============================================================

@router.post("/{document_id}/process")
def process_document(
    document_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    try:

        # -----------------------------------------------------
        # Step 1: Mark document as processing
        # -----------------------------------------------------

        document.status = "PROCESSING"
        db.commit()

        # -----------------------------------------------------
        # Step 2: Extract text
        # -----------------------------------------------------

        extracted_text = extract_text_from_file(
            document.file_path,
            document.file_type
        )

        if not extracted_text.strip():

            document.status = "FAILED"
            db.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No text could be extracted "
                    "from the document"
                )
            )

        # -----------------------------------------------------
        # Step 3: Store extracted text
        # -----------------------------------------------------

        document.extracted_text = extracted_text

        # -----------------------------------------------------
        # Step 4: Split text into chunks
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Step 5: Remove existing chunks
        # -----------------------------------------------------

        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).delete(
            synchronize_session=False
        )

        # -----------------------------------------------------
        # Step 6: Save new chunks
        # -----------------------------------------------------

        for index, chunk in enumerate(chunks):

            document_chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=index,
                content=chunk,
                character_count=len(chunk)
            )

            db.add(document_chunk)

        # -----------------------------------------------------
        # Step 7: Update document status
        # -----------------------------------------------------

        document.status = "CHUNKED"

        db.commit()
        db.refresh(document)

        return {
            "message": (
                "Document processed and "
                "chunked successfully"
            ),
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
            detail=(
                f"Document processing failed: {str(error)}"
            )
        )


# ============================================================
# Generate Document Embeddings
# ============================================================

@router.post("/{document_id}/embed")
def embed_document(
    document_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document.id
        )
        .order_by(
            DocumentChunk.chunk_index
        )
        .all()
    )

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No chunks found for this document"
        )

    try:

        texts = [
            chunk.content
            for chunk in chunks
        ]

        embeddings = (
            embedding_service.generate_embeddings(
                texts
            )
        )

        for chunk, embedding in zip(
            chunks,
            embeddings
        ):
            chunk.embedding = embedding

        db.commit()

        return {
            "message": (
                "Embeddings generated successfully"
            ),
            "document_id": document.id,
            "chunks_embedded": len(embeddings),
            "embedding_dimension": len(
                embeddings[0]
            )
        }

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Embedding generation failed: {str(error)}"
            )
        )


# ============================================================
# Delete Document
# ============================================================

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_document(
    document_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    try:

        # -----------------------------------------------------
        # 1. Delete document chunks
        # -----------------------------------------------------

        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).delete(
            synchronize_session=False
        )

        # -----------------------------------------------------
        # 2. Delete physical uploaded file
        # -----------------------------------------------------

        if document.file_path and os.path.exists(
            document.file_path
        ):
            os.remove(
                document.file_path
            )

        # -----------------------------------------------------
        # 3. Delete document record
        # -----------------------------------------------------

        db.delete(document)
        db.commit()

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Failed to delete document: {str(error)}"
            )
        )