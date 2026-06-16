import arxiv
from datetime import datetime, timedelta, timezone

TOPIC = "Retrieval Augmented Generation"
CATEGORY = "cs.AI"
DAYS_BACK = 7
MAX_RESULTS = 15

def fetch_papers(topic: str, category: str, days_back: int, max_results: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    search = arxiv.Search(
        query=f"{topic} and cat={category}",
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    papers = []
    client = arxiv.Client()

    for result in client.results(search):
        if result.published < cutoff:
            break
        papers.append({
            "id":        result.entry_id,
            "title":     result.title,
            "authors":   [a.name for a in result.authors[:3]],
            "abstract":  result.summary.replace("\n", " ").strip(),
            "published": result.published.strftime("%Y-%m-%d"),
            "url":       result.entry_id,
        })

    return papers


if __name__ == "__main__":
    print(f"Fetching papers on {TOPIC} from {CATEGORY}, last {DAYS_BACK} days...\n")
    papers = fetch_papers(TOPIC, CATEGORY, DAYS_BACK, MAX_RESULTS)

    if not papers:
        print("No papers found. Try increasing days back or broadening research TOPIC")

    else:
        print(f"Found {len(papers)} papers:\n")
        for i, p in enumerate(papers, 1):
            print(f"{i}. {p['title']}")
            print(f"   Authors  : {', '.join(p['authors'])}")
            print(f"   Published: {p['published']}")
            print(f"   Abstract : {p['abstract'][:230]}...")
            print()
