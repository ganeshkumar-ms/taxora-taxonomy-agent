"""Lightweight HTTP SDK client for the TAXORA Taxonomy Agent API."""

from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Optional

DEFAULT_API_URL = "https://yvw8dqk6c2.execute-api.us-east-1.amazonaws.com"
LIVE_APP_URL = "https://duwz8hk1atmbr.cloudfront.net"
_PRESIGN_THRESHOLD_BYTES = int(1.8 * 1024 * 1024)


class TaxoraError(RuntimeError):
    """Raised when the TAXORA API returns an HTTP or network error."""

    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def _encode_multipart(fields: dict[str, str], filename: str, file_bytes: bytes) -> tuple[bytes, str]:
    boundary = f"----TaxoraSDK{uuid.uuid4().hex[:12]}"
    chunks: list[bytes] = []

    for key, value in fields.items():
        chunks.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode("utf-8")
        )

    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    safe_name = Path(filename).name.replace('"', "_")
    chunks.append(
        (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"file\"; filename=\"{safe_name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode("utf-8")
    )
    chunks.append(file_bytes)
    chunks.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class TaxoraClient:
    """Client for integrating TAXORA into external Python applications and services."""

    def __init__(self, api_url: str = DEFAULT_API_URL, timeout: float = 90.0):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    def _request_json(
        self,
        method: str,
        path: str,
        data: Optional[bytes] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        url = f"{self.api_url}{path}"
        req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw_err = exc.read().decode("utf-8", errors="replace")
            try:
                err_payload = json.loads(raw_err)
                detail = err_payload.get("detail") or err_payload.get("message") or raw_err
            except Exception:
                err_payload = raw_err
                detail = raw_err
            raise TaxoraError(f"TAXORA HTTP {exc.code}: {detail}", status_code=exc.code, payload=err_payload) from exc
        except urllib.error.URLError as exc:
            raise TaxoraError(f"Network error calling TAXORA ({url}): {exc.reason}") from exc

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        return self._request_json("POST", path, data=body, headers={"Content-Type": "application/json"})

    def health(self) -> dict[str, Any]:
        """Check TAXORA service health (`GET /health`)."""
        return self._request_json("GET", "/health")

    def get_taxonomy(self) -> dict[str, Any]:
        """Fetch the taxonomy overview endpoint (`GET /api/taxonomy`)."""
        return self._request_json("GET", "/api/taxonomy")

    def classify_text(
        self,
        text: str,
        conversation_history: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Classify text or send a conversational taxonomy query (`POST /api/classify`)."""
        if not text or not text.strip():
            raise ValueError("text must be a non-empty string")
        return self._post_json(
            "/api/classify",
            {
                "text": text,
                "conversation_history": conversation_history or [],
            },
        )

    def chat(
        self,
        message: str,
        conversation_history: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Alias for conversational queries with TAXORA."""
        return self.classify_text(message, conversation_history=conversation_history)

    def classify_bytes(
        self,
        filename: str,
        file_bytes: bytes,
        prompt: str = "",
        conversation_history: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Classify in-memory file bytes, using presigned S3 upload automatically for large files or ZIPs."""
        history = conversation_history or []
        use_presign = len(file_bytes) > _PRESIGN_THRESHOLD_BYTES or filename.lower().endswith(".zip")

        if use_presign:
            try:
                ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                presign = self._post_json("/api/upload-url", {"filename": Path(filename).name, "content_type": ctype})
                put_req = urllib.request.Request(
                    presign["upload_url"],
                    data=file_bytes,
                    headers={"Content-Type": ctype},
                    method="PUT",
                )
                with urllib.request.urlopen(put_req, timeout=self.timeout):
                    pass
                return self._post_json(
                    "/api/classify",
                    {
                        "s3_key": presign["s3_key"],
                        "filename": Path(filename).name,
                        "text": prompt,
                        "conversation_history": history,
                    },
                )
            except Exception:
                # Fallback to direct multipart upload (for example against local FastAPI dev servers)
                pass

        body, content_type = _encode_multipart(
            {
                "text": prompt or "",
                "conversation_history": json.dumps(history),
            },
            filename,
            file_bytes,
        )
        return self._request_json("POST", "/api/classify", data=body, headers={"Content-Type": content_type})

    def classify_file(
        self,
        file_path: str | Path,
        prompt: str = "",
        conversation_history: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Read a local file and classify it into an enterprise taxonomy."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        return self.classify_bytes(path.name, path.read_bytes(), prompt=prompt, conversation_history=conversation_history)
