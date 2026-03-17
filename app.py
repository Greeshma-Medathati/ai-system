import os
import json
import shutil
from pathlib import Path

import gradio as gr

from config import PDF_DIR, METADATA_DIR, EXTRACTED_DIR
from modules.search import search_papers
from modules.downloader import is_pdf_accessible, download_pdf
from modules.dataset import save_metadata
from milestone2 import run_milestone2


# -----------------------------
# Helpers
# -----------------------------
def ensure_dirs():
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)
    os.makedirs(EXTRACTED_DIR, exist_ok=True)


def clear_folder(folder_path: str):
    os.makedirs(folder_path, exist_ok=True)
    for name in os.listdir(folder_path):
        path = os.path.join(folder_path, name)
        if os.path.isfile(path):
            os.remove(path)


def clear_previous_run():
    clear_folder(PDF_DIR)
    clear_folder(EXTRACTED_DIR)


def load_metadata_table():
    metadata_path = os.path.join(METADATA_DIR, "papers.json")
    if not os.path.exists(metadata_path):
        return []

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            papers = json.load(f)

        rows = []
        for p in papers:
            rows.append([
                p.get("paperId", ""),
                p.get("title", ""),
                p.get("year", ""),
                p.get("localPdfPath", ""),
            ])
        return rows
    except Exception:
        return []


def load_json_file(path: str):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


def load_text_file(path: str):
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def format_search_choice(idx: int, paper: dict) -> str:
    title = paper.get("title", "Untitled")
    year = paper.get("year", "N/A")
    return f"{idx + 1}. {title} ({year})"


def format_findings_for_display(findings_data):
    if not findings_data:
        return "No findings available."

    metadata_path = os.path.join(METADATA_DIR, "papers.json")
    title_map = {}

    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                papers = json.load(f)
            for p in papers:
                pid = p.get("paperId", "")
                title = p.get("title", pid)
                title_map[pid] = title
        except Exception:
            pass

    lines = []

    for paper, findings in findings_data.items():
        paper_id = paper.replace(".pdf", "")
        title = title_map.get(paper_id, paper_id)

        lines.append(f"## 📄 {title}")
        lines.append("")

        if findings:
            for finding in findings:
                clean = finding.replace("**", "").strip()
                lines.append(f"• {clean}")
        else:
            lines.append("• No findings extracted")

        lines.append("")

    return "\n".join(lines)


def format_comparison_for_display(comparison_text):
    if not comparison_text:
        return "No comparison available."

    return comparison_text.replace("**", "")


def read_outputs():
    metadata_rows = load_metadata_table()
    findings = load_json_file(os.path.join(EXTRACTED_DIR, "findings.json"))
    comparison = load_text_file(os.path.join(EXTRACTED_DIR, "comparison.txt"))
    narrative = load_text_file(os.path.join(EXTRACTED_DIR, "literature_review.txt"))
    return metadata_rows, findings, comparison, narrative


# -----------------------------
# Automatic search flow
# -----------------------------
def search_downloadable(topic: str, count: int):
    ensure_dirs()

    topic = (topic or "").strip()
    if not topic:
        return (
            "❌ Please enter a research topic.",
            gr.update(choices=[], value=[]),
            []
        )

    try:
        papers = search_papers(topic, max(10, count * 6))
        downloadable = []

        for p in papers:
            pdf_info = p.get("openAccessPdf")
            if not pdf_info or not pdf_info.get("url"):
                continue
            if is_pdf_accessible(pdf_info["url"]):
                downloadable.append(p)
            if len(downloadable) >= count:
                break

        if not downloadable:
            return (
                "❌ No freely downloadable PDFs found for this topic.",
                gr.update(choices=[], value=[]),
                []
            )

        choices = [format_search_choice(i, p) for i, p in enumerate(downloadable)]
        msg = f"✅ Found {len(downloadable)} downloadable paper(s). Select and download them."
        return msg, gr.update(choices=choices, value=choices[:min(len(choices), count)]), downloadable

    except Exception as e:
        return (
            f"❌ Search failed: {e}",
            gr.update(choices=[], value=[]),
            []
        )


def download_selected_papers(selected_labels, papers_state):
    ensure_dirs()

    if not papers_state:
        return "❌ Search for papers first."

    if not selected_labels:
        return "❌ Please select at least one paper."

    try:
        clear_previous_run()

        selected_papers = []
        label_to_paper = {
            format_search_choice(i, p): p for i, p in enumerate(papers_state)
        }

        for label in selected_labels:
            paper = label_to_paper.get(label)
            if not paper:
                continue

            pdf_path = download_pdf(paper)
            paper_copy = dict(paper)
            paper_copy["localPdfPath"] = pdf_path
            selected_papers.append(paper_copy)

        selected_papers = [p for p in selected_papers if p.get("localPdfPath")]

        if not selected_papers:
            return "❌ Download failed for all selected papers."

        meta_path = save_metadata(selected_papers)
        return (
            f"✅ Downloaded {len(selected_papers)} paper(s).\n"
            f"📁 PDFs saved in: {PDF_DIR}\n"
            f"📝 Metadata saved in: {meta_path}"
        )

    except Exception as e:
        return f"❌ Download failed: {e}"


