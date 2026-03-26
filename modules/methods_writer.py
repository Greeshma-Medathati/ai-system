import os
from dotenv import load_dotenv
from google import genai
from modules.writer_input import build_writer_context

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.5-flash"


def generate_methods_comparison(findings_path, comparison_path):
    context = build_writer_context(findings_path, comparison_path)

    prompt = f"""
You are writing the methodology comparison section of a literature review draft.

Use ONLY the structured findings and comparison provided below.
Do not add assumptions beyond the input.

Write one concise academic paragraph.
Focus on:
- the methods, frameworks, or approaches used in the papers
- how the papers differ in technical focus
- any notable contrast in system design or problem framing

Return only the paragraph.

INPUT:
{context}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text.strip()