import os
import requests
from tqdm import tqdm
from config import PDF_DIR, PDF_CHECK_TIMEOUT

print("RUNNING DOWNLOADER FILE:", __file__)
def is_pdf_accessible(pdf_url: str) -> bool:
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.head(
            pdf_url,
            headers=headers,
            allow_redirects=True,
            timeout=PDF_CHECK_TIMEOUT
        )

        content_type = r.headers.get("Content-Type", "").lower()
        if r.status_code == 200 and "pdf" in content_type:
            return True

        r = requests.get(
            pdf_url,
            headers=headers,
            stream=True,
            allow_redirects=True,
            timeout=PDF_CHECK_TIMEOUT
        )

        content_type = r.headers.get("Content-Type", "").lower()
        return r.status_code == 200 and "pdf" in content_type

    except requests.RequestException:
        return False


def download_pdf(paper: dict):
    os.makedirs(PDF_DIR, exist_ok=True)

    pdf_info = paper.get("openAccessPdf")
    if not pdf_info or not pdf_info.get("url"):
        return None

    pdf_url = pdf_info["url"]
    paper_id = paper["paperId"]
    filepath = os.path.join(PDF_DIR, f"{paper_id}.pdf")

    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(
            pdf_url,
            stream=True,
            timeout=60,
            headers=headers,
            allow_redirects=True
        )

        if r.status_code != 200:
            return None

        content_type = r.headers.get("Content-Type", "").lower()
        if "pdf" not in content_type:
            print("⚠️ Skipping non-PDF response")
            return None

        with open(filepath, "wb") as f:
            for chunk in tqdm(r.iter_content(chunk_size=1024), desc="Downloading", leave=False):
                if chunk:
                    f.write(chunk)

        with open(filepath, "rb") as f:
            if f.read(5) != b"%PDF-":
                print("⚠️ Invalid PDF downloaded, removing file")
                os.remove(filepath)
                return None

        return filepath

    except requests.RequestException:
        return None