from fastapi import FastAPI, UploadFile
from typing import List
from pydantic import BaseModel
import os, shutil

from utils.docx_redactor import redact_docx_inplace
from utils.pdf_redactor import redact_pdf_inplace
from utils.sheet_cleaner import clean_sheet
from utils.drive_downloader import download_drive_file


app = FastAPI()

UPLOADS = "uploads"
OUTPUTS = "outputs"
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(OUTPUTS, exist_ok=True)

# =========================================================
# 1️⃣ BULK FILE UPLOAD (PDF / DOCX / XLSX / CSV)
# =========================================================
@app.post("/anonymize/bulk")
async def anonymize_bulk(files: List[UploadFile]):
    results = []

    for file in files:
        input_path = os.path.join(UPLOADS, file.filename)

        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        name, ext = os.path.splitext(file.filename)
        output_path = os.path.join(OUTPUTS, f"V1_{name}{ext}")

        if ext.lower() == ".docx":
            redact_docx_inplace(input_path, output_path)

        elif ext.lower() == ".pdf":
            redact_pdf_inplace(input_path, output_path)

        elif ext.lower() in [".xlsx", ".csv"]:
            output_path = os.path.join(OUTPUTS, f"V1_{name}.xlsx")
            clean_sheet(input_path, output_path)

        else:
            continue

        results.append({
            "input": file.filename,
            "output": output_path
        })

    return {
        "status": "success",
        "processed": len(results),
        "files": results
    }


# =========================================================
# 2️⃣ GOOGLE DRIVE RESUME LINK SUPPORT
# =========================================================
class DriveRequest(BaseModel):
    drive_url: str

@app.post("/anonymize/drive")
async def anonymize_from_drive(data: DriveRequest):
    """
    Accepts a PUBLIC Google Drive resume link,
    downloads the file, anonymizes it,
    and saves output in the outputs/ folder.
    """

    # Download file from Drive
    input_path = download_drive_file(data.drive_url, UPLOADS)

    # Try to detect file type by content
    output_file = None

    if input_path.endswith(".pdf"):
        output_file = os.path.join(OUTPUTS, "V1_drive_resume.pdf")
        redact_pdf_inplace(input_path, output_file)

    elif input_path.endswith(".docx"):
        output_file = os.path.join(OUTPUTS, "V1_drive_resume.docx")
        redact_docx_inplace(input_path, output_file)

    else:
        return {
            "status": "error",
            "message": "Only PDF or DOCX resumes are supported from Drive links"
        }

    return {
        "status": "success",
        "output": output_file
    }



@app.post("/anonymize")
async def anonymize_adapter(files: List[UploadFile]):
    # If single file → use single-run logic
    if len(files) == 1:
        return await anonymize_run(files[0])

    # If multiple files → use bulk-run logic
    return await anonymize_bulk_run(files)
