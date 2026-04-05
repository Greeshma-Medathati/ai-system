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
from modules.evaluate_rouge import safe_evaluate_and_display


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
        title = title_map.get(paper_id)
        if not title:
            for pid, t in title_map.items():
                if pid in paper_id or paper_id in pid:
                    title = t
                    break
        if not title:
            title = paper_id.replace("_", " ").replace("-", " ").strip() or paper
        content = "\n".join(f"• {f.replace('**', '').strip()}" for f in findings) if findings else "• No findings extracted"
        sections.append((title, content))
    return sections


def build_findings_html(sections):
    if not sections:
        return "<p style='color:#a08dff;padding:10px;opacity:0.6'>No findings available.</p>"
    parts = ["""
    <style>
    .findings-wrap { font-family: inherit; margin-top: 4px; }
    details.finding-item {
        border: 1px solid rgba(124,99,255,0.25);
        border-radius: 10px; margin-bottom: 10px; overflow: hidden;
    }
    details.finding-item summary {
        padding: 10px 14px; cursor: pointer; font-weight: 600;
        font-size: 0.95rem;
        background: rgba(124,99,255,0.08);
        color: #a08dff;
        list-style: none; display: flex; align-items: center; gap: 8px;
    }
    details.finding-item summary::-webkit-details-marker { display: none; }
    details.finding-item summary::before {
        content: "▶"; font-size: 0.65rem; transition: transform 0.2s; flex-shrink: 0;
        color: #7c63ff;
    }
    details.finding-item[open] summary::before { transform: rotate(90deg); }
    .finding-body {
        padding: 10px 16px 14px 16px; font-size: 0.9rem; line-height: 1.7;
        white-space: pre-wrap; border-top: 1px solid rgba(124,99,255,0.2);
        color: rgba(255,255,255,0.75);
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
# ROUGE table formatter
# -----------------------------
def format_rouge_as_html(rouge_text: str) -> str:
    """
    Parse the rouge result string and render a styled HTML table.
    Falls back to showing raw text if parsing fails.
    """
    import re

    lines = [l.strip() for l in rouge_text.strip().splitlines() if l.strip()]
    if not lines:
        return "<p style='color:rgba(160,141,255,0.6);padding:12px'>No ROUGE results yet. Run evaluation first.</p>"

    # Try to extract metric rows like:  ROUGE-1  P: 0.xx  R: 0.xx  F: 0.xx
    pattern = re.compile(
        r'(ROUGE[-\s]?\w+)\s*[:\-]?\s*'
        r'(?:P(?:recision)?[:\s]+)?([\d.]+)\s*'
        r'(?:R(?:ecall)?[:\s]+)?([\d.]+)\s*'
        r'(?:F(?:[1\-]?score)?[:\s]+)?([\d.]+)',
        re.IGNORECASE
    )

    rows = []
    for line in lines:
        m = pattern.search(line)
        if m:
            rows.append((m.group(1).upper(), m.group(2), m.group(3), m.group(4)))

    def bar(val):
        try:
            pct = float(val) * 100
        except Exception:
            pct = 0
        color = "#7c63ff" if pct >= 50 else "#a08dff" if pct >= 30 else "rgba(124,99,255,0.4)"
        return (
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<div style="flex:1;background:rgba(124,99,255,0.15);border-radius:4px;height:8px;">'
            f'<div style="width:{min(pct,100):.1f}%;background:{color};height:8px;border-radius:4px;"></div>'
            f'</div>'
            f'<span style="font-size:0.8rem;color:#c4b8ff;min-width:36px;">{float(val):.4f}</span>'
            f'</div>'
        )

    if rows:
        header = """
        <style>
        .rouge-table { width:100%; border-collapse:collapse; font-size:0.88rem; }
        .rouge-table th {
            text-align:left; padding:10px 14px;
            background:rgba(124,99,255,0.15);
            color:#a08dff; font-weight:700; letter-spacing:0.5px;
            border-bottom:1px solid rgba(124,99,255,0.25);
        }
        .rouge-table td {
            padding:10px 14px; border-bottom:1px solid rgba(124,99,255,0.1);
            vertical-align:middle;
        }
        .rouge-table tr:last-child td { border-bottom:none; }
        .rouge-table tr:hover td { background:rgba(124,99,255,0.06); }
        .metric-pill {
            display:inline-block; padding:3px 10px; border-radius:20px;
            background:rgba(124,99,255,0.18); color:#c4b8ff;
            font-weight:700; font-size:0.8rem;
        }
        </style>
        <table class="rouge-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Precision</th>
              <th>Recall</th>
              <th>F1 Score</th>
            </tr>
          </thead>
          <tbody>
        """
        body = ""
        for metric, p, r, f in rows:
            body += f"""
            <tr>
              <td><span class="metric-pill">{metric}</span></td>
              <td>{bar(p)}</td>
              <td>{bar(r)}</td>
              <td>{bar(f)}</td>
            </tr>
            """
        footer = "</tbody></table>"
        return header + body + footer

    # fallback: wrap raw text nicely
    raw = rouge_text.replace("<", "&lt;").replace(">", "&gt;")
    return f"<pre style='color:#c4b8ff;font-size:0.85rem;line-height:1.7;padding:12px;white-space:pre-wrap'>{raw}</pre>"


# -----------------------------
# Search / download
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
            return ("❌ No freely downloadable PDFs found for this topic.",
                    gr.update(choices=[], value=[]), [])
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
        status = (f"✅ Downloaded {len(selected_papers)} paper(s).\n"
                  f"📁 PDFs saved in: {PDF_DIR}\n"
                  f"📝 Metadata saved in: {meta_path}")
        preview = get_pdf_preview_markdown()
        return status, preview, gr.update(visible=bool(preview))
    except Exception as e:
        return f"❌ Download failed: {e}", "", gr.update(visible=False)


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
            metadata.append({"paperId": paper_id, "title": title, "year": "",
                              "localPdfPath": str(dest)})
            saved.append(clean_name)
        if not saved:
            return "❌ No valid PDF files were uploaded.", "", gr.update(visible=False)
        metadata_path = os.path.join(METADATA_DIR, "papers.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)
        status = (f"✅ Uploaded {len(saved)} PDF file(s).\n"
                  f"📁 PDFs saved in: {PDF_DIR}\n"
                  f"📝 Metadata saved in: {metadata_path}")
        preview = get_pdf_preview_markdown()
        return status, preview, gr.update(visible=bool(preview))
    except Exception as e:
        return f"❌ Upload failed: {e}", "", gr.update(visible=False)


# -----------------------------
# Analysis
# -----------------------------
def run_full_analysis_ui(progress=gr.Progress(track_tqdm=True)):
    ensure_dirs()
    pdfs = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
    if not pdfs:
        return ("❌ No PDFs available. Please download or upload papers first.",
                [], "<p style='color:rgba(160,141,255,0.6);padding:10px'>No findings available.</p>",
                "No final draft available.", gr.update(visible=False, value=None),
                gr.update(value="", visible=False),
                "<p style='color:rgba(160,141,255,0.6);padding:12px'>Run analysis first.</p>")
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
        return ("✅ Analysis and review generation completed successfully.",
                metadata_rows, findings_html, formatted_draft,
                gr.update(visible=pdf_path is not None, value=pdf_path),
                gr.update(value="", visible=False),
                "<p style='color:rgba(160,141,255,0.6);padding:12px'>Click \"Run ROUGE Evaluation\" to generate scores.</p>")
    except Exception as e:
        error_detail = traceback.format_exc()
        return (f"❌ Analysis failed: {e}", [],
                "<p style='color:rgba(160,141,255,0.6);padding:10px'>No findings available.</p>",
                "No final draft available.", gr.update(visible=False, value=None),
                gr.update(value=error_detail, visible=True),
                "<p style='color:rgba(160,141,255,0.6);padding:12px'>No results.</p>")


# -----------------------------
# ROUGE evaluation
# -----------------------------
def run_rouge_evaluation():
    draft_path = os.path.join(EXTRACTED_DIR, "final_review_draft.txt")
    sections_path = os.path.join(EXTRACTED_DIR, "sections.json")
    output_path = os.path.join(EXTRACTED_DIR, "rouge_scores.json")

    if not os.path.exists(draft_path):
        return format_rouge_as_html("❌ No final draft found. Run analysis first.")
    if not os.path.exists(sections_path):
        return format_rouge_as_html("❌ No sections.json found. Run analysis first.")

    result = safe_evaluate_and_display(draft_path, sections_path, output_path)
    return format_rouge_as_html(result)


# -----------------------------
# PDF export
# -----------------------------
def _save_draft_as_pdf(draft_text: str):
    try:
        import re
        from xml.sax.saxutils import escape
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

        if not draft_text or not draft_text.strip():
            return None

        out_path = os.path.join(EXTRACTED_DIR, "final_review_draft.pdf")
        doc = SimpleDocTemplate(out_path, pagesize=A4,
            leftMargin=50, rightMargin=50, topMargin=50, bottomMargin=45)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle("MyTitle", parent=styles["Title"],
            alignment=TA_CENTER, fontSize=18, leading=22, spaceAfter=16,
            textColor=colors.HexColor("#7c63ff"))
        subtitle_style = ParagraphStyle("MySubtitle", parent=styles["Normal"],
            alignment=TA_CENTER, fontSize=10, leading=12, spaceAfter=18,
            textColor=colors.HexColor("#a08dff"))
        heading_style = ParagraphStyle("MyHeading", parent=styles["Heading2"],
            alignment=TA_LEFT, fontSize=13, leading=16, spaceBefore=14,
            spaceAfter=8, textColor=colors.HexColor("#534AB7"))
        body_style = ParagraphStyle("MyBody", parent=styles["BodyText"],
            alignment=TA_JUSTIFY, fontSize=10.5, leading=16, spaceAfter=8,
            splitLongWords=True, textColor=colors.HexColor("#222222"))
        ref_style = ParagraphStyle("MyRef", parent=styles["BodyText"],
            alignment=TA_LEFT, fontSize=10, leading=15, leftIndent=14,
            firstLineIndent=-10, spaceAfter=6, splitLongWords=True,
            textColor=colors.HexColor("#222222"))

        def add_page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(colors.HexColor("#7c63ff"))
            canvas.drawRightString(A4[0] - 50, 25, f"Page {doc.page}")
            canvas.restoreState()

        story = []
        story.append(Paragraph("Final Literature Review Draft", title_style))
        story.append(Paragraph("AI Research Paper Review System", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=0.8,
                                color=colors.HexColor("#7c63ff")))
        story.append(Spacer(1, 14))

        text = draft_text.replace("**", "").replace("\t", " ")
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        section_names = ["Abstract", "Introduction", "Methods Comparison",
                         "Results Synthesis", "Conclusion", "References"]
        for sec in section_names:
            text = re.sub(rf"(?<!\n)({re.escape(sec)})\s+", rf"\n\n\1\n", text)

        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
        in_references = False

        for block in blocks:
            raw_block = block.strip()
            if raw_block.startswith("## "):
                heading = escape(raw_block[3:].strip())
                story.append(Paragraph(heading, heading_style))
                in_references = heading.lower() == "references"
                continue
            if raw_block in section_names:
                heading = escape(raw_block)
                story.append(Paragraph(heading, heading_style))
                in_references = raw_block.lower() == "references"
                continue
            safe_block = escape(raw_block)
            if in_references:
                ref_lines = [r.strip() for r in re.split(
                    r'(?=https?://)|(?<=\.)\s+(?=[A-Z][a-z]+,)', safe_block) if r.strip()]
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
    if not (edited_text or "").strip():
        return gr.update(visible=False, value=None), "❌ Draft is empty — nothing to export."
    pdf_path = _save_draft_as_pdf(edited_text)
    if pdf_path:
        return gr.update(visible=True, value=pdf_path), "✅ PDF updated from your edited draft."
    return gr.update(visible=False, value=None), "❌ PDF generation failed."


def toggle_mode(mode):
    is_auto = mode == "Automatic Search"
    return (gr.update(visible=is_auto), gr.update(visible=is_auto),
            gr.update(visible=is_auto), gr.update(visible=not is_auto),
            gr.update(visible=not is_auto))


def show_main_app():
    return gr.update(visible=False), gr.update(visible=True)


# ─────────────────────────────────────────────────────────────
# CSS  — Deep Navy + Violet palette throughout
# ─────────────────────────────────────────────────────────────
CSS = """
/* ── Global container ── */
.gradio-container { max-width: 1200px !important; margin: auto !important; }

/* ════════════════════════════════════════
   LANDING PAGE
════════════════════════════════════════ */
.landing-outer {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #0f0e1a;
    padding: 64px 24px 48px;
    border-radius: 16px;
}

.hero-block {
    text-align: center;
    width: 100%;
    max-width: 640px;
}
.hero-block h1 {
    font-size: 2.8rem;
    font-weight: 800;
    margin: 0 0 16px;
    letter-spacing: -0.5px;
    line-height: 1.15;
    color: #ffffff;
}
.hero-block h1 span { color: #7c63ff; }
.hero-block p {
    font-size: 1.05rem;
    color: rgba(255,255,255,0.52);
    max-width: 520px;
    margin: 0 auto 36px;
    line-height: 1.75;
}

/* CTA pill button */
#gs-row {
    display: flex !important;
    justify-content: center !important;
    margin-bottom: 52px;
}
#gs-row > div, #gs-row > div > div {
    flex: 0 0 auto !important;
    width: auto !important;
}
#gs-btn {
    background: #7c63ff !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 13px 52px !important;
    border-radius: 50px !important;
    border: none !important;
    width: auto !important;
    min-width: 0 !important;
    box-shadow: 0 0 32px rgba(124,99,255,0.35) !important;
    transition: background 0.18s, transform 0.14s !important;
    cursor: pointer !important;
}
#gs-btn:hover {
    background: #6450e0 !important;
    transform: translateY(-2px) !important;
}

