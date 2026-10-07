
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunker import split_text
from app.services.document_processor import extract_text_from_file
from app.services.embedding_service import embedding_service


def ingest_document(document_id: int) -> None:
    db: Session = SessionLocal()

    try:
        document = db.query(Document).filter(
            Document.id == document_id
        ).first()

        if document is None:
            return

        document.status = "PROCESSING"
        db.commit()

        # Extract document text
        extracted_text = extract_text_from_file(
            document.file_path,
            document.file_type
        )

        if not extracted_text or not extracted_text.strip():
            raise ValueError("No text could be extracted")

        # Split into chunks
        chunks = split_text(
            extracted_text,
            chunk_size=1000,
            chunk_overlap=200
        )

        if not chunks:
            raise ValueError("No chunks were generated")

        # Generate embeddings
        embeddings = embedding_service.generate_embeddings(chunks)

        if len(embeddings) != len(chunks):
            raise ValueError("Embedding count does not match chunk count")

        # Remove old chunks before saving replacements
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).delete(synchronize_session=False)

        document.extracted_text = extracted_text

        for index, (content, embedding) in enumerate(
            zip(chunks, embeddings)
        ):
            db.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    content=content,
                    character_count=len(content),
                    embedding=embedding
                )
            )

        document.status = "COMPLETED"
        db.commit()

        print(f"Document {document_id} ingestion completed")

    except Exception as error:
        db.rollback()

        document = db.query(Document).filter(
            Document.id == document_id
        ).first()

        if document is not None:
            document.status = "FAILED"
            db.commit()

        print(f"Document {document_id} ingestion failed: {error}")
        raise

    finally:
        db.close()
