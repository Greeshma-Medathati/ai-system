import os
from dotenv import load_dotenv
from google import genai
from modules.writer_input import build_writer_context

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.5-flash"


def generate_results_synthesis(findings_path, comparison_path):
    context = build_writer_context(findings_path, comparison_path)

    prompt = f"""
You are writing the results synthesis section of a literature review draft.

Use ONLY the structured findings and comparison provided below.
Do not invent metrics, scores, or outcomes that are not explicitly supported by the input.

Write one concise academic paragraph.
Focus on:
- the major outcomes or findings across the papers
- notable differences in effectiveness, conclusions, or observed behavior
- any high-level synthesis of the results

Return only the paragraph.

INPUT:
{context}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text.strip()