import os
import re
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

EXTRACTED_DIR = "data/extracted"


def load_text_file(path: str):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def save_draft_as_pdf(draft_text: str):
    try:
        if not draft_text or not draft_text.strip():
            print("No draft text found.")
            return None

        os.makedirs(EXTRACTED_DIR, exist_ok=True)
        out_path = os.path.join(EXTRACTED_DIR, "test_final_review_draft.pdf")

        doc = SimpleDocTemplate(
            out_path,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "MyTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=16,
            leading=20,
            spaceAfter=14
        )

        heading_style = ParagraphStyle(
            "MyHeading",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=10,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            "MyBody",
            parent=styles["BodyText"],
            alignment=TA_JUSTIFY,
            fontSize=10.5,
            leading=14,
            spaceAfter=8,
            splitLongWords=True,
        )

        story = []
        story.append(Paragraph("Final Literature Review Draft", title_style))
        story.append(Spacer(1, 8))

        text = draft_text.replace("**", "")
        text = text.replace("\t", " ")
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        blocks = [b.strip() for b in text.split("\n\n") if b.strip()]

        for block in blocks:
            block = escape(block)

            if block.startswith("## "):
                heading = block[3:].strip()
                story.append(Paragraph(heading, heading_style))
                continue

            if block.isupper() and len(block) < 120:
                story.append(Paragraph(block.title(), heading_style))
                continue

            block = block.replace("\n", "<br/>")
            story.append(Paragraph(block, body_style))
            story.append(Spacer(1, 4))

        doc.build(story)
        return out_path

    except Exception as e:
        print("PDF generation failed:", e)
        return None


if __name__ == "__main__":
    txt_path = os.path.join(EXTRACTED_DIR, "final_review_draft.txt")

    draft_text = load_text_file(txt_path)
    print("Draft loaded:", bool(draft_text))
    print("Draft length:", len(draft_text))

    pdf_path = save_draft_as_pdf(draft_text)

    if pdf_path:
        print("PDF created successfully:", pdf_path)
    else:
        print("PDF creation failed.")