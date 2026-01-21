import requests
import re
import os

def extract_drive_file_id(url: str) -> str:
    patterns = [
        r"/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)"
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    raise ValueError("Invalid Google Drive link")


def download_drive_file(drive_url: str, download_dir: str) -> str:
    os.makedirs(download_dir, exist_ok=True)
    file_id = extract_drive_file_id(drive_url)

    export_url = f"https://docs.google.com/document/d/{file_id}/export?format=pdf"
    export_resp = requests.get(export_url)

    if export_resp.status_code == 200 and export_resp.headers.get("Content-Type", "").startswith("application/pdf"):
        output_path = os.path.join(download_dir, "drive_resume.pdf")
        with open(output_path, "wb") as f:
            f.write(export_resp.content)
        return output_path

    session = requests.Session()
    download_url = "https://drive.google.com/uc?export=download"
    response = session.get(download_url, params={"id": file_id}, stream=True)

    for k, v in response.cookies.items():
        if k.startswith("download_warning"):
            response = session.get(
                download_url,
                params={"id": file_id, "confirm": v},
                stream=True
            )
            break

    content_type = response.headers.get("Content-Type", "").lower()

    if "pdf" in content_type:
        ext = ".pdf"
    elif "word" in content_type or "officedocument" in content_type:
        ext = ".docx"
    else:
        raise Exception(
            "This Drive file is NOT a PDF/DOCX.\n"
            "If it is a Google Doc, keep it public and retry.\n"
            "If it is something else, download and upload manually."
        )

    output_path = os.path.join(download_dir, f"drive_resume{ext}")
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(32768):
            if chunk:
                f.write(chunk)

    return output_path
