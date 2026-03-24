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
You are writing a structured literature review based on multiple research papers.

Your task:
- Write in academic paragraph form
- For each paper:
  - briefly explain its main contribution
- Then provide a final synthesis across all papers

Rules:
- Do NOT use bullet points
- Avoid repeating the same phrases
- Keep it readable and structured
- Mention paper ideas naturally (not as a list)

Structure:
1. Intro sentence (what papers are analyzed)
2. One paragraph per paper (contribution + findings)
3. Final synthesis paragraph (overall direction, insights)

INPUT:
{review_input}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return (response.text or "").strip()