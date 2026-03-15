import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-2.5-flash"


def extract_key_findings(sections):
    combined_text = "\n\n".join(
        value.strip() for value in sections.values() if value and value.strip()
    )

    if not combined_text:
        return []

    combined_text = combined_text[:30000]

    prompt = f"""
You are reviewing a research paper.

Extract the 3 to 5 most important findings from the text below.

Rules:
- Return only bullet points
- Keep each point concise
- Do not ask for more input
- Do not add explanation before or after

TEXT:
{combined_text}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    findings = []
    for line in response.text.splitlines():
        line = line.strip()
        if not line:
            continue

        lower_line = line.lower()
        if lower_line.startswith("here are the"):
            continue

        line = line.lstrip("-•* ").strip()
        line = line.replace("**", "").strip()

        if line:
            findings.append(line)

    return findings[:5]