import os
import json
import shutil
import traceback
from pathlib import Path

import gradio as gr

from config import PDF_DIR, METADATA_DIR, EXTRACTED_DIR
from modules.search import search_papers
from modules.downloader import is_pdf_accessible, download_pdf
from modules.dataset import save_metadata
from milestone2 import run_milestone2
from milestone3 import run_milestone3


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
                str(p.get("year", "")) or "N/A",
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


def format_findings_as_sections(findings_data):
    """Return a list of (title, content) tuples for accordion rendering."""
    if not findings_data:
        return []

    metadata_path = os.path.join(METADATA_DIR, "papers.json")
    title_map = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                papers = json.load(f)
            for p in papers:
                pid = p.get("paperId", "")
                title_map[pid] = p.get("title", pid)
        except Exception:
            pass

    sections = []
    for paper, findings in findings_data.items():
        paper_id = paper.replace(".pdf", "")

        # Try exact match first, then partial match (handles mismatched IDs)
        title = title_map.get(paper_id)
        if not title:
            for pid, t in title_map.items():
                if pid in paper_id or paper_id in pid:
                    title = t
                    break
        if not title:
            # Last resort: humanise the filename
            title = paper_id.replace("_", " ").replace("-", " ").strip() or paper

        if findings:
            content = "\n".join(f"• {f.replace('**', '').strip()}" for f in findings)
        else:
            content = "• No findings extracted"
        sections.append((title, content))
    return sections


def build_findings_html(sections):
    """Build a clean accordion-style HTML block for findings per paper."""
    if not sections:
        return "<p style='color:gray;padding:10px'>No findings available.</p>"

    parts = ["""
    <style>
    .findings-wrap { font-family: inherit; margin-top: 4px; }
    details.finding-item {
        border: 1px solid var(--border-color-primary, #ddd);
        border-radius: 8px;
        margin-bottom: 10px;
        overflow: hidden;
    }
    details.finding-item summary {
        padding: 10px 14px;
        cursor: pointer;
        font-weight: 600;
        font-size: 0.95rem;
        background: var(--block-background-fill, #f9f9f9);
        list-style: none;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    details.finding-item summary::-webkit-details-marker { display: none; }
    details.finding-item summary::before {
        content: "▶";
        font-size: 0.65rem;
        transition: transform 0.2s;
        flex-shrink: 0;
    }
    details.finding-item[open] summary::before { transform: rotate(90deg); }
    .finding-body {
        padding: 10px 16px 14px 16px;
        font-size: 0.9rem;
        line-height: 1.7;
        white-space: pre-wrap;
        border-top: 1px solid var(--border-color-primary, #ddd);
    }
    </style>
    <div class="findings-wrap">
    """]
    for title, content in sections:
        safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
        safe_content = content.replace("<", "&lt;").replace(">", "&gt;")
        parts.append(f"""
        <details class="finding-item">
            <summary>📄 {safe_title}</summary>
            <div class="finding-body">{safe_content}</div>
        </details>
        """)
    parts.append("</div>")
    return "".join(parts)


def format_final_draft_for_display(draft_text):
    if not draft_text:
        return "No final draft available."
    import re
    text = draft_text.replace("**", "")
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and stripped.isupper() and len(stripped) > 3:
            lines.append(f"## {stripped.title()}")
        else:
            lines.append(line)
    return "\n".join(lines)


def read_outputs():
    metadata_rows = load_metadata_table()
    findings = load_json_file(os.path.join(EXTRACTED_DIR, "findings.json"))
    final_draft = load_text_file(os.path.join(EXTRACTED_DIR, "final_review_draft.txt"))
    return metadata_rows, findings, final_draft


def normalize_selected_labels(selected_labels):
    if not selected_labels:
        return []
    if isinstance(selected_labels, str):
        return [selected_labels]
    if isinstance(selected_labels, (list, tuple)):
        return list(selected_labels)
    return [str(selected_labels)]


def normalize_papers_state(papers_state):
    if not papers_state:
        return []
    if isinstance(papers_state, list):
        if all(isinstance(p, dict) for p in papers_state):
            return papers_state
        normalized = []
        for item in papers_state:
            if isinstance(item, dict):
                normalized.append(item)
            elif isinstance(item, str):
                try:
                    parsed = json.loads(item)
                    if isinstance(parsed, dict):
                        normalized.append(parsed)
                except Exception:
                    pass
        return normalized
    if isinstance(papers_state, str):
        try:
            parsed = json.loads(papers_state)
            if isinstance(parsed, list):
                return [p for p in parsed if isinstance(p, dict)]
            if isinstance(parsed, dict):
                return [parsed]
        except Exception:
            return []
    if isinstance(papers_state, dict):
        return [papers_state]
    return []