# -----------------------------
# Manual upload flow
# -----------------------------
def upload_manual_pdfs(uploaded_files):
    ensure_dirs()

    if not uploaded_files:
        return "❌ Please upload one or more PDF files."

    try:
        clear_previous_run()

        saved = []
        metadata = []

        for file_path in uploaded_files:
            src = Path(file_path)
            if src.suffix.lower() != ".pdf":
                continue

            clean_name = src.name
            dest = Path(PDF_DIR) / clean_name
            shutil.copy(file_path, dest)

            paper_id = dest.stem
            title = dest.stem.replace("_", " ").replace("-", " ")

            metadata.append({
                "paperId": paper_id,
                "title": title,
                "year": "",
                "localPdfPath": str(dest),
            })
            saved.append(clean_name)

        if not saved:
            return "❌ No valid PDF files were uploaded."

        os.makedirs(METADATA_DIR, exist_ok=True)
        metadata_path = os.path.join(METADATA_DIR, "papers.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)

        return (
            f"✅ Uploaded {len(saved)} PDF file(s).\n"
            f"📁 PDFs saved in: {PDF_DIR}\n"
            f"📝 Metadata saved in: {metadata_path}"
        )

    except Exception as e:
        return f"❌ Upload failed: {e}"


# -----------------------------
# Analysis flow
# -----------------------------
def run_analysis_ui():
    ensure_dirs()

    pdfs = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    if not pdfs:
        return (
            "❌ No PDFs available. Please download or upload papers first.",
            [],
            "No findings available.",
            "No comparison available.",
            ""
        )

    try:
        run_milestone2()
        metadata_rows, findings, comparison, narrative = read_outputs()

        formatted_findings = format_findings_for_display(findings)
        formatted_comparison = format_comparison_for_display(comparison)

        return (
            "✅ Analysis completed successfully.",
            metadata_rows,
            formatted_findings,
            formatted_comparison,
            narrative
        )

    except Exception as e:
        return (
            f"❌ Analysis failed: {e}",
            [],
            "No findings available.",
            "No comparison available.",
            ""
        )


# -----------------------------
# UI visibility toggle
# -----------------------------
def toggle_mode(mode):
    is_auto = mode == "Automatic Search"
    return (
        gr.update(visible=is_auto),
        gr.update(visible=is_auto),
        gr.update(visible=is_auto),
        gr.update(visible=not is_auto),
        gr.update(visible=not is_auto),
    )


# -----------------------------
# UI
# -----------------------------
ensure_dirs()

CSS = """
.gradio-container {
    max-width: 1200px !important;
    margin: auto !important;
}
.hero {
    text-align: center;
    padding: 12px 0 6px 0;
}
.hero h1 {
    font-size: 2rem;
    margin-bottom: 0.2rem;
}
.hero p {
    opacity: 0.88;
    font-size: 1rem;
}
"""

with gr.Blocks(
    title="AI Research Paper Review System",
    theme=gr.themes.Soft(),
    css=CSS
) as demo:
    gr.HTML(
        """
        <div class="hero">
            <h1>📚 AI Research Paper Review System</h1>
            <p>Search or upload papers, analyze them, and view findings, comparison, and narrative review.</p>
        </div>
        """
    )

    papers_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=1):
            mode = gr.Radio(
                choices=["Automatic Search", "Manual Upload"],
                value="Automatic Search",
                label="Choose Input Mode"
            )

            topic = gr.Textbox(
                label="Research Topic",
                placeholder="Enter your topic here..."
            )

            paper_count = gr.Slider(
                minimum=1,
                maximum=5,
                value=3,
                step=1,
                label="Number of Papers"
            )

            search_btn = gr.Button("🔎 Search Downloadable Papers", variant="primary")
            search_status = gr.Textbox(label="Search Status", interactive=False)

            paper_selector = gr.CheckboxGroup(
                label="Select Papers to Download",
                choices=[]
            )

            download_btn = gr.Button("⬇️ Download Selected Papers")
            download_status = gr.Textbox(label="Download / Upload Status", interactive=False)

            manual_upload = gr.File(
                label="Upload PDF Files",
                file_count="multiple",
                file_types=[".pdf"],
                visible=False
            )

            upload_btn = gr.Button("📤 Save Uploaded PDFs", visible=False)

            run_btn = gr.Button("⚙️ Run Analysis", variant="primary")
            overall_status = gr.Textbox(label="System Status", interactive=False)

        with gr.Column(scale=2):
            with gr.Tab("📄 Selected Papers"):
                papers_table = gr.Dataframe(
                    headers=["Paper ID", "Title", "Year", "Local PDF Path"],
                    datatype=["str", "str", "str", "str"],
                    value=[],
                    interactive=False,
                    wrap=True
                )

            with gr.Tab("🔍 Findings"):
                findings_markdown = gr.Markdown(value="No findings available.")

            with gr.Tab("📊 Comparison"):
                comparison_markdown = gr.Markdown(value="No comparison available.")

            with gr.Tab("📝 Narrative Review"):
                narrative_text = gr.Markdown(value="")

    mode.change(
        fn=toggle_mode,
        inputs=mode,
        outputs=[paper_count, search_btn, paper_selector, manual_upload, upload_btn]
    )

    search_btn.click(
        fn=search_downloadable,
        inputs=[topic, paper_count],
        outputs=[search_status, paper_selector, papers_state]
    )

    download_btn.click(
        fn=download_selected_papers,
        inputs=[paper_selector, papers_state],
        outputs=download_status
    )

    upload_btn.click(
        fn=upload_manual_pdfs,
        inputs=manual_upload,
        outputs=download_status
    )

    run_btn.click(
        fn=run_analysis_ui,
        inputs=[],
        outputs=[overall_status, papers_table, findings_markdown, comparison_markdown, narrative_text]
    )

demo.launch()