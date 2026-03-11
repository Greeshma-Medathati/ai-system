from modules.search import search_papers
from modules.downloader import is_pdf_accessible, download_pdf
from modules.dataset import save_metadata
from config import (
    DEFAULT_LIMIT,
    SAFE_MAX_LIMIT,
    HARD_CAP_LIMIT,
    PDF_DIR,
    POOL_MULTIPLIER,
    POOL_MIN,
    POOL_MAX,
)
import os


def get_n_downloadable_papers(topic: str, n: int):
    pool_size = max(POOL_MIN, n * POOL_MULTIPLIER)
    pool_size = min(pool_size, POOL_MAX)

    papers = search_papers(topic, pool_size)
    downloadable = []

    print("\nChecking for freely downloadable PDFs...")

    for p in papers:
        pdf_info = p.get("openAccessPdf")

        if not pdf_info or not pdf_info.get("url"):
            continue

        if is_pdf_accessible(pdf_info["url"]):
            downloadable.append(p)

        if len(downloadable) == n:
            break

    return downloadable

def clear_previous_pdfs():
    os.makedirs(PDF_DIR, exist_ok=True)

    for file_name in os.listdir(PDF_DIR):
        file_path = os.path.join(PDF_DIR, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)


def main():
    topic = input("Enter research topic: ").strip()

    if not topic:
        print("❌ Topic cannot be empty.")
        return

    raw_limit = input(
        f"How many downloadable papers do you want? "
        f"(default {DEFAULT_LIMIT}, safe max {SAFE_MAX_LIMIT}, hard cap {HARD_CAP_LIMIT}): "
    ).strip()

    if raw_limit == "":
        limit = DEFAULT_LIMIT
    else:
        limit = int(raw_limit)

        if limit > HARD_CAP_LIMIT:
            print(f"Limit too high. Using hard cap: {HARD_CAP_LIMIT}")
            limit = HARD_CAP_LIMIT

        elif limit > SAFE_MAX_LIMIT:
            print("⚠ Warning: Large number of papers may slow later steps.")

    papers = get_n_downloadable_papers(topic, limit)

    if not papers:
        print("\n❌ No freely downloadable PDFs found for this topic. Try another topic.")
        return

    if len(papers) < limit:
        print(f"\n⚠️ Only found {len(papers)} freely downloadable PDFs (requested {limit}).")
        print("Continuing with available papers...\n")

    print("\nDownloadable papers:")
    for i, p in enumerate(papers, start=1):
        print(f"{i}. {p['title']} ({p.get('year', 'N/A')})")

    choice = input("\nSelect paper numbers (comma-separated, e.g. 1,2): ").strip()

    indices = [int(x.strip()) - 1 for x in choice.split(",") if x.strip().isdigit()]
    indices = [i for i in indices if 0 <= i < len(papers)]

    if not indices:
        print("❌ No valid selections.")
        return

    selected = []

    # Clear previous run PDFs before downloading current topic PDFs
    clear_previous_pdfs()

    print("\nDownloading selected PDFs...\n")

    for idx in indices:
        p = papers[idx]
        pdf_path = download_pdf(p)

        p["localPdfPath"] = pdf_path
        selected.append(p)

        if pdf_path:
            print(f"✅ Downloaded: {p['title']}")
        else:
            print(f"⚠️ Could not download (blocked or removed): {p['title']}")

    meta_path = save_metadata(selected)

    print("📄 PDFs folder: data/raw_pdfs/")
    print(f"🧾 Metadata file: {meta_path}")


if __name__ == "__main__":
    main()