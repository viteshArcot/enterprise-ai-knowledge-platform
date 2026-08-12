"""Documents endpoints."""

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app.core.dependencies import get_document_service
from app.schemas.document import DocumentResponse
from app.services.document import DocumentService
from app.config.settings import settings

router = APIRouter()


import hashlib

@router.post("/", response_model=DocumentResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str | None, Form()] = None,
    document_service: DocumentService = Depends(get_document_service),
):
    """Upload a document to be ingested."""
    # Ensure a directory exists for storage
    upload_dir = str(settings.UPLOAD_DIRECTORY)
    os.makedirs(upload_dir, exist_ok=True)
    
    import uuid
    safe_filename = f"{uuid.uuid4().hex}_{file.filename or 'unknown'}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Compute SHA256 incrementally and save the file
    sha256_hash = hashlib.sha256()
    file_size = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(8192):
            sha256_hash.update(chunk)
            f.write(chunk)
            file_size += len(chunk)
            if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
                f.close()
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                from app.core.exceptions import FileTooLargeError
                raise FileTooLargeError(settings.MAX_UPLOAD_SIZE_BYTES)
            
    file_hash = sha256_hash.hexdigest()

    # Check for duplicate
    existing_doc = await document_service.get_document_by_hash(file_hash)
    if existing_doc:
        # File exists, remove the duplicate uploaded file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as e:
                import logging
                logging.getLogger("app.api").warning(f"Failed to remove duplicate temp file {file_path}: {e}")
            
        import logging
        logging.getLogger("app.api").info(
            "document_duplicate_detected",
            extra={"file_hash": file_hash, "existing_id": str(existing_doc.id)}
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "is_duplicate": True,
                "existing_document_id": str(existing_doc.id),
                "message": "Document already exists."
            }
        )

    # Need the full content for the parsing in background (since process_document_async takes bytes)
    # Actually wait, `process_document_async` currently takes `content: bytes`. 
    # Let's read it back into memory for the background task for now, as that's how it's currently built.
    with open(file_path, "rb") as f:
        file_content = f.read()

    doc_title = title or file.filename or "Untitled Document"

    # Create the document record
    document = await document_service.create_document(
        title=doc_title,
        file_name=file.filename or "unknown",
        file_type=file.content_type or "application/octet-stream",
        file_size_bytes=len(file_content),
        file_path=file_path,
        metadata_={"file_hash": file_hash}
    )

    # Process in background
    background_tasks.add_task(
        document_service.process_document_async,
        document_id=document.id,
        content=file_content,
        file_name=file.filename or "unknown",
    )

    return document


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    document_service: DocumentService = Depends(get_document_service),
) -> list[DocumentResponse]:
    """List all documents."""
    return await document_service.list_documents(limit=limit, offset=offset)


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    document_service: DocumentService = Depends(get_document_service),
):
    """Download the original document file."""
    import os
    import logging
    from fastapi.responses import FileResponse
    from fastapi import HTTPException
    
    doc = await document_service.get_document(document_id)
    file_path = doc.file_path
    
    if file_path and not os.path.exists(file_path) and file_path.startswith("/tmp/uploads/"):
        fallback_path = os.path.join(str(settings.UPLOAD_DIRECTORY), os.path.basename(file_path))
        if os.path.exists(fallback_path):
            file_path = fallback_path
    
    if not file_path or not os.path.exists(file_path):
        logging.getLogger("app.api").warning("document_download_failed_not_found", extra={"document_id": str(document_id)})
        raise HTTPException(status_code=404, detail="File not found on server.")
        
    logging.getLogger("app.api").info("document_downloaded", extra={"document_id": str(document_id)})
    return FileResponse(path=file_path, filename=doc.file_name, media_type=doc.file_type)


@router.post("/{document_id}/reindex", response_model=DocumentResponse, status_code=202)
async def reindex_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Reindex a document."""
    import logging
    from fastapi import HTTPException
    
    try:
        doc = await document_service.reindex_document(document_id)
        
        import os
        file_path = doc.file_path
        
        if file_path and not os.path.exists(file_path) and file_path.startswith("/tmp/uploads/"):
            fallback_path = os.path.join(str(settings.UPLOAD_DIRECTORY), os.path.basename(file_path))
            if os.path.exists(fallback_path):
                file_path = fallback_path
                
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Physical file missing, cannot reindex.")
            
        with open(file_path, "rb") as f:
            file_content = f.read()
            
        background_tasks.add_task(
            document_service.process_document_async,
            document_id=doc.id,
            content=file_content,
            file_name=doc.file_name,
        )
        
        logging.getLogger("app.api").info("document_reindex_requested", extra={"document_id": str(document_id)})
        return doc
    except ValueError as e:
        logging.getLogger("app.api").warning("document_reindex_conflict", extra={"document_id": str(document_id), "error": str(e)})
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    """Get a specific document."""
    return await document_service.get_document(document_id)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    document_service: DocumentService = Depends(get_document_service),
) -> None:
    """Delete a document."""
    import logging
    logging.getLogger("app.api").info("document_delete_requested", extra={"document_id": str(document_id)})
    await document_service.delete_document(document_id)
