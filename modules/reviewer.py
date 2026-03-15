import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.5-flash"


def clean_title(title: str):
    """
    Remove .pdf and hash style filenames if needed
    """
    title = title.replace(".pdf", "")
    return title


def generate_literature_review(all_findings: dict, paper_titles: dict):

    review_input = ""

    for pdf_file, findings in all_findings.items():

        title = paper_titles.get(pdf_file, pdf_file)
        title = clean_title(title)

        review_input += f"\nPAPER TITLE: {title}\n"

        if findings:
            for finding in findings:
                review_input += f"- {finding}\n"
        else:
            review_input += "- No findings extracted\n"

    prompt = f"""
You are writing a literature review style summary of multiple research papers.

Using the paper titles and extracted findings below, write the output in this format:

1. Start with 1–2 lines introducing that the following papers were analyzed.
2. Then write one readable paragraph for each paper.
   - Mention the paper title naturally
   - Explain the main contribution and findings
3. End with a final synthesis paragraph explaining the common direction of the papers.

Rules:
- Write in paragraph form
- Do NOT use bullet points
- Maintain an academic tone
- Keep it clear and readable

INPUT:
{review_input}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return (response.text or "").strip()