import os
import re
from pdf2docx import Converter
from docx import Document

EMOJI_PATTERN = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF]",
    flags=re.UNICODE
)

PERSONAL_KEYWORDS = [
    "email", "@", "phone", "mobile", "contact",
    "date of birth", "dob",
    "nationality", "birth", "address",
    "linkedin", "github", "leetcode", "hackerrank"
]

def pdf_to_docx(pdf_path, docx_path):
    cv = Converter(pdf_path)
    cv.convert(docx_path)
    cv.close()

def anonymize_docx(docx_path):
    doc = Document(docx_path)

    for para in doc.paragraphs:
        text = para.text.lower()

        # Remove emojis/icons
        para.text = EMOJI_PATTERN.sub("", para.text)

        # Remove personal info lines
        if any(k in text for k in PERSONAL_KEYWORDS):
            para.text = ""

    doc.save(docx_path)

def full_pdf_anonymization(input_pdf, output_docx):
    os.makedirs(os.path.dirname(output_docx), exist_ok=True)

    temp_docx = output_docx
    pdf_to_docx(input_pdf, temp_docx)
    anonymize_docx(temp_docx)
