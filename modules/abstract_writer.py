import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.5-flash"


def generate_abstract(findings_text: str, comparison_text: str, methods_text: str, results_text: str):
    combined_input = f"""
FINDINGS SUMMARY:
{findings_text[:5000]}

COMPARISON:
{comparison_text[:3000]}

METHODS SECTION:
{methods_text[:3000]}

RESULTS SECTION:
{results_text[:3000]}
"""

    prompt = f"""
Write a concise ABSTRACT for a literature review.

The review analyzes multiple research papers.

Your task:
- Briefly introduce the topic
- Mention what was analyzed (multiple papers)
- Summarize the main themes and insights
- End with a strong concluding statement

Rules:
- 100 to 120 words ONLY
- No bullet points
- No unnecessary details
- Keep it clear, compact, and academic
- Avoid repeating technical details

INPUT:
{combined_input}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return (response.text or "").strip()