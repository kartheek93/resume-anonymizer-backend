import re
from docx import Document
from docx.oxml.ns import qn
from utils.location_keywords import LOCATION_KEYWORDS

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
    r"\b(linked\s*in|github|git\s*hub|leet\s*code|hacker\s*rank|portfolio|profile)\b\s*[:\-|/]?\s*\S+",
    re.I
)

USERNAME_PATTERN = re.compile(r"\b[a-z][a-z0-9._-]{3,}\b", re.I)

SOCIAL_CONTEXT = [
    "linkedin", "github", "leetcode", "hackerrank", "portfolio", "profile"
]

# ---------------- HELPERS ----------------

def remove_hyperlinks(paragraph):
    """
    Removes hyperlink nodes completely (LinkedIn, GitHub, mailto, tel)
    """
    p = paragraph._p
    for link in p.findall(".//w:hyperlink", namespaces=p.nsmap):
        p.remove(link)

def remove_inline_images(paragraph):
    """
    Removes inline images/icons inside a paragraph (LinkedIn icons, etc.)
    """
    for run in paragraph.runs:
        # graphicData indicates an embedded image
        if "graphicData" in run._element.xml:
            run.clear()

# ---------------- MAIN FUNCTION ----------------

def redact_docx_inplace(input_path, output_path):
    doc = Document(input_path)

    for para in doc.paragraphs:
        raw = para.text
        text = raw.lower()

        # 🔹 Step 1: remove emojis
        para.text = EMOJI_PATTERN.sub("", para.text)

        # 🔹 Step 2: remove hyperlinks & icon images
        remove_hyperlinks(para)
        remove_inline_images(para)

        # 🔹 Step 3: decide whether to delete paragraph
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
            para.text = ""

    doc.save(output_path)
