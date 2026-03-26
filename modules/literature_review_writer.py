import os
from dotenv import load_dotenv
from google import genai
from modules.writer_input import build_writer_context

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.5-flash"


def generate_literature_review(findings_path, comparison_path):
    context = build_writer_context(findings_path, comparison_path)

    prompt = f"""
You are writing a short literature review section.

Use ONLY the structured findings and comparison provided below.
Do not invent new papers, claims, datasets, or metrics.

Write 2 concise academic paragraphs that:
- synthesize the selected papers
- compare their focus areas and findings
- present a coherent literature review narrative

Return only the review text.

INPUT:
{context}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text.strip()