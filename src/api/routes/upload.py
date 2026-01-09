"""File upload API for multi-file handling."""

from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel

from src.services.file_processor import (
    get_file_processor,
    ProcessedFile,
    FileCategory,
    get_file_category,
)
from src.utils.logger import logger


router = APIRouter(prefix="/api/v1", tags=["upload"])


class FileUploadResponse(BaseModel):
    """Response model for file upload."""

    filename: str
    category: str
    mime_type: str
    size: int
    success: bool
    error: str | None = None
    # For text files: character count
    text_length: int | None = None
    # For images: base64 data included
    has_image: bool = False


class UploadedFileContext(BaseModel):
    """File context for chat."""

    filename: str
    category: str
    # Text content for non-image files
    text_content: str | None = None
    # Image data for vision API
    image_base64: str | None = None
    image_mime_type: str | None = None


# Temporary storage for uploaded files (per session)
# In production, use Redis or database
uploaded_files: dict[str, ProcessedFile] = {}


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a single file.
    Args:
        file: Uploaded file
    Returns:
        Processing result
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    # Check file category first
    category = get_file_category(file.filename)
    if category == FileCategory.UNSUPPORTED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: txt, md, pdf, docx, csv, xlsx, py, js, ts, png, jpg, gif, etc.",
        )

    try:
        content = await file.read()
        processor = get_file_processor()
        result = await processor.process(file.filename, content)

        if result.is_success:
            # Store for later use with chat
            uploaded_files[file.filename] = result
            logger.info(f"File uploaded: {file.filename} ({result.category.value})")

        return FileUploadResponse(
            filename=result.filename,
            category=result.category.value,
            mime_type=result.mime_type,
            size=result.size,
            success=result.is_success,
            error=result.error,
            text_length=len(result.text_content) if result.text_content else None,
            has_image=result.has_image,
        )

    except Exception as e:
        logger.error(f"Upload failed for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/multiple", response_model=list[FileUploadResponse])
async def upload_multiple_files(files: list[UploadFile] = File(...)):
    """Upload and process multiple files.
    Args:
        files: List of uploaded files
    Returns:
        List of processing results
    """
    results = []
    processor = get_file_processor()

    for file in files:
        if not file.filename:
            results.append(
                FileUploadResponse(
                    filename="unknown",
                    category="unsupported",
                    mime_type="",
                    size=0,
                    success=False,
                    error="Filename required",
                )
            )
            continue

        try:
            content = await file.read()
            result = await processor.process(file.filename, content)

            if result.is_success:
                uploaded_files[file.filename] = result

            results.append(
                FileUploadResponse(
                    filename=result.filename,
                    category=result.category.value,
                    mime_type=result.mime_type,
                    size=result.size,
                    success=result.is_success,
                    error=result.error,
                    text_length=(
                        len(result.text_content) if result.text_content else None
                    ),
                    has_image=result.has_image,
                )
            )

        except Exception as e:
            logger.error(f"Upload failed for {file.filename}: {e}")
            results.append(
                FileUploadResponse(
                    filename=file.filename,
                    category="unsupported",
                    mime_type="",
                    size=0,
                    success=False,
                    error=str(e),
                )
            )

    return results


@router.get("/upload/{filename}", response_model=UploadedFileContext)
async def get_file_context(filename: str):
    """Get uploaded file context for chat.
    Args:
        filename: Uploaded filename
    Returns:
        File context with text or image data
    """
    if filename not in uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")

    file = uploaded_files[filename]

    return UploadedFileContext(
        filename=file.filename,
        category=file.category.value,
        text_content=file.text_content,
        image_base64=file.image_base64 if file.has_image else None,
        image_mime_type=file.mime_type if file.has_image else None,
    )


@router.delete("/upload/{filename}")
async def delete_uploaded_file(filename: str):
    """Delete an uploaded file.
    Args:
        filename: Filename to delete
    Returns:
        Success message
    """
    if filename not in uploaded_files:
        raise HTTPException(status_code=404, detail="File not found")

    del uploaded_files[filename]
    logger.info(f"File deleted: {filename}")

    return {"message": f"File {filename} deleted"}


@router.get("/upload")
async def list_uploaded_files():
    """List all uploaded files.
    Returns:
        List of uploaded file info
    """
    return {
        "files": [
            {
                "filename": f.filename,
                "category": f.category.value,
                "size": f.size,
                "has_text": f.has_text,
                "has_image": f.has_image,
            }
            for f in uploaded_files.values()
        ]
    }


@router.delete("/upload")
async def clear_uploaded_files():
    """Clear all uploaded files.
    Returns:
        Success message
    """
    count = len(uploaded_files)
    uploaded_files.clear()
    logger.info(f"Cleared {count} uploaded files")

    return {"message": f"Cleared {count} files"}
