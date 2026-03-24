import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.5-flash"


def generate_methods_comparison(all_sections: dict, paper_titles: dict):
    methods_input = ""

    for pdf_file, sections in all_sections.items():
        title = paper_titles.get(pdf_file, pdf_file).replace(".pdf", "")
        methods_text = sections.get("methods", "")[:4000]

        if not methods_text:
            continue

        methods_input += f"\nPAPER TITLE: {title}\n"
        methods_input += f"METHODS:\n{methods_text[:6000]}\n"

    if not methods_input.strip():
        return "No methods sections available for comparison."

    prompt = f"""
You are writing the METHODS COMPARISON section of a literature review.

You are given methods from multiple research papers.

Your task:
- Compare the methods used across papers (NOT describe one paper only)
- Clearly identify:
  1. What each paper focuses on (e.g., system design vs experimental evaluation)
  2. Key methodological differences
  3. Any similarities or shared approaches
- Highlight contrasts between approaches

Rules:
- Write in 1–2 well-structured paragraphs
- Do NOT use bullet points
- Do NOT describe papers separately one by one
- Use comparative language like:
  "In contrast", "While one approach...", "Both papers..."
- Keep it concise and academic

INPUT:
{methods_input}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return (response.text or "").strip()