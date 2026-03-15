import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.5-flash"


def compare_papers(all_findings: dict):
    comparison_input = ""

    for paper_title, findings in all_findings.items():
        comparison_input += f"\nPAPER: {paper_title}\n"
        if findings:
            for finding in findings:
                comparison_input += f"- {finding}\n"
        else:
            comparison_input += "- No findings extracted\n"

    prompt = f"""
You are comparing multiple research papers.

Using only the findings below, identify:
1. Common themes
2. Major differences
3. Overlapping conclusions

Return the answer in clear bullet points under these exact headings:
Common Themes:
Major Differences:
Overlapping Conclusions:

Do not ask for more input.
Do not say that findings are missing unless every paper has no findings.

FINDINGS:
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