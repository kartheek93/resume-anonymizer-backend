from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List
from pydantic import BaseModel
import os, shutil, zipfile

from utils.docx_redactor import redact_docx_inplace
from utils.pdf_redactor import redact_pdf_inplace
from utils.sheet_cleaner import clean_sheet
from utils.drive_downloader import download_drive_file
from utils.name_extractor import (
    extract_name_from_pdf,
    extract_name_from_docx,
    normalize_name
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS = "uploads"
OUTPUTS = "outputs"
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(OUTPUTS, exist_ok=True)

# =========================================================
# 1️⃣ BULK / SINGLE FILE UPLOAD
# =========================================================
@app.post("/anonymize")
async def anonymize(files: List[UploadFile]):
    results = []

    # 🔽 NEW: clean outputs before each run
    for f in os.listdir(OUTPUTS):
        os.remove(os.path.join(OUTPUTS, f))

    for file in files:
        input_path = os.path.join(UPLOADS, file.filename)

        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        name, ext = os.path.splitext(file.filename)
        ext = ext.lower()

        if ext == ".docx":
            candidate = extract_name_from_docx(input_path)
            safe = normalize_name(candidate)
            output_path = (
                os.path.join(OUTPUTS, f"{safe}.docx")
                if safe else
                os.path.join(OUTPUTS, f"V1_{name}.docx")
            )
            redact_docx_inplace(input_path, output_path)

        elif ext == ".pdf":
            candidate = extract_name_from_pdf(input_path)
            safe = normalize_name(candidate)
            output_path = (
                os.path.join(OUTPUTS, f"{safe}.pdf")
                if safe else
                os.path.join(OUTPUTS, f"V1_{name}.pdf")
            )
            redact_pdf_inplace(input_path, output_path)

        elif ext in [".xlsx", ".csv"]:
            output_path = os.path.join(OUTPUTS, f"V1_{name}.xlsx")
            clean_sheet(input_path, output_path)

        else:
            continue

        results.append(output_path)

    if len(results) == 1:
        return FileResponse(
            path=results[0],
            filename=os.path.basename(results[0]),
            media_type="application/octet-stream"
        )

    zip_path = os.path.join(OUTPUTS, "anonymized_resumes.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in results:
            zipf.write(file_path, arcname=os.path.basename(file_path))

    return FileResponse(
        path=zip_path,
        filename="anonymized_resumes.zip",
        media_type="application/zip"
    )

# =========================================================
# 2️⃣ GOOGLE DRIVE LINK SUPPORT
# =========================================================
class DriveRequest(BaseModel):
    drive_url: str

@app.post("/anonymize/drive")
async def anonymize_from_drive(data: DriveRequest):
    input_path = download_drive_file(data.drive_url, UPLOADS)

    if input_path.endswith(".pdf"):
        candidate = extract_name_from_pdf(input_path)
        safe = normalize_name(candidate)
        output_path = (
            os.path.join(OUTPUTS, f"{safe}.pdf")
            if safe else
            os.path.join(OUTPUTS, "V1_drive_resume.pdf")
        )
        redact_pdf_inplace(input_path, output_path)

    elif input_path.endswith(".docx"):
        candidate = extract_name_from_docx(input_path)
        safe = normalize_name(candidate)
        output_path = (
            os.path.join(OUTPUTS, f"{safe}.docx")
            if safe else
            os.path.join(OUTPUTS, "V1_drive_resume.docx")
        )
        redact_docx_inplace(input_path, output_path)

    else:
        return {
            "status": "error",
            "message": "Only PDF or DOCX resumes are supported"
        }

    return FileResponse(
        path=output_path,
        filename=os.path.basename(output_path),
        media_type="application/octet-stream"
    )
