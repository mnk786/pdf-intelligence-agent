"""
PDF Processing Module
Extracts text with page tracking so the AI can accurately cite sources.
"""

from typing import Dict, List, Any, Optional
import io
import re
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image


def extract_text_by_pages(pdf_file) -> List[Dict[str, Any]]:
    """
    Extracts text from a PDF file stream or bytes, returning a list of dicts:
    [{'page': 1, 'text': '...', 'char_count': 123}, ...]
    """
    reader = PdfReader(pdf_file)
    pages_data = []

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        text = page.extract_text() or ""
        text = text.strip()
        pages_data.append({
            "page": page_num,
            "text": text,
            "char_count": len(text)
        })

    return pages_data


def format_pages_for_context(pages_data: List[Dict[str, Any]]) -> str:
    """
    Formats extracted pages into a structured context block for the LLM.
    Includes page markers to facilitate exact page citations.
    """
    chunks = []
    for item in pages_data:
        page_num = item["page"]
        text = item["text"]
        if not text:
            text = "[No selectable text found on this page. May be an image or blank.]"
        chunks.append(f"--- [Page {page_num}] ---\n{text}\n")
    return "\n".join(chunks)


def get_pdf_metadata(pdf_file, pages_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Returns summary metadata about the processed PDF.
    """
    total_pages = len(pages_data)
    total_chars = sum(p["char_count"] for p in pages_data)
    pages_with_text = sum(1 for p in pages_data if p["char_count"] > 0)

    return {
        "total_pages": total_pages,
        "total_characters": total_chars,
        "pages_with_text": pages_with_text,
        "is_scanned_suspicion": total_pages > 0 and (pages_with_text / total_pages < 0.3)
    }


def extract_cited_pages(text: str) -> List[int]:
    """
    Finds all cited page numbers in text like '[Page 4]', 'Page 12', 'Pages 5-7', etc.
    Returns a sorted, unique list of integer page numbers.
    """
    if not text:
        return []

    found = set()
    # Pattern 1: [Page X] or [Pages X, Y] or [Pages X-Y]
    bracket_matches = re.findall(r'\[Pages?\s*([0-9,\s\-–]+)\]', text, re.IGNORECASE)
    for match in bracket_matches:
        for part in re.split(r'[,;]', match):
            part = part.strip()
            if '-' in part or '–' in part:
                range_parts = re.split(r'[\-–]', part)
                if len(range_parts) == 2 and range_parts[0].strip().isdigit() and range_parts[1].strip().isdigit():
                    start, end = int(range_parts[0].strip()), int(range_parts[1].strip())
                    for p in range(start, min(end + 1, start + 25)):
                        found.add(p)
            elif part.isdigit():
                found.add(int(part))

    # Pattern 2: standalone "Page 5" or "Page: 5"
    page_matches = re.findall(r'\bPages?\s*(\d+)\b', text, re.IGNORECASE)
    for p in page_matches:
        if p.isdigit():
            found.add(int(p))

    return sorted(list(found))


def render_pdf_page_image(pdf_bytes: bytes, page_number: int, scale: float = 2.0) -> Optional[Image.Image]:
    """
    Renders a specific 1-indexed PDF page as a PIL Image using PDFium.
    scale 2.0 gives crisp high-definition resolution.
    """
    try:
        doc = pdfium.PdfDocument(pdf_bytes)
        if 1 <= page_number <= len(doc):
            page = doc[page_number - 1]
            bitmap = page.render(scale=scale)
            return bitmap.to_pil()
    except Exception as e:
        print(f"Error rendering PDF page {page_number}: {e}")
    return None

