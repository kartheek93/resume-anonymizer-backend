import fitz
import re
import os

# 🔁 Import fallback pipeline
from utils.pdf_to_docx_pipeline import full_pdf_anonymization

EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]",
    flags=re.UNICODE
)

EMAIL_PATTERN = re.compile(r"@")
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-]{8,}\d")

DOB_PATTERN = re.compile(
    r"\b(dob|date\s+of\s+birth)\b|"
    r"\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b",
    re.I
)

IDENTITY_LABEL_PATTERN = re.compile(
    r"\b(birth\s*place|birthplace|nationality|citizenship|gender|marital\s*status)\b",
    re.I
)

ADDRESS_PATTERN = re.compile(r"\d{1,4}[-/]\d{1,4}|\b\d{6}\b", re.I)

PLATFORM_KEYWORDS = [
    "linkedin", "github", "git hub",
    "leetcode", "leet code",
    "hackerrank", "hacker rank",
    "portfolio", "profile"
]

def is_design_heavy_pdf(page):
    """
    Heuristic:
    - Very low readable text
    - Many scattered words
    """
    text = page.get_text("text")
    words = page.get_text("words")

    if len(text.strip()) < 80:
        return True

    if len(words) > 200 and len(text.split()) < 50:
        return True

    return False


def redact_pdf_inplace(input_pdf, output_pdf):
    try:
        doc = fitz.open(input_pdf)

        # 🔍 Detect design-heavy PDF early
        if is_design_heavy_pdf(doc[0]):
            raise Exception("Design heavy PDF detected")

        for page in doc:
            words = page.get_text("words")
            lines = {}

            for w in words:
                y = round(w[1], 1)
                lines.setdefault(y, []).append(w)

            for line_words in lines.values():
                raw = " ".join(w[4] for w in line_words)
                text = raw.lower()

                # Step 1: emoji redaction
                if EMOJI_PATTERN.search(raw):
                    for w in line_words:
                        if EMOJI_PATTERN.search(w[4]):
                            rect = fitz.Rect(w[0], w[1], w[2], w[3])
                            page.add_redact_annot(rect, fill=(1, 1, 1))

                # Step 2: full-line personal info redaction
                delete_line = (
                    EMAIL_PATTERN.search(raw)
                    or PHONE_PATTERN.search(raw)
                    or DOB_PATTERN.search(text)
                    or IDENTITY_LABEL_PATTERN.search(text)
                    or ADDRESS_PATTERN.search(text)
                    or any(p in text for p in PLATFORM_KEYWORDS)
                )

                if delete_line:
                    for w in line_words:
                        rect = fitz.Rect(w[0], w[1], w[2], w[3])
                        page.add_redact_annot(rect, fill=(1, 1, 1))

            page.apply_redactions()

        doc.save(output_pdf)
        doc.close()

    except Exception:
        # 🔁 Fallback to Option 2 pipeline
        output_docx = output_pdf.replace(".pdf", ".docx")
        full_pdf_anonymization(input_pdf, output_docx)