def find_paper_from_label(label, papers):
    for i, p in enumerate(papers):
        if format_search_choice(i, p) == label:
            return p
    for p in papers:
        if p.get("title") == label:
            return p
    for p in papers:
        if p.get("paperId") == label:
            return p
    return None


def get_pdf_preview_markdown():
    """Return a markdown string listing all PDFs currently in PDF_DIR."""
    if not os.path.exists(PDF_DIR):
        return ""
    pdfs = sorted(f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf"))
    if not pdfs:
        return ""
    lines = ["**📁 PDFs ready for analysis:**"]
    for name in pdfs:
        lines.append(f"• {name}")
    return "\n".join(lines)


# -----------------------------
# Automatic search flow
# -----------------------------
def search_downloadable(topic: str, count: int):
    ensure_dirs()
    topic = (topic or "").strip()
    if not topic:
        return "❌ Please enter a research topic.", gr.update(choices=[], value=[]), []
    try:
        papers = search_papers(topic, max(10, count * 6))
        downloadable = []
        for p in papers:
            if not isinstance(p, dict):
                continue
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
        return f"❌ Search failed: {e}", gr.update(choices=[], value=[]), []


def download_selected_papers(selected_labels, papers_state):
    ensure_dirs()
    selected_labels = normalize_selected_labels(selected_labels)
    papers = normalize_papers_state(papers_state)

    if not papers:
        return "❌ Search for papers first.", "", gr.update(visible=False)
    if not selected_labels:
        return "❌ Please select at least one paper.", "", gr.update(visible=False)

    try:
        clear_previous_run()
        selected_papers = []
        for label in selected_labels:
            paper = find_paper_from_label(label, papers)
            if not isinstance(paper, dict):
                continue
            pdf_path = download_pdf(paper)
            if not pdf_path:
                continue
            paper_copy = dict(paper)
            paper_copy["localPdfPath"] = pdf_path
            selected_papers.append(paper_copy)

        if not selected_papers:
            return "❌ Download failed for all selected papers.", "", gr.update(visible=False)

        meta_path = save_metadata(selected_papers)
        status = (
            f"✅ Downloaded {len(selected_papers)} paper(s).\n"
            f"📁 PDFs saved in: {PDF_DIR}\n"
            f"📝 Metadata saved in: {meta_path}"
        )
        preview = get_pdf_preview_markdown()
        return status, preview, gr.update(visible=bool(preview))

    except Exception as e:
        return f"❌ Download failed: {e}", "", gr.update(visible=False)


# -----------------------------
# Manual upload flow
# -----------------------------
def upload_manual_pdfs(uploaded_files):
    ensure_dirs()
    if not uploaded_files:
        return "❌ Please upload one or more PDF files.", "", gr.update(visible=False)

    try:
        clear_previous_run()
        saved = []
        metadata = []

        for file_item in uploaded_files:
            file_path = file_item.name if hasattr(file_item, "name") else str(file_item)
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
            return "❌ No valid PDF files were uploaded.", "", gr.update(visible=False)

        metadata_path = os.path.join(METADATA_DIR, "papers.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)

        status = (
            f"✅ Uploaded {len(saved)} PDF file(s).\n"
            f"📁 PDFs saved in: {PDF_DIR}\n"
            f"📝 Metadata saved in: {metadata_path}"
        )
        preview = get_pdf_preview_markdown()
        return status, preview, gr.update(visible=bool(preview))

    except Exception as e:
        return f"❌ Upload failed: {e}", "", gr.update(visible=False)


# -----------------------------
# Analysis flow
# -----------------------------
def run_full_analysis_ui(progress=gr.Progress(track_tqdm=True)):
    ensure_dirs()

    pdfs = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    if not pdfs:
        return (
            "❌ No PDFs available. Please download or upload papers first.",
            [],
            "<p style='color:gray;padding:10px'>No findings available.</p>",
            "No final draft available.",
            gr.update(visible=False, value=None),
            gr.update(value="", visible=False),
        )

    try:
        progress(0.1, desc="⚙️ Step 1/3 — Extracting findings from papers...")
        run_milestone2()

        progress(0.6, desc="✍️ Step 2/3 — Generating literature review draft...")
        run_milestone3()

        progress(0.9, desc="📄 Step 3/3 — Preparing outputs...")
        metadata_rows, findings, final_draft = read_outputs()

        sections = format_findings_as_sections(findings)
        findings_html = build_findings_html(sections)
        formatted_draft = format_final_draft_for_display(final_draft)

        pdf_path = _save_draft_as_pdf(final_draft) if final_draft else None

        progress(1.0, desc="✅ Done!")
        return (
            "✅ Analysis and review generation completed successfully.",
            metadata_rows,
            findings_html,
            formatted_draft,
            gr.update(visible=pdf_path is not None, value=pdf_path),
            gr.update(value="", visible=False),
        )

    except Exception as e:
        error_detail = traceback.format_exc()
        return (
            f"❌ Analysis failed: {e}",
            [],
            "<p style='color:gray;padding:10px'>No findings available.</p>",
            "No final draft available.",
            gr.update(visible=False, value=None),
            gr.update(value=error_detail, visible=True),
        )


def _save_draft_as_pdf(draft_text: str):
    try:
        import os
        import re
        from xml.sax.saxutils import escape
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            PageBreak,
            HRFlowable
        )

        if not draft_text or not draft_text.strip():
            return None

        out_path = os.path.join(EXTRACTED_DIR, "final_review_draft.pdf")

        doc = SimpleDocTemplate(
            out_path,
            pagesize=A4,
            leftMargin=50,
            rightMargin=50,
            topMargin=50,
            bottomMargin=45
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "MyTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=18,
            leading=22,
            spaceAfter=16,
            textColor=colors.HexColor("#222222")
        )

        subtitle_style = ParagraphStyle(
            "MySubtitle",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontSize=10,
            leading=12,
            spaceAfter=18,
            textColor=colors.HexColor("#666666")
        )

        heading_style = ParagraphStyle(
            "MyHeading",
            parent=styles["Heading2"],
            alignment=TA_LEFT,
            fontSize=13,
            leading=16,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#1f1f1f")
        )

        body_style = ParagraphStyle(
            "MyBody",
            parent=styles["BodyText"],
            alignment=TA_JUSTIFY,
            fontSize=10.5,
            leading=16,
            spaceAfter=8,
            splitLongWords=True,
            textColor=colors.HexColor("#222222")
        )

        ref_style = ParagraphStyle(
            "MyRef",
            parent=styles["BodyText"],
            alignment=TA_LEFT,
            fontSize=10,
            leading=15,
            leftIndent=14,
            firstLineIndent=-10,
            spaceAfter=6,
            splitLongWords=True,
            textColor=colors.HexColor("#222222")
        )

        def add_page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(colors.grey)
            canvas.drawRightString(A4[0] - 50, 25, f"Page {doc.page}")
            canvas.restoreState()

        story = []
        story.append(Paragraph("Final Literature Review Draft", title_style))
        story.append(Paragraph("AI Research Paper Review System", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#BBBBBB")))
        story.append(Spacer(1, 14))

        text = draft_text.replace("**", "")
        text = text.replace("\t", " ")
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        # known section names
        section_names = [
            "Abstract",
            "Introduction",
            "Methods Comparison",
            "Results Synthesis",
            "Conclusion",
            "References"
        ]

        # convert inline headings into proper blocks
        for sec in section_names:
            text = re.sub(rf"(?<!\n)({re.escape(sec)})\s+", rf"\n\n\1\n", text)

        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]

        in_references = False

        for block in blocks:
            raw_block = block.strip()

            # heading detection
            if raw_block.startswith("## "):
                heading = escape(raw_block[3:].strip())
                story.append(Paragraph(heading, heading_style))
                if heading.lower() == "references":
                    in_references = True
                continue

            if raw_block in section_names:
                heading = escape(raw_block)
                story.append(Paragraph(heading, heading_style))
                if raw_block.lower() == "references":
                    in_references = True
                else:
                    in_references = False
                continue

            safe_block = escape(raw_block)

            if in_references:
                # split references more neatly
                ref_lines = [r.strip() for r in re.split(r'(?=https?://)|(?<=\.)\s+(?=[A-Z][a-z]+,)', safe_block) if r.strip()]
                if len(ref_lines) == 1:
                    story.append(Paragraph(ref_lines[0].replace("\n", "<br/>"), ref_style))
                else:
                    for ref in ref_lines:
                        story.append(Paragraph(ref.replace("\n", "<br/>"), ref_style))
                story.append(Spacer(1, 4))
            else:
                story.append(Paragraph(safe_block.replace("\n", "<br/>"), body_style))
                story.append(Spacer(1, 4))

        doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
        return out_path

    except Exception as e:
        print(f"PDF generation failed: {e}")
        return None


def regenerate_pdf_from_edit(edited_text):
    """Re-generate the PDF from user-edited draft text."""
    if not (edited_text or "").strip():
        return gr.update(visible=False, value=None), "❌ Draft is empty — nothing to export."
    pdf_path = _save_draft_as_pdf(edited_text)
    if pdf_path:
        return gr.update(visible=True, value=pdf_path), "✅ PDF updated from your edited draft."
    return gr.update(visible=False, value=None), "❌ PDF generation failed — check console for details."


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
.gradio-container { max-width: 1200px !important; margin: auto !important; }
.hero { text-align: center; padding: 12px 0 6px 0; }
.hero h1 { font-size: 2rem; margin-bottom: 0.2rem; }
.hero p { opacity: 0.88; font-size: 1rem; }
.pdf-preview {
    background: var(--block-background-fill);
    border: 1px solid var(--border-color-primary);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.88rem;
    margin-top: 4px;
}
.error-box textarea {
    font-family: monospace !important;
    font-size: 0.8rem !important;
    color: #c0392b !important;
}
"""

with gr.Blocks(title="AI Research Paper Review System", theme=gr.themes.Soft(), css=CSS) as demo:
    gr.HTML("""
        <div class="hero">
            <h1>📚 AI Research Paper Review System</h1>
            <p>Search or upload papers, run analysis, and generate a literature review draft.</p>
        </div>
    """)

    papers_state = gr.State([])

    with gr.Row():
        # ── Left panel ───────────────────────────────────────────────────
        with gr.Column(scale=1):
            mode = gr.Radio(
                choices=["Automatic Search", "Manual Upload"],
                value="Automatic Search",
                label="Choose Input Mode"
            )
            topic = gr.Textbox(label="Research Topic", placeholder="Enter your topic here...")
            paper_count = gr.Slider(minimum=1, maximum=5, value=3, step=1, label="Number of Papers")
            search_btn = gr.Button("🔎 Search Downloadable Papers", variant="primary")
            search_status = gr.Textbox(label="Search Status", interactive=False)
            paper_selector = gr.CheckboxGroup(label="Select Papers to Download", choices=[])
            download_btn = gr.Button("⬇️ Download Selected Papers")
            download_status = gr.Textbox(label="Download / Upload Status", interactive=False)

            # 🆕 Paper preview list
            pdf_preview = gr.Markdown(value="", elem_classes=["pdf-preview"], visible=False)

            manual_upload = gr.File(
                label="Upload PDF Files", file_count="multiple",
                file_types=[".pdf"], visible=False
            )
            upload_btn = gr.Button("📤 Save Uploaded PDFs", visible=False)

            run_btn = gr.Button("⚙️ Run Full Analysis", variant="primary")
            overall_status = gr.Textbox(label="System Status", interactive=False)

            # 🆕 Error log (hidden unless there's a failure)
            error_log = gr.Textbox(
                label="⚠️ Error Details",
                interactive=False,
                visible=False,
                lines=7,
                elem_classes=["error-box"]
            )

        # ── Right panel ──────────────────────────────────────────────────
        with gr.Column(scale=2):
            with gr.Tab("📄 Selected Papers"):
                papers_table = gr.Dataframe(
                    headers=["Paper ID", "Title", "Year"],
                    datatype=["str", "str", "str"],
                    column_widths=["20%", "65%", "15%"],
                    value=[],
                    interactive=False,
                    wrap=True
                )

            with gr.Tab("🔍 Findings"):
                # 🆕 Accordion-per-paper via HTML
                findings_html = gr.HTML(
                    value="<p style='color:gray;padding:10px'>No findings available.</p>"
                )

            with gr.Tab("📘 Final Draft"):
                # 🆕 Editable textbox instead of read-only Markdown
                final_draft_box = gr.Textbox(
                    value="No final draft available.",
                    label="Review Draft  —  edit freely, then re-export as PDF",
                    lines=26,
                    interactive=True
                )
                with gr.Row():
                    regenerate_btn = gr.Button("🔄 Re-export Edited Draft as PDF", variant="secondary")
                    draft_download = gr.File(label="⬇️ Download Final Draft as PDF", visible=False)

    # ── Event wiring ─────────────────────────────────────────────────────

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
        outputs=[download_status, pdf_preview, pdf_preview]
    )

    upload_btn.click(
        fn=upload_manual_pdfs,
        inputs=manual_upload,
        outputs=[download_status, pdf_preview, pdf_preview]
    )

    run_btn.click(
        fn=run_full_analysis_ui,
        inputs=[],
        outputs=[overall_status, papers_table, findings_html, final_draft_box, draft_download, error_log]
    )

    regenerate_btn.click(
        fn=regenerate_pdf_from_edit,
        inputs=[final_draft_box],
        outputs=[draft_download, overall_status]
    )

demo.launch()