/* Feature cards */
.feat-row {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    justify-content: center;
    width: 100%;
    max-width: 720px;
}
.feat-card {
    background: rgba(124,99,255,0.08);
    border: 1px solid rgba(124,99,255,0.22);
    border-radius: 14px;
    padding: 22px 16px;
    width: 155px;
    text-align: center;
    transition: border-color 0.2s, transform 0.2s;
}
.feat-card:hover {
    border-color: #7c63ff;
    transform: translateY(-4px);
}
.feat-icon  { font-size: 1.5rem; margin-bottom: 8px; }
.feat-title { color: #a08dff; font-weight: 700; font-size: 0.83rem; margin-bottom: 4px; }
.feat-desc  { color: rgba(255,255,255,0.38); font-size: 0.74rem; line-height: 1.5; }

/* ════════════════════════════════════════
   MAIN APP  — violet palette
════════════════════════════════════════ */

/* Dark background for the whole main app area */
#main-app-root {
    background: #0f0e1a;
    border-radius: 16px;
    padding: 20px;
    min-height: 90vh;
}

/* App header badge */
.app-header-wrap { display: flex; }
.app-header {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: 1px solid rgba(124,99,255,0.35);
    border-radius: 10px;
    padding: 7px 16px;
    margin-bottom: 16px;
    width: fit-content;
    background: rgba(124,99,255,0.10);
}
.app-header h2 {
    font-size: 0.97rem;
    font-weight: 700;
    margin: 0;
    color: #c4b8ff;
}
.app-header h2 span { color: #7c63ff; }

/* Sidebar panel */
.sidebar-panel {
    background: rgba(124,99,255,0.06);
    border: 1px solid rgba(124,99,255,0.18);
    border-radius: 12px;
    padding: 16px;
}

/* All labels in main app */
#main-app-root label,
#main-app-root .label-wrap span {
    color: #c4b8ff !important;
}

