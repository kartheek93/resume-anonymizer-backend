import re
from docx import Document

# Unicode emoji removal (any emoji)
EMOJI_PATTERN = re.compile(
    "[\U0001F300-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]",
    flags=re.UNICODE
)

# Strong personal info patterns
EMAIL_PATTERN = re.compile(r"@")
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-]{8,}\d")

# DOB in words or numbers
DOB_PATTERN = re.compile(
    r"\b(dob|date\s+of\s+birth)\b|"
    r"\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4}\b",
    re.I
)

# Other identity info
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

def redact_docx_inplace(input_path, output_path):
    doc = Document(input_path)

    for para in doc.paragraphs:
        raw = para.text
        text = raw.lower()

        # Step 1: remove emojis only
        if EMOJI_PATTERN.search(raw):
            for run in para.runs:
                run.text = EMOJI_PATTERN.sub("", run.text)

        # Step 2: remove entire line if personal info
        delete_line = (
            EMAIL_PATTERN.search(raw)
            or PHONE_PATTERN.search(raw)
            or DOB_PATTERN.search(text)
            or IDENTITY_LABEL_PATTERN.search(text)
            or ADDRESS_PATTERN.search(text)
            or any(p in text for p in PLATFORM_KEYWORDS)
        )

        if delete_line:
            for run in para.runs:
                run.text = ""

    doc.save(output_path)
