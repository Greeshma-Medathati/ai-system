import os
from dotenv import load_dotenv
from google import genai
from modules.chunker import chunk_text

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-3-flash-preview"

def extract_key_findings(sections: dict):
    important_text = "\n\n".join([
        f"{name.upper()}:\n{content}"
        for name, content in sections.items()
        if name in ["abstract", "results", "discussion", "conclusion"] and content
    ])

    if not important_text.strip():
        return []

    chunks = chunk_text(important_text, model="gpt-4.1-mini")  # fine to reuse your existing token chunking
    all_findings = []

    for chunk in chunks:
        prompt = f"""
Extract the key findings from the following research paper content.

Return 3 to 5 concise bullet points.

Content:
{chunk}
"""

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            text = (response.text or "").strip()

            findings = [
                line.strip("-• ").strip()
                for line in text.splitlines()
                if line.strip()
            ]

            all_findings.extend(findings)

        except Exception as e:
            print(f"❌ Error extracting findings: {e}")

    return all_findings