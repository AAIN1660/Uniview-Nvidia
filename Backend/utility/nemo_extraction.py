"""
NeMo Retriever Extraction - Cloud NIM mode.
Uses nemoretriever-parse hosted on integrate.api.nvidia.com
No local GPU needed. Works on Windows 10.
Falls back to unstructured extraction if cloud call fails.
"""
import os
import io
import json
import base64
import logging
import requests
from typing import Any
from dotenv import load_dotenv

load_dotenv("unified.env")

logger = logging.getLogger(__name__)

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BUILD_KEY = os.getenv("NVIDIA_BUILD_API_KEY", NVIDIA_API_KEY)
EXTRACT_TEXT = os.getenv("EXTRACT_TEXT", "true").lower() == "true"
EXTRACT_TABLES = os.getenv("EXTRACT_TABLES", "true").lower() == "true"
EXTRACT_CHARTS = os.getenv("EXTRACT_CHARTS", "false").lower() == "true"
EXTRACT_IMAGES = os.getenv("EXTRACT_IMAGES", "false").lower() == "true"

PARSE_ENDPOINT = os.getenv(
    "NEMORETRIEVER_PARSE_HTTP_ENDPOINT",
    "https://integrate.api.nvidia.com/v1/chat/completions"
)
PARSE_MODEL = os.getenv("NEMORETRIEVER_PARSE_MODEL", "nvidia/nemoretriever-parse")


def _pdf_to_images(pdf_bytes: bytes) -> list:
    """Convert PDF pages to base64 PNG images for nemoretriever-parse."""
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_bytes)
        images = []
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            bitmap = page.render(scale=2)
            pil_img = bitmap.to_pil()
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            images.append({"page": page_num + 1, "b64": b64})
        return images
    except Exception as e:
        logger.error("[NeMo] PDF to image failed: %s", e)
        return []


def _parse_page_via_nim(image_b64: str, page_num: int) -> str:
    """
    Send one page image to nemoretriever-parse cloud NIM.
    Image ONLY - no text input supported by this model.
    Uses tools parameter with markdown_bbox mode.
    Returns clean extracted text from the page.
    """
    payload = {
        "model": PARSE_MODEL,
        "tools": [
            {
                "type": "function",
                "function": {"name": "markdown_bbox"}
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64," + image_b64
                        }
                    }
                ]
            }
        ],
        "max_tokens": 3500,
    }

    response = requests.post(
        PARSE_ENDPOINT,
        headers={
            "Authorization": "Bearer " + NVIDIA_API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()

    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        return ""

    message = choices[0].get("message", {})

    tool_calls = message.get("tool_calls", [])
    if tool_calls:
        try:
            raw = tool_calls[0]["function"]["arguments"]
            args = json.loads(raw)
            all_texts = []
            if isinstance(args, list):
                for item in args:
                    if isinstance(item, list):
                        for subitem in item:
                            if isinstance(subitem, dict):
                                t = subitem.get("text", "").strip()
                                if t:
                                    all_texts.append(t)
                    elif isinstance(item, dict):
                        t = item.get("text", "").strip()
                        if t:
                            all_texts.append(t)
            return "\n".join(all_texts)
        except Exception as ex:
            logger.warning("[NeMo] Failed to parse tool_calls: %s", ex)
            return ""

    content = message.get("content", "") or ""
    return content.strip()


def _chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> list:
    """Split extracted text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start += chunk_size - overlap
    return chunks


def extract_with_nemo(
    pdf_bytes: bytes,
    source_name: str = "document.pdf",
) -> list:
    """
    Main extraction function.
    Converts PDF pages to images, sends to nemoretriever-parse Cloud NIM.
    Falls back to unstructured then PyMuPDF on failure.
    """
    try:
        logger.info("[NeMo Cloud] Starting extraction: %s", source_name)

        page_images = _pdf_to_images(pdf_bytes)
        if not page_images:
            raise ValueError("Could not convert PDF to images")

        logger.info("[NeMo Cloud] %d pages to process", len(page_images))

        all_chunks = []
        for page_info in page_images:
            page_num = page_info["page"]
            try:
                text = _parse_page_via_nim(page_info["b64"], page_num)
                if text.strip():
                    page_chunks = _chunk_text(text)
                    for chunk in page_chunks:
                        all_chunks.append({
                            "content": chunk,
                            "type": "text",
                            "source": source_name,
                            "page": page_num,
                        })
                    logger.info(
                        "[NeMo Cloud] Page %d -> %d chunks",
                        page_num, len(page_chunks)
                    )
            except Exception as e:
                logger.warning("[NeMo Cloud] Page %d failed: %s", page_num, e)
                continue

        if not all_chunks:
            raise ValueError("No content extracted from any page")

        logger.info(
            "[NeMo Cloud] %s -> %d total chunks",
            source_name, len(all_chunks)
        )
        return all_chunks

    except Exception as e:
        logger.warning(
            "[NeMo Cloud] Extraction failed (%s) -> falling back to unstructured",
            e
        )
        return _fallback_unstructured(pdf_bytes, source_name)


def _fallback_unstructured(pdf_bytes: bytes, source_name: str) -> list:
    """
    Fallback 1 - unstructured library.
    Fallback 2 - PyMuPDF as last resort.
    """
    try:
        from unstructured.partition.pdf import partition_pdf

        elements = partition_pdf(
            file=io.BytesIO(pdf_bytes),
            strategy="hi_res",
            infer_table_structure=True,
        )
        text = "\n\n".join(
            getattr(el, "text", "") for el in elements
            if getattr(el, "text", "").strip()
        )
        chunks = _chunk_text(text)
        logger.info(
            "[Fallback] unstructured -> %d chunks from %s",
            len(chunks), source_name
        )
        return [
            {"content": c, "type": "text", "source": source_name, "page": 0}
            for c in chunks
        ]
    except Exception as unstructured_err:
        logger.warning("[Fallback] unstructured failed: %s", unstructured_err)

    try:
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        all_chunks = []
        for page_idx in range(len(doc)):
            page_text = (doc[page_idx].get_text("text") or "").strip()
            if not page_text:
                continue
            for c in _chunk_text(page_text):
                all_chunks.append({
                    "content": c,
                    "type": "text",
                    "source": source_name,
                    "page": page_idx + 1,
                })
        logger.info(
            "[Fallback] PyMuPDF -> %d chunks from %s",
            len(all_chunks), source_name
        )
        return all_chunks

    except Exception as e:
        logger.error("[Fallback] PyMuPDF also failed: %s", e)
        return []
