import requests
from config import S2_API_KEY

def search_papers(topic: str, limit: int):
    if not S2_API_KEY:
        raise RuntimeError("S2_API_KEY not found. Check your .env file.")

    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    headers = {"x-api-key": S2_API_KEY}

    params = {
        "query": topic,
        "limit": limit,
        "fields": "paperId,title,authors,year,abstract,openAccessPdf,citationCount"
    }

    r = requests.get(url, headers=headers, params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Semantic Scholar error {r.status_code}: {r.text}")

    papers = r.json().get("data", [])

    # Better ordering (optional but professional)
    papers = sorted(papers, key=lambda x: x.get("citationCount", 0), reverse=True)
    return papers
