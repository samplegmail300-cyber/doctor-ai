"""
file_utils.py - Turn uploaded files into something the AI can read.

Each uploaded file becomes a dict:
    {"name": str, "mime": str, "data": bytes, "text": str, "kind": "image"|"pdf"|"text"}

* images        -> sent to a vision model (Gemini / OpenAI)
* PDFs          -> text is extracted with pypdf; if the PDF is scanned
                   (no text), the PDF itself is sent to Gemini
* txt/csv/json  -> decoded as text
"""

import io
import mimetypes

IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]
DOC_TYPES = ["pdf", "txt", "csv", "md", "json"]
ALL_TYPES = IMAGE_TYPES + DOC_TYPES

MAX_FILE_MB = 15
MAX_TEXT_CHARS = 20000


def _extract_pdf_text(data):
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [(page.extract_text() or "") for page in reader.pages[:30]]
        return "\n".join(pages).strip()
    except Exception:
        return ""


def read_uploaded_file(uploaded):
    """
    Convert a Streamlit UploadedFile (or camera photo) into our dict.
    Returns None if the file is too large or unsupported.
    """
    name = getattr(uploaded, "name", None) or "camera_photo.jpg"
    data = uploaded.getvalue()
    if len(data) > MAX_FILE_MB * 1024 * 1024:
        return None

    ext = name.rsplit(".", 1)[-1].lower() if "." in name else "jpg"
    mime = getattr(uploaded, "type", None) or mimetypes.guess_type(name)[0] or ""

    if ext in IMAGE_TYPES or mime.startswith("image/"):
        if not mime.startswith("image/"):
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
        return {"name": name, "mime": mime, "data": data, "text": "", "kind": "image"}

    if ext == "pdf":
        text = _extract_pdf_text(data)
        return {
            "name": name,
            "mime": "application/pdf",
            "data": data,
            "text": text[:MAX_TEXT_CHARS],
            "kind": "pdf",
        }

    if ext in DOC_TYPES:
        text = data.decode("utf-8", errors="replace")[:MAX_TEXT_CHARS]
        return {"name": name, "mime": "text/plain", "data": b"", "text": text, "kind": "text"}

    return None


def read_many(uploaded_files):
    """Read a list of uploaded files. Returns (files, skipped_names)."""
    files, skipped = [], []
    for item in uploaded_files or []:
        parsed = read_uploaded_file(item)
        if parsed:
            files.append(parsed)
        else:
            skipped.append(getattr(item, "name", "file"))
    return files, skipped


def needs_vision(files):
    """True if any file must be looked at by a vision-capable model."""
    for f in files:
        if f["kind"] == "image":
            return True
        if f["kind"] == "pdf" and len(f["text"]) < 80:  # scanned PDF
            return True
    return False


def files_label(files):
    return ", ".join(f["name"] for f in files) if files else None


def files_text(files):
    """Readable text from all files (images contribute nothing)."""
    parts = []
    for f in files:
        if f["text"]:
            parts.append(f"--- {f['name']} ---\n{f['text']}")
    return "\n\n".join(parts)
