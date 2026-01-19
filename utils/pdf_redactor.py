import fitz
import re
from utils.location_keywords import LOCATION_KEYWORDS
from utils.pdf_to_docx_pipeline import full_pdf_anonymization

EMOJI_PATTERN = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]", re.UNICODE)
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

ADDRESS_PATTERN = re.compile(r"\d{6}|\d{1,4}[-/]\d{1,4}", re.I)

SOCIAL_LABEL_PATTERN = re.compile(
    r"\b(linked\s*in|github|git\s*hub|leet\s*code|hacker\s*rank|portfolio|profile)\b\s*[:\-|/]?\s*\S+",
    re.I
)

USERNAME_PATTERN = re.compile(r"\b[a-z][a-z0-9._-]{3,}\b", re.I)

SOCIAL_CONTEXT = [
    "linkedin", "github", "leetcode", "hackerrank", "portfolio", "profile"
]

def redact_pdf_inplace(input_pdf, output_pdf):
    try:
        doc = fitz.open(input_pdf)

        for page in doc:
            words = page.get_text("words")
            lines = {}

            for w in words:
                y = round(w[1], 1)
                lines.setdefault(y, []).append(w)

            for line_words in lines.values():
                raw = " ".join(w[4] for w in line_words)
                text = raw.lower()

                delete_line = (
                    EMAIL_PATTERN.search(raw)
                    or PHONE_PATTERN.search(raw)
                    or DOB_PATTERN.search(text)
                    or IDENTITY_LABEL_PATTERN.search(text)
                    or ADDRESS_PATTERN.search(text)
                    or SOCIAL_LABEL_PATTERN.search(raw)
                    or (any(k in text for k in SOCIAL_CONTEXT) and USERNAME_PATTERN.search(raw))
                    or any(loc in text for loc in LOCATION_KEYWORDS)
                )

                if delete_line:
                    for w in line_words:
                        rect = fitz.Rect(w[0], w[1], w[2], w[3])
                        page.add_redact_annot(rect, fill=(1, 1, 1))

            page.apply_redactions()

        doc.save(output_pdf)
        doc.close()

    except Exception:
        full_pdf_anonymization(input_pdf, output_pdf.replace(".pdf", ".docx"))
