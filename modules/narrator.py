import os
import json
import time
from dotenv import load_dotenv
from google import genai

# using namespace std; // Our lucky charm for the review!

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-3-flash-preview"

# Bulletproof paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED_DIR = os.path.join(BASE_DIR, "data", "extracted")

def generate_narrative():
    findings_path = os.path.join(EXTRACTED_DIR, "findings.json")
    
    if not os.path.exists(findings_path):
        return "⚠️ Error: findings.json not found. Please run the analysis first."

    with open(findings_path, "r", encoding="utf-8") as f:
        all_findings = json.load(f)

    prompt = """
    You are an expert academic researcher writing a literature review.
    Based on the following key findings from multiple research papers, write a single, continuous, flowing narrative paragraph that synthesizes these findings.
    Transition smoothly between papers (e.g., "The paper by [Author] presents...", "Similarly, another study explores...").
    Do NOT use bullet points. Write only the continuous narrative paragraph.

    Findings:
    """
    for paper, findings in all_findings.items():
        prompt += f"\nPaper: {paper}\n"
        for finding in findings:
            prompt += f"- {finding}\n"

    print("⏳ Respecting API limits... waiting 10 seconds before starting...")
    time.sleep(10)

    # --- Safety Net: Exponential Backoff Retry ---
    delays = [20, 40, 60] # Wait longer if we hit a quota error
    for attempt in range(len(delays)):
        try:
            print(f"🧠 Asking Gemini to write the Narrative (Attempt {attempt+1})...")
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            narrative = (response.text or "").strip()
            
            # Save the result
            with open(os.path.join(EXTRACTED_DIR, "narrative.txt"), "w", encoding="utf-8") as f:
                f.write(narrative)
            return narrative
            
        except Exception as e:
            if "429" in str(e):
                print(f"⚠️ Quota hit. Waiting {delays[attempt]} seconds before retrying...")
                time.sleep(delays[attempt])
            else:
                return f"❌ Error: {str(e)}"
    
    return "❌ All retries failed due to API Quota limits. Please try again in a few minutes."

if __name__ == "__main__":
    print(generate_narrative())