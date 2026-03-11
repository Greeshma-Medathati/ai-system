from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_key_findings(sections: dict):
    important_text = "\n\n".join([
        f"{name.upper()}:\n{content}"
        for name, content in sections.items()
        if name in ["abstract", "results", "discussion", "conclusion"] and content
    ])

    if not important_text.strip():
        return []

    prompt = f"""
You are analyzing a research paper.

From the following paper sections, extract 5 concise key findings.
Return them as bullet points.

Paper content:
{important_text}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        text = response.choices[0].message.content.strip()
        findings = [line.strip("-• ").strip() for line in text.splitlines() if line.strip()]
        return findings

    except Exception as e:
        print(f"❌ Error extracting key findings: {e}")
        return []