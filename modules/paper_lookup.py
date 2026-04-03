import requests

SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper/"


def fetch_paper_metadata(paper_id):
    url = f"{SEMANTIC_SCHOLAR_BASE}{paper_id}"
    params = {
        "fields": "paperId,title,authors,year,venue,openAccessPdf,citationCount"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"[API] {paper_id} -> status {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"[API TITLE] {paper_id} -> {data.get('title', '')}")
            return data

    except Exception as e:
        print(f"⚠️ API fetch failed for {paper_id}: {e}")

    return None