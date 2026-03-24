import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.5-flash"


def generate_results_synthesis(all_sections: dict, all_findings: dict, paper_titles: dict):
    synthesis_input = ""

    for pdf_file, sections in all_sections.items():
        title = paper_titles.get(pdf_file, pdf_file).replace(".pdf", "")

        results_text = sections.get("results", "").strip()
        discussion_text = sections.get("discussion", "").strip()
        conclusion_text = sections.get("conclusion", "").strip()
        findings = all_findings.get(pdf_file, [])

        synthesis_input += f"\nPAPER TITLE: {title}\n"

        if findings:
            synthesis_input += "KEY FINDINGS:\n"
            for finding in findings:
                synthesis_input += f"- {finding}\n"

        combined = "\n".join([
            results_text[:3000],
            discussion_text[:2000],
            conclusion_text[:2000]
        ]).strip()

        if combined:
            synthesis_input += f"RESULT-RELATED TEXT:\n{combined}\n"

    if not synthesis_input.strip():
        return "No result-related content available."

    prompt = f"""
You are writing the RESULTS SYNTHESIS section of a literature review.

You are given extracted findings and result-related content from multiple papers.

Your task:
- Combine results across papers into a unified explanation
- Identify:
  1. Key outcomes from each paper
  2. Common trends across papers
  3. Major differences in results
- Show how the papers relate to each other

Rules:
- Write in 2 concise paragraphs
- Do NOT list results paper-by-paper
- Do NOT use bullet points
- Focus on synthesis, not repetition
- Maintain academic tone

INPUT:
{synthesis_input}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    return (response.text or "").strip()