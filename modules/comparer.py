import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-3-flash-preview"

def compare_papers(all_findings: dict):
    comparison_input = ""

    for paper_title, findings in all_findings.items():
        comparison_input += f"\nPAPER: {paper_title}\n"
        for f in findings:
            comparison_input += f"- {f}\n"

    prompt = f"""
You are comparing multiple research papers.

Based on the findings below, identify:
1. Common themes
2. Major differences
3. Overlapping conclusions

Return the result in clear bullet points.

{comparison_input}
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )

        return (response.text or "").strip()

    except Exception as e:
        print(f"❌ Error comparing papers: {e}")
        return ""