"""add document file hash

Revision ID: d72f48a9c631
Revises: cb0343edf7c6
Create Date: 2026-10-06 21:02:33.785174

"""

from typing import Sequence, Union
import hashlib
import os

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d72f48a9c631"
down_revision: Union[str, Sequence[str], None] = "cb0343edf7c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # ---------------------------------------------------------
    # 1. Add the column temporarily as nullable
    # ---------------------------------------------------------

    op.add_column(
        "documents",
        sa.Column(
            "file_hash",
            sa.String(length=64),
            nullable=True
        )
    )

    # ---------------------------------------------------------
    # 2. Get existing documents
    # ---------------------------------------------------------

    connection = op.get_bind()

    documents = connection.execute(
        sa.text(
            """
            SELECT id, file_path
            FROM documents
            """
        )
    ).fetchall()

    # ---------------------------------------------------------
    # 3. Calculate SHA-256 for existing files
    # ---------------------------------------------------------

    for document_id, file_path in documents:

        if not file_path or not os.path.exists(file_path):
            raise RuntimeError(
                f"File not found for document {document_id}: "
                f"{file_path}"
            )

        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as file:
            for chunk in iter(
                lambda: file.read(1024 * 1024),
                b""
            ):
                sha256_hash.update(chunk)

        file_hash = sha256_hash.hexdigest()

        connection.execute(
            sa.text(
                """
                UPDATE documents
                SET file_hash = :file_hash
                WHERE id = :document_id
                """
            ),
            {
                "file_hash": file_hash,
                "document_id": document_id
            }
        )

    # ---------------------------------------------------------
    # 4. Make file_hash NOT NULL
    # ---------------------------------------------------------

    op.alter_column(
        "documents",
        "file_hash",
        existing_type=sa.String(length=64),
        nullable=False
    )

    # ---------------------------------------------------------
    # 5. Create unique index
    # ---------------------------------------------------------

    op.create_index(
        op.f("ix_documents_file_hash"),
        "documents",
        ["file_hash"],
        unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_documents_file_hash"),
        table_name="documents"
    )

    op.drop_column(
        "documents",
        "file_hash"
    )