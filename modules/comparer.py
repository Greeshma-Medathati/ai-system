from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
3. Any overlapping conclusions

Return the result in clear bullet points.

{comparison_input}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ Error comparing papers: {e}")
        return ""