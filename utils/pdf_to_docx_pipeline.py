import os
import re
from pdf2docx import Converter
from docx import Document
from utils.location_keywords import LOCATION_KEYWORDS

EMOJI_PATTERN = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF]", re.UNICODE)

SOCIAL_CONTEXT = [
    "linkedin", "github", "leetcode", "hackerrank", "portfolio", "profile"
]


def pdf_to_docx(pdf_path, docx_path):
    cv = Converter(pdf_path)
    cv.convert(docx_path)
    cv.close()


def anonymize_docx(docx_path):
    doc = Document(docx_path)

    for para in doc.paragraphs:
        text = para.text.lower()
        para.text = EMOJI_PATTERN.sub("", para.text)

        if any(k in text for k in SOCIAL_CONTEXT) or any(loc in text for loc in LOCATION_KEYWORDS):
            para.text = ""

    doc.save(docx_path)


def full_pdf_anonymization(input_pdf, output_docx):
    os.makedirs(os.path.dirname(output_docx), exist_ok=True)
    pdf_to_docx(input_pdf, output_docx)
    anonymize_docx(output_docx)
