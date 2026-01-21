import fitz
from docx import Document
import re

NAME_CLEANER = re.compile(r"[^A-Za-z\s]")

def normalize_name(name):
    if not name:
        return None
    name = NAME_CLEANER.sub("", name).strip()
    if not name or len(name.split()) > 6:
        return None
    return name.replace(" ", "_")

# ---------------- PDF NAME EXTRACTION ----------------

def extract_name_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]

        page_height = page.rect.height
        header_limit = page_height * 0.20

        blocks = page.get_text("dict")["blocks"]
        candidates = []

        for block in blocks:
            if block["type"] != 0:
                continue

            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    size = span["size"]
                    y = span["bbox"][1]

                    if not text:
                        continue
                    if y > header_limit:
                        continue
                    if any(ch.isdigit() for ch in text):
                        continue
                    if "@" in text or "+" in text or "http" in text:
                        continue

                    words = text.split()
                    if 1 <= len(words) <= 6:
                        candidates.append((size, y, text))

        if not candidates:
            return None

        candidates.sort(key=lambda x: (-x[0], x[1]))
        return candidates[0][2]

    except Exception:
        return None

# ---------------- DOCX NAME EXTRACTION ----------------

def extract_name_from_docx(docx_path):
    try:
        doc = Document(docx_path)

        candidates = []

        for para in doc.paragraphs[:6]:
            text = para.text.strip()
            if not text:
                continue
            if any(ch.isdigit() for ch in text):
                continue
            if "@" in text or "+" in text:
                continue
            words = text.split()
            if 1 <= len(words) <= 6:
                candidates.append(text)

        if not candidates:
            return None

        return candidates[0]

    except Exception:
        return None
