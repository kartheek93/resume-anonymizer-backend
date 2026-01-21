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
    r"\b(linked\s*in|github|git\s*hub|leet\s*code|hacker\s*rank|portfolio|profile)\b",
    re.I
)

USERNAME_PATTERN = re.compile(r"\b[a-z][a-z0-9._-]{3,}\b", re.I)

SOCIAL_CONTEXT = [
    "linkedin", "github", "leetcode", "hackerrank", "portfolio", "profile"
]

def looks_like_name(text):
    t = text.strip()
    if not t:
        return False
    if EMAIL_PATTERN.search(t) or PHONE_PATTERN.search(t):
        return False
    if sum(c.isdigit() for c in t) > 2:
        return False
    words = t.replace("|", " ").split()
    if 1 <= len(words) <= 10:
        return any(w[:1].isupper() for w in words)
    return False

def remove_all_links(page):
    for link in page.get_links():
        page.delete_link(link)

def remove_small_icon_images(page, y_limit, max_size=70):
    for img in page.get_images(full=True):
        for rect in page.get_image_rects(img[0]):
            if rect.y1 <= y_limit and rect.width <= max_size and rect.height <= max_size:
                page.add_redact_annot(rect, fill=(1, 1, 1))

def mask_vector_icons_micro(page, y_limit, max_size=85):
    for d in page.get_drawings():
        rect = d.get("rect")
        if rect and rect.y1 <= y_limit:
            if rect.width <= max_size and rect.height <= max_size:
                page.add_redact_annot(rect, fill=(1, 1, 1))

def auto_whiteout_contact_blocks(page, y_limit):
    redacted = False
    blocks = page.get_text("blocks")

    for b in blocks:
        x0, y0, x1, y1, text, *_ = b
        if y1 > y_limit:
            continue

        t = text.lower()
        signals = 0

        if PHONE_PATTERN.search(text): signals += 1
        if EMAIL_PATTERN.search(text): signals += 1
        if any(k in t for k in SOCIAL_CONTEXT): signals += 1
        if "|" in text or "#" in text or "*" in text: signals += 1
        if IDENTITY_LABEL_PATTERN.search(t): signals += 1
        if ADDRESS_PATTERN.search(t): signals += 1
        if EMOJI_PATTERN.search(text): signals += 1

        if any(loc in t for loc in LOCATION_KEYWORDS) and (
            PHONE_PATTERN.search(text)
            or EMAIL_PATTERN.search(text)
            or any(k in t for k in SOCIAL_CONTEXT)
            or ADDRESS_PATTERN.search(t)
            or EMOJI_PATTERN.search(text)
        ):
            signals += 1

        if signals >= 2:
            height = y1 - y0
            if looks_like_name(text):
                cut = y0 + height * 0.35
                page.add_redact_annot(
                    fitz.Rect(x0, cut, x1, y1),
                    fill=(1, 1, 1)
                )
            else:
                page.add_redact_annot(
                    fitz.Rect(x0, y0, x1, y1),
                    fill=(1, 1, 1)
                )
            redacted = True

    return redacted

def redact_pdf_inplace(input_pdf, output_pdf):
    try:
        doc = fitz.open(input_pdf)

        total_height = sum(page.rect.height for page in doc)
        anonymize_limit = total_height * 0.30
        cursor = 0

        for page in doc:
            if cursor >= anonymize_limit:
                break

            page_height = page.rect.height
            y_limit = min(page_height, anonymize_limit - cursor)

            remove_all_links(page)
            remove_small_icon_images(page, y_limit)

            words = page.get_text("words")
            lines = {}

            for w in words:
                y = round(w[1], 1)
                lines.setdefault(y, []).append(w)

            for line_words in lines.values():
                raw = " ".join(w[4] for w in line_words)
                text = raw.lower()

                line_bottom = max(w[3] for w in line_words)
                if line_bottom > y_limit:
                    continue

                delete_line = (
                    EMAIL_PATTERN.search(raw)
                    or PHONE_PATTERN.search(raw)
                    or DOB_PATTERN.search(text)
                    or IDENTITY_LABEL_PATTERN.search(text)
                    or ADDRESS_PATTERN.search(text)
                    or SOCIAL_LABEL_PATTERN.search(raw)
                    or (any(k in text for k in SOCIAL_CONTEXT) and USERNAME_PATTERN.search(raw))
                    or EMOJI_PATTERN.search(raw)
                )

                if any(loc in text for loc in LOCATION_KEYWORDS) and (
                    EMAIL_PATTERN.search(raw)
                    or PHONE_PATTERN.search(raw)
                    or SOCIAL_LABEL_PATTERN.search(raw)
                    or ADDRESS_PATTERN.search(text)
                    or EMOJI_PATTERN.search(raw)
                ):
                    delete_line = True

                if delete_line:
                    for w in line_words:
                        page.add_redact_annot(
                            fitz.Rect(w[0], w[1], w[2], w[3]),
                            fill=(1, 1, 1)
                        )

            mask_vector_icons_micro(page, y_limit)
            auto_whiteout_contact_blocks(page, y_limit)
            page.apply_redactions()

            cursor += page_height

        doc.save(output_pdf)
        doc.close()

    except Exception:
        full_pdf_anonymization(
            input_pdf,
            output_pdf.replace(".pdf", ".docx")
        )