/* Textbox / inputs */
#main-app-root input[type=text],
#main-app-root textarea {
    background: rgba(124,99,255,0.08) !important;
    border: 1px solid rgba(124,99,255,0.3) !important;
    color: #e8e4ff !important;
    border-radius: 8px !important;
}
#main-app-root input[type=text]:focus,
#main-app-root textarea:focus {
    border-color: #7c63ff !important;
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(124,99,255,0.2) !important;
}

/* Primary buttons */
#main-app-root .gr-button-primary,
#main-app-root button[variant="primary"] {
    background: #7c63ff !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    box-shadow: 0 0 16px rgba(124,99,255,0.25) !important;
    transition: background 0.15s, transform 0.12s !important;
}
#main-app-root .gr-button-primary:hover,
#main-app-root button[variant="primary"]:hover {
    background: #6450e0 !important;
    transform: translateY(-1px) !important;
}

/* Secondary buttons */
#main-app-root .gr-button-secondary,
#main-app-root button[variant="secondary"] {
    background: rgba(124,99,255,0.12) !important;
    color: #a08dff !important;
    border: 1px solid rgba(124,99,255,0.3) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: background 0.15s !important;
}
#main-app-root .gr-button-secondary:hover,
#main-app-root button[variant="secondary"]:hover {
    background: rgba(124,99,255,0.22) !important;
}

