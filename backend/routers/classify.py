from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from typing import Optional
from pathlib import Path
import json
import uuid
from urllib.parse import quote
from services import bedrock_service, document_service, file_validation, viewer_service
from services.taxonomy_service import load_taxonomy
from models.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix='/api')
UPLOADS_DIR = Path(__file__).resolve().parent.parent / 'uploads'
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.get('/taxonomy')
def get_taxonomy():
    return load_taxonomy()


def _resolve_upload(filename: str) -> Path:
    safe = Path(filename).name  # block path traversal
    file_path = UPLOADS_DIR / safe
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='File not found. Please upload it again.')
    return file_path


def _display_name(stored: str) -> str:
    # stored names look like "<8-char id>_<original name>"
    return stored.split('_', 1)[1] if len(stored) > 9 and stored[8] == '_' else stored


@router.get('/document/{filename}/view')
def view_document(filename: str):
    """Opens the uploaded file inside the browser (PDF inline, Excel/Word/CSV/TXT as HTML)."""
    file_path = _resolve_upload(filename)
    name = _display_name(file_path.name)
    if file_path.suffix.lower() == '.pdf':
        return FileResponse(path=file_path, media_type='application/pdf',
                            headers={'Content-Disposition': f'inline; filename="{name}"'})
    return HTMLResponse(viewer_service.render_html(file_path, name))


@router.get('/document/{filename}')
def get_document(filename: str):
    """Downloads the original uploaded file."""
    file_path = _resolve_upload(filename)
    return FileResponse(path=file_path, filename=_display_name(file_path.name))


@router.post('/classify')
async def classify(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    conversation_history: Optional[str] = Form('[]')
):
    try:
        history = json.loads(conversation_history or '[]')
    except json.JSONDecodeError:
        history = []

    doc_meta = None
    combined_text = text or ''
    effective_history = history

    if file:
        file_bytes = await file.read()
        pre_rej = file_validation.validate_file_pre_extract(file.filename, file_bytes)
        if pre_rej:
            return {
                "type": "chat",
                "message": pre_rej['message'],
                "rejected": True,
                "rejection_details": pre_rej,
                "document_metadata": {'filename': file.filename, 'size_bytes': len(file_bytes)}
            }
        stored_name = f"{uuid.uuid4().hex[:8]}_{Path(file.filename).name}"
        try:
            (UPLOADS_DIR / stored_name).write_bytes(file_bytes)
        except Exception:
            stored_name = None

        extracted = document_service.extract_text(file_bytes, file.filename)  # never raises
        doc_meta = extracted['metadata']
        if stored_name:
            q = quote(stored_name)
            doc_meta['stored_name'] = stored_name
            doc_meta['url'] = f'/api/document/{q}'
            doc_meta['view_url'] = f'/api/document/{q}/view'

        user_text = (text or '').strip()
        post_rej = file_validation.validate_file_post_extract(file.filename, file_bytes, extracted.get('text', ''), meta=doc_meta)
        if post_rej or doc_meta.get('is_empty', False) or len(file_bytes) == 0:
            return {
                "type": "chat",
                "message": post_rej['message'] if post_rej else f"File Not Accepted: '{file.filename}' is empty.",
                "rejected": True,
                "rejection_details": post_rej,
                "document_metadata": doc_meta
            }

        file_text = (
            f"[NEW FILE TO CLASSIFY: {file.filename}]\n"
            f"==================== FULL DOCUMENT CONTENT & PROFILE ====================\n"
            f"{extracted['text']}\n"
            f"=========================================================================\n"
        )
        instruction = (
            f"\nINSTRUCTION: Read the ENTIRE document profile and all extracted sections (Start, Middle, and End) of '{file.filename}' before classifying. "
            f"Do NOT judge early based on introductory framing or scenario examples in the first few lines. "
            f"Determine the exact industry, domain, and true document/artifact nature of '{file.filename}' directly from its full content, "
            f"and provide a complete, accurate 5-level taxonomy hierarchy, per-level rationales (especially Level 1 rationale), source traceability mappings, summary, and detailed explanation."
        )
        combined_text = (file_text + f"\nUser Note: {user_text}\n" + instruction) if user_text else (file_text + instruction)
        effective_history = history

    if not combined_text.strip():
        raise HTTPException(status_code=400, detail='Please provide a document or text to classify.')

    try:
        result = bedrock_service.classify(combined_text, effective_history)
    except Exception as e:
        # Graceful fallback: return as chat message rather than throwing 502
        result = {
            "type": "chat",
            "message": "I'm ready to assist. Please share the details, question, or document you would like to discuss or classify."
        }
    result['document_metadata'] = doc_meta
    return result


@router.post('/feedback')
def feedback(req: FeedbackRequest):
    # In production: save to DB. For now: acknowledge.
    return FeedbackResponse(message=f'Feedback recorded: {req.action}')


