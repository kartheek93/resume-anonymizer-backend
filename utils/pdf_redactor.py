import fitz
import re
from utils.location_keywords import LOCATION_KEYWORDS
from utils.pdf_to_docx_pipeline import full_pdf_anonymization

# ---------------- REGEX PATTERNS ----------------

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
    r"\b(linked\s*in|github|git\s*hub|leet\s*code|hacker\s*rank|portfolio|profile)\b",
    re.I
)

USERNAME_PATTERN = re.compile(r"\b[a-z][a-z0-9._-]{3,}\b", re.I)

SOCIAL_CONTEXT = [
    "linkedin", "github", "leetcode", "hackerrank", "portfolio", "profile"
]

# ---------------- NAME DETECTION ----------------

def is_probable_name_block(text):
    t = text.strip()

    if not t:
        return False

    # Name cannot be pure contact info
    if EMAIL_PATTERN.search(t) or PHONE_PATTERN.search(t):
        return False

    # Too many digits = not a name
    if sum(c.isdigit() for c in t) > 2:
        return False

    words = t.replace("|", " ").split()

    if 1 <= len(words) <= 10:
        capital_words = sum(1 for w in words if w[:1].isupper())
        if capital_words >= 1:
            return True

    return False

# ---------------- HELPERS ----------------

def remove_all_links(page):
    for link in page.get_links():
        page.delete_link(link)

def remove_small_icon_images(page, max_size=70):
    for img in page.get_images(full=True):
        for rect in page.get_image_rects(img[0]):
            if rect.width <= max_size and rect.height <= max_size:
                page.add_redact_annot(rect, fill=(1, 1, 1))

def mask_vector_icons_micro(page, max_size=85):
    page_height = page.rect.height
    for d in page.get_drawings():
        rect = d.get("rect")
        if rect and rect.width <= max_size and rect.height <= max_size:
            if rect.y1 <= page_height * 0.18:
                page.add_redact_annot(rect, fill=(1, 1, 1))

# ---------------- BLOCK-LEVEL AUTO WHITEOUT ----------------

def auto_whiteout_contact_blocks(page):
    redacted = False
    blocks = page.get_text("blocks")

    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        t = text.lower()

        if is_probable_name_block(text):
            continue

        signals = 0
        if PHONE_PATTERN.search(text): signals += 1
        if EMAIL_PATTERN.search(text): signals += 1
        if any(k in t for k in SOCIAL_CONTEXT): signals += 1
        if any(loc in t for loc in LOCATION_KEYWORDS): signals += 1
        if "|" in text or "#" in text or "*" in text: signals += 1
        if IDENTITY_LABEL_PATTERN.search(t): signals += 1
        if ADDRESS_PATTERN.search(t): signals += 1
        if EMOJI_PATTERN.search(text): signals += 1

        if signals >= 2:
            page.add_redact_annot(fitz.Rect(x0, y0, x1, y1), fill=(1, 1, 1))
            redacted = True

    return redacted

# ---------------- FINAL HEADER WHITEOUT (LAST RESORT) ----------------

def final_header_whiteout_fallback(page):
    blocks = page.get_text("blocks")

    for b in blocks:
        x0, y0, x1, y1, text, *_ = b

        if is_probable_name_block(text):
            continue

        if y1 <= page.rect.height * 0.12:
            page.add_redact_annot(
                fitz.Rect(x0, y0, x1, y1),
                fill=(1, 1, 1)
            )

# ---------------- MAIN ----------------

def redact_pdf_inplace(input_pdf, output_pdf):
    try:
        doc = fitz.open(input_pdf)

        for page in doc:
            any_redaction_done = False

            remove_all_links(page)
            remove_small_icon_images(page)

            # --- TEXT LINE LEVEL ---
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
                    or EMOJI_PATTERN.search(raw)
                )

                if delete_line:
                    for w in line_words:
                        page.add_redact_annot(
                            fitz.Rect(w[0], w[1], w[2], w[3]),
                            fill=(1, 1, 1)
                        )
                    any_redaction_done = True

            mask_vector_icons_micro(page)

            # --- BLOCK LEVEL ---
            if auto_whiteout_contact_blocks(page):
                any_redaction_done = True

            # --- FINAL FALLBACK (ONLY IF NOTHING WORKED) ---
            if not any_redaction_done:
                final_header_whiteout_fallback(page)

            page.apply_redactions()

        doc.save(output_pdf)
        doc.close()

    except Exception:
        full_pdf_anonymization(
            input_pdf,
            output_pdf.replace(".pdf", ".docx")
        )