/* Tab navigation */
.tab-nav button {
    color: rgba(160,141,255,0.6) !important;
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
    transition: color 0.15s !important;
}
.tab-nav button.selected {
    color: #a08dff !important;
    border-bottom: 2px solid #7c63ff !important;
    background: transparent !important;
}
.tab-nav button:hover {
    color: #c4b8ff !important;
}

/* Dataframe table */
#main-app-root .gr-dataframe table {
    background: rgba(124,99,255,0.05) !important;
}
#main-app-root .gr-dataframe th {
    background: rgba(124,99,255,0.15) !important;
    color: #a08dff !important;
    border-bottom: 1px solid rgba(124,99,255,0.25) !important;
}
#main-app-root .gr-dataframe td {
    color: #e0daff !important;
    border-bottom: 1px solid rgba(124,99,255,0.1) !important;
}

/* Slider */
#main-app-root input[type=range] {
    accent-color: #7c63ff;
}

/* Radio buttons */
#main-app-root .gr-radio input:checked + label::before,
#main-app-root input[type=radio]:checked {
    accent-color: #7c63ff;
}

/* Radio option labels — lighter tint so they stand out from Input Mode bg */
#main-app-root .gr-radio label,
#main-app-root [data-testid="radio-group"] label,
#main-app-root .gr-form .gr-radio span {
    background: rgba(124,99,255,0.14) !important;
    border: 1px solid rgba(124,99,255,0.28) !important;
    border-radius: 7px !important;
    padding: 5px 12px !important;
    color: #c4b8ff !important;
    transition: background 0.15s !important;
}
#main-app-root .gr-radio label:hover,
#main-app-root [data-testid="radio-group"] label:hover {
    background: rgba(124,99,255,0.24) !important;
}

