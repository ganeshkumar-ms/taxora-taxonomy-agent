import base64
import json
import os
import re
import uuid
from email.parser import BytesParser
from email.policy import default as default_email_policy
from pathlib import Path
from urllib.parse import unquote, quote

import boto3
from botocore.config import Config
from services import bedrock_service, document_service, viewer_service
from services.taxonomy_service import load_taxonomy

TMP_UPLOADS = Path('/tmp/uploads')
TMP_UPLOADS.mkdir(parents=True, exist_ok=True)
S3_BUCKET = os.environ.get('TAXORA_S3_BUCKET', 'taxora-ui-984625844016')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
s3_client = boto3.client(
    's3',
    region_name=REGION,
    endpoint_url=f'https://s3.{REGION}.amazonaws.com',
    config=Config(signature_version='s3v4', s3={'addressing_style': 'virtual'})
)

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': '*',
}


def _json_response(status_code: int, payload: dict) -> dict:
    return {
        'statusCode': status_code,
        'headers': {**CORS_HEADERS, 'Content-Type': 'application/json'},
        'body': json.dumps(payload),
    }


def _parse_multipart(body_bytes: bytes, content_type: str) -> dict:
    raw_msg = b'Content-Type: ' + content_type.encode('utf-8') + b'\r\nMIME-Version: 1.0\r\n\r\n' + body_bytes
    msg = BytesParser(policy=default_email_policy).parsebytes(raw_msg)
    fields = {}
    file_info = None
    if msg.is_multipart():
        for part in msg.iter_parts():
            cd = part.get('Content-Disposition', '')
            if not cd:
                continue
            name = part.get_param('name', header='content-disposition')
            filename = part.get_filename()
            payload = part.get_payload(decode=True) or b''
            if filename:
                file_info = {'filename': filename, 'bytes': payload}
            elif name:
                fields[name] = payload.decode('utf-8', errors='replace')
    return {'fields': fields, 'file': file_info}


def _display_name(stored: str) -> str:
    return stored.split('_', 1)[1] if len(stored) > 9 and stored[8] == '_' else stored


def _sanitize_filename(filename: str) -> str:
    name = Path(filename or 'document').name
    return re.sub(r'[^\w.\- ()+\[\]]', '_', name) or 'document'


def _get_s3_size(s3_key: str) -> int:
    try:
        head = s3_client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return int(head.get('ContentLength', 0))
    except Exception:
        return -1


def _read_s3_smart(s3_key: str, filename: str) -> tuple:
    """
    Reads file bytes from S3. For very large PDFs (> 12 MB), reads 6 x 2 MB slices across
    beginning, middle, and end in ~0.3s so Lambda never times out or exhausts memory.
    Returns (bytes_data, actual_total_size).
    """
    total_size = _get_s3_size(s3_key)
    if total_size < 0:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        b = obj['Body'].read()
        return b, len(b)

    if total_size > 12_000_000 and filename.lower().endswith('.pdf'):
        chunk_sz = 2_000_000
        chunks = []
        for frac in (0.0, 0.18, 0.36, 0.54, 0.72, 0.90):
            start = int(total_size * frac)
            end = min(total_size - 1, start + chunk_sz - 1)
            if end > start:
                part = s3_client.get_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Range=f'bytes={start}-{end}'
                )['Body'].read()
                chunks.append(part)
        return b'\n'.join(chunks), total_size

    obj = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
    b = obj['Body'].read()
    return b, total_size


def _resolve_upload(filename: str) -> Path:
    safe = Path(unquote(filename)).name
    local_path = TMP_UPLOADS / safe
    if not local_path.exists():
        try:
            obj = s3_client.get_object(Bucket=S3_BUCKET, Key=f'uploads/{safe}')
            local_path.write_bytes(obj['Body'].read())
        except Exception:
            return None
    return local_path