/* Checkbox group */
#main-app-root input[type=checkbox]:checked {
    accent-color: #7c63ff;
}

/* Markdown headings inside app */
#main-app-root .gradio-markdown h1,
#main-app-root .gradio-markdown h2,
#main-app-root .gradio-markdown h3 {
    background: none !important;
    border: none !important;
    padding: 0 !important;
    font-weight: 600 !important;
    color: #c4b8ff !important;
}

/* PDF preview box */
.pdf-preview {
    background: rgba(124,99,255,0.07);
    border: 1px solid rgba(124,99,255,0.22);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.88rem;
    margin-top: 4px;
    color: #c4b8ff;
}

/* Error box */
.error-box textarea {
    font-family: monospace !important;
    font-size: 0.8rem !important;
    color: #f09595 !important;
    background: rgba(226,75,74,0.08) !important;
    border: 1px solid rgba(226,75,74,0.25) !important;
}

/* Status textbox */
#main-app-root .gr-textbox textarea {
    color: #c4b8ff !important;
}

/* Block backgrounds */
#main-app-root .gr-block, #main-app-root .gr-form {
    background: rgba(124,99,255,0.04) !important;
    border-color: rgba(124,99,255,0.18) !important;
    border-radius: 10px !important;
}
"""

# ─────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────
ensure_dirs()

with gr.Blocks(title="AI Research Paper Review System", theme=gr.themes.Soft(), css=CSS) as demo:

    # ── Landing Page ──────────────────────────────────────────
    with gr.Group(visible=True) as landing_page:
        gr.HTML("""
        <div class="landing-outer">
            <div class="hero-block">
                <h1>AI Literature <span>Review</span></h1>
                <p>Automatically search, download, and synthesize research papers
                   into a polished literature review — powered by AI.</p>
            </div>
        </div>
        """)

        with gr.Row(elem_id="gs-row"):
            gs_btn = gr.Button("Get Started →", elem_id="gs-btn")

        gr.HTML("""
        <div style="background:#0f0e1a; padding: 0 0 40px; border-radius: 0 0 16px 16px;">
        <div class="feat-row" style="margin: 0 auto; justify-content: center;">
            <div class="feat-card">
                <div class="feat-icon">🔍</div>
                <div class="feat-title">Search Papers</div>
                <div class="feat-desc">Find open-access PDFs automatically by topic</div>
            </div>
            <div class="feat-card">
                <div class="feat-icon">🧠</div>
                <div class="feat-title">AI Analysis</div>
                <div class="feat-desc">Extract key findings from each paper</div>
            </div>
            <div class="feat-card">
                <div class="feat-icon">📝</div>
                <div class="feat-title">Generate Review</div>
                <div class="feat-desc">Produce a structured literature review draft</div>
            </div>
            <div class="feat-card">
                <div class="feat-icon">📊</div>
                <div class="feat-title">ROUGE Scores</div>
                <div class="feat-desc">Evaluate quality with ROUGE-1, 2, L metrics</div>
            </div>
        </div>
        </div>
        """)

    # ── Main App ──────────────────────────────────────────────
    with gr.Group(visible=False, elem_id="main-app-root") as main_app:

        gr.HTML("""
        <div class="app-header-wrap">
            <div class="app-header">
                <span style="font-size:1.15rem">📚</span>
                <h2>AI Literature <span>Review System</span></h2>
            </div>
        </div>
        """)

        papers_state = gr.State([])

        with gr.Row():
            # ── Left sidebar ──────────────────────────────────
            with gr.Column(scale=1, elem_classes=["sidebar-panel"]):
                mode = gr.Radio(
                    choices=["Automatic Search", "Manual Upload"],
                    value="Automatic Search", label="Input Mode"
                )
                topic = gr.Textbox(
                    label="Research Topic",
                    placeholder="Enter your topic here..."
                )
                paper_count = gr.Slider(
                    minimum=1, maximum=5, value=3, step=1, label="Number of Papers"
                )
                search_btn = gr.Button("🔎 Search Downloadable Papers", variant="primary")
                search_status = gr.Textbox(label="Search Status", interactive=False)
                paper_selector = gr.CheckboxGroup(
                    label="Select Papers to Download", choices=[]
                )
                download_btn = gr.Button("⬇️ Download Selected Papers")
                download_status = gr.Textbox(
                    label="Download / Upload Status", interactive=False
                )
                pdf_preview = gr.Markdown(
                    value="", elem_classes=["pdf-preview"], visible=False
                )
                manual_upload = gr.File(
                    label="Upload PDF Files", file_count="multiple",
                    file_types=[".pdf"], visible=False
                )
                upload_btn = gr.Button("📤 Save Uploaded PDFs", visible=False)
                run_btn = gr.Button("⚙️ Run Full Analysis", variant="primary")
                overall_status = gr.Textbox(label="System Status", interactive=False)
                error_log = gr.Textbox(
                    label="⚠️ Error Details", interactive=False,
                    visible=False, lines=7, elem_classes=["error-box"]
                )

            # ── Right panel ───────────────────────────────────
            with gr.Column(scale=2):
                with gr.Tab("📄 Selected Papers"):
                    papers_table = gr.Dataframe(
                        headers=["Paper ID", "Title", "Year"],
                        datatype=["str", "str", "str"],
                        column_widths=["20%", "65%", "15%"],
                        value=[], interactive=False, wrap=True
                    )

                with gr.Tab("🔍 Findings"):
                    findings_html = gr.HTML(
                        value="<p style='color:rgba(160,141,255,0.6);padding:10px'>No findings available.</p>"
                    )

                with gr.Tab("📘 Final Draft"):
                    final_draft_box = gr.Textbox(
                        value="No final draft available.",
                        label="Review Draft  —  edit freely, then re-export as PDF",
                        lines=26, interactive=True
                    )
                    with gr.Row():
                        regenerate_btn = gr.Button(
                            "🔄 Re-export Edited Draft as PDF", variant="secondary"
                        )
                        draft_download = gr.File(
                            label="⬇️ Download Final Draft as PDF", visible=False
                        )

                with gr.Tab("📊 ROUGE Evaluation"):
                    gr.HTML("""
                    <p style="color:rgba(160,141,255,0.7);font-size:0.88rem;margin-bottom:12px;">
                    Run ROUGE evaluation after generating the final draft.
                    Scores compare the generated review against the original paper abstracts.
                    </p>
                    """)
                    rouge_btn = gr.Button("▶ Run ROUGE Evaluation", variant="primary")
                    rouge_output = gr.HTML(
                        value="<p style='color:rgba(160,141,255,0.6);padding:12px'>Click the button above to evaluate.</p>"
                    )

    # ── Event wiring ──────────────────────────────────────────
    gs_btn.click(fn=show_main_app, inputs=[], outputs=[landing_page, main_app])

    mode.change(fn=toggle_mode, inputs=mode,
        outputs=[paper_count, search_btn, paper_selector, manual_upload, upload_btn])

    search_btn.click(fn=search_downloadable, inputs=[topic, paper_count],
        outputs=[search_status, paper_selector, papers_state])

    download_btn.click(fn=download_selected_papers,
        inputs=[paper_selector, papers_state],
        outputs=[download_status, pdf_preview, pdf_preview])

    upload_btn.click(fn=upload_manual_pdfs, inputs=manual_upload,
        outputs=[download_status, pdf_preview, pdf_preview])

    run_btn.click(fn=run_full_analysis_ui, inputs=[],
        outputs=[overall_status, papers_table, findings_html,
                 final_draft_box, draft_download, error_log, rouge_output])

    regenerate_btn.click(fn=regenerate_pdf_from_edit, inputs=[final_draft_box],
        outputs=[draft_download, overall_status])

    rouge_btn.click(fn=run_rouge_evaluation, inputs=[],
        outputs=[rouge_output])

demo.launch()