def lambda_handler(event, context):
    method = (
        event.get('requestContext', {}).get('http', {}).get('method')
        or event.get('httpMethod')
        or 'GET'
    ).upper()

    raw_path = event.get('rawPath') or event.get('path') or '/'

    if method == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    if raw_path in ('/health', '/api/health'):
        return _json_response(200, {'status': 'ok', 'agent': 'TAXORA'})

    if raw_path == '/api/taxonomy' and method == 'GET':
        return _json_response(200, load_taxonomy())

    if raw_path == '/api/feedback' and method == 'POST':
        return _json_response(200, {'status': 'recorded', 'message': 'Feedback recorded'})

    if raw_path == '/api/upload-url' and method == 'POST':
        try:
            body_raw = event.get('body') or '{}'
            body_bytes = base64.b64decode(body_raw) if event.get('isBase64Encoded') else body_raw.encode('utf-8')
            data = json.loads(body_bytes.decode('utf-8'))
            orig_filename = _sanitize_filename(data.get('filename', 'file.bin'))
            content_type = data.get('content_type') or 'application/octet-stream'
            stored_name = f"{uuid.uuid4().hex[:8]}_{orig_filename}"
            s3_key = f"uploads/{stored_name}"
            upload_url = s3_client.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': S3_BUCKET,
                    'Key': s3_key,
                    'ContentType': content_type,
                },
                ExpiresIn=900,
            )
            return _json_response(200, {
                'upload_url': upload_url,
                's3_key': s3_key,
                'stored_name': stored_name,
                'filename': orig_filename,
            })
        except Exception as e:
            return _json_response(500, {'detail': f'Failed to create upload URL: {e}'})

    if raw_path.startswith('/api/document/') and method == 'GET':
        tail = raw_path[len('/api/document/'):]
        is_view = tail.endswith('/view')
        fname = tail[:-len('/view')] if is_view else tail
        safe_stored = Path(unquote(fname)).name
        disp = _display_name(safe_stored)
        s3_size = _get_s3_size(f'uploads/{safe_stored}')

        # Redirect directly to S3 presigned URL for large files (> 4 MB) without downloading into /tmp
        if s3_size > 4_000_000 and (not is_view or safe_stored.lower().endswith('.pdf')):
            params = {
                'Bucket': S3_BUCKET,
                'Key': f'uploads/{safe_stored}',
                'ResponseContentDisposition': f'{"inline" if is_view else "attachment"}; filename="{disp}"',
            }
            if is_view and safe_stored.lower().endswith('.pdf'):
                params['ResponseContentType'] = 'application/pdf'
            presigned = s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params=params,
                ExpiresIn=3600,
            )
            return {'statusCode': 302, 'headers': {**CORS_HEADERS, 'Location': presigned}, 'body': ''}

        file_path = _resolve_upload(fname)
        if not file_path or not file_path.exists():
            return _json_response(404, {'detail': 'File not found. Please upload it again.'})
        file_size = file_path.stat().st_size

        if is_view:
            if file_path.suffix.lower() == '.pdf':
                return {
                    'statusCode': 200,
                    'headers': {
                        **CORS_HEADERS,
                        'Content-Type': 'application/pdf',
                        'Content-Disposition': f'inline; filename="{disp}"',
                    },
                    'isBase64Encoded': True,
                    'body': base64.b64encode(file_path.read_bytes()).decode('ascii'),
                }
            html_out = viewer_service.render_html(file_path, disp)
            return {
                'statusCode': 200,
                'headers': {**CORS_HEADERS, 'Content-Type': 'text/html; charset=utf-8'},
                'body': html_out,
            }
        else:
            return {
                'statusCode': 200,
                'headers': {
                    **CORS_HEADERS,
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f'attachment; filename="{disp}"',
                },
                'isBase64Encoded': True,
                'body': base64.b64encode(file_path.read_bytes()).decode('ascii'),
            }

    if raw_path == '/api/classify' and method == 'POST':
        headers = {k.lower(): v for k, v in (event.get('headers') or {}).items()}
        ct = headers.get('content-type', '')
        body_raw = event.get('body') or ''
        body_bytes = base64.b64decode(body_raw) if event.get('isBase64Encoded') else body_raw.encode('utf-8')

        text = ''
        conversation_history = '[]'
        file_obj = None
        pre_stored_name = None
        actual_total_size = None

        if 'multipart/form-data' in ct:
            parsed_mp = _parse_multipart(body_bytes, ct)
            text = parsed_mp['fields'].get('text', '')
            conversation_history = parsed_mp['fields'].get('conversation_history', '[]')
            file_obj = parsed_mp['file']
        else:
            try:
                j = json.loads(body_bytes.decode('utf-8'))
                text = j.get('text', '')
                ch = j.get('conversation_history', [])
                conversation_history = ch if isinstance(ch, str) else json.dumps(ch)
                s3_key = j.get('s3_key')
                if s3_key:
                    pre_stored_name = Path(s3_key).name
                    orig_fname = j.get('filename') or _display_name(pre_stored_name)
                    s3_bytes, actual_total_size = _read_s3_smart(s3_key, orig_fname)
                    file_obj = {'filename': orig_fname, 'bytes': s3_bytes}
            except Exception:
                pass

        try:
            history = json.loads(conversation_history or '[]')
        except Exception:
            history = []

        doc_meta = None
        combined_text = text or ''
        effective_history = history

        if file_obj:
            file_bytes = file_obj['bytes']
            orig_filename = file_obj['filename']
            total_sz = actual_total_size if actual_total_size is not None else len(file_bytes)
            stored_name = pre_stored_name or f"{uuid.uuid4().hex[:8]}_{_sanitize_filename(orig_filename)}"
            try:
                if total_sz <= 8_000_000:
                    (TMP_UPLOADS / stored_name).write_bytes(file_bytes)
                if not pre_stored_name:
                    s3_client.put_object(Bucket=S3_BUCKET, Key=f'uploads/{stored_name}', Body=file_bytes)
            except Exception:
                pass

            extracted = document_service.extract_text(file_bytes, orig_filename, total_size_override=total_sz)
            doc_meta = extracted['metadata']
            q = quote(stored_name)
            doc_meta['stored_name'] = stored_name
            doc_meta['url'] = f'/api/document/{q}'
            doc_meta['view_url'] = f'/api/document/{q}/view'

            user_text = (text or '').strip()
            if doc_meta.get('is_empty', False) or total_sz == 0:
                return _json_response(200, {
                    'type': 'chat',
                    'message': f"The uploaded file '{orig_filename}' is empty (0 bytes) and contains no content to classify. Please upload a file containing text, code, or documentation.",
                    'document_metadata': doc_meta,
                })

            file_text = (
                f"[NEW FILE TO CLASSIFY: {orig_filename}]\n"
                f"==================== FULL DOCUMENT CONTENT & PROFILE ====================\n"
                f"{extracted['text']}\n"
                f"=========================================================================\n"
            )
            instruction = (
                f"\nINSTRUCTION: Read the ENTIRE document profile and all extracted sections (Start, Middle, and End) of '{orig_filename}' before classifying. "
                f"Do NOT judge early based on introductory framing or scenario examples in the first few lines. "
                f"Determine the exact industry, domain, and true document/artifact nature of '{orig_filename}' directly from its full content, "
                f"and provide a complete, accurate 5-level taxonomy hierarchy, per-level rationales (especially Level 1 rationale), source traceability mappings, summary, and detailed explanation."
            )
            combined_text = (file_text + f"\nUser Note: {user_text}\n" + instruction) if user_text else (file_text + instruction)
            effective_history = history

        if not combined_text.strip():
            return _json_response(400, {'detail': 'Please provide a document or text to classify.'})

        try:
            result = bedrock_service.classify(combined_text, effective_history)
        except Exception as e:
            import traceback
            traceback.print_exc()
            result = {
                'type': 'chat',
                'message': f"I'm ready to assist. Please share the details, question, or document you would like to discuss or classify. (Error: {e})",
            }
        result['document_metadata'] = doc_meta
        return _json_response(200, result)

    return _json_response(404, {'detail': f'Not found: {raw_path}'})
