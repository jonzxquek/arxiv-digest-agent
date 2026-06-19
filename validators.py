import json
import re
from datetime import datetime, timedelta, timezone


# Agent 3 (Cluster agent) validation
# It takes two raw strings — Agent 2's output  
# Agent 1's output — and answers one question: did Agent 2 score and return only the papers it was actually given?
# raw is Agent 2 output, fetch_raw is Agent 1 output
def validate_filter_output(raw: str, fetch_raw: str) -> list | None: # Either returns a list of papers or None if fail
    try:
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            raise json.JSONDecodeError("No JSON array found", raw, 0)
        filtered_papers = json.loads(match.group(0))

        match2 = re.search(r'\[.*\]', fetch_raw, re.DOTALL)
        fetched_papers = json.loads(match2.group(0)) if match2 else []

        fetched_ids  = {p["id"] for p in fetched_papers}
        returned_ids = {p["id"] for p in filtered_papers}
        hallucinated = returned_ids - fetched_ids

        if hallucinated:
            print(f"\n⚠️  AGENT 2 HALLUCINATION — {len(hallucinated)} fabricated paper(s):")
            for hid in hallucinated:
                print(f"   {hid}")
            return None

        print(f"\n✅ Agent 2 valid — {len(filtered_papers)} papers passed filter, all IDs verified.")
        return filtered_papers

    except json.JSONDecodeError:
        print("\n⚠️  Agent 2 output is not valid JSON.")
        return None
    
# Agent 1 hallucination check - previous models had a tendency to skip tool and search its own knowledge base
# Does not listen to system prompt and fetches well known paper from years back then specified range
# Date validation of the papers found by Agent 1
def validate_date_window(papers: list, days_back: int) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    flagged = []

    for p in papers:
        published = datetime.strptime(
            p.get("published", "1900-01-01"), "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc)

        if published < cutoff:
            flagged.append(p)

    if flagged:
        print(f"\n⚠️  DATE WARNING — {len(flagged)} paper(s) outside {days_back}-day window:")
        for p in flagged:
            print(f"   [{p.get('published', '?')}] {p.get('title', p.get('id', '?'))}")
    else:
        print(f"\n✅ Date check passed — all papers within {days_back}-day window.")

    return flagged


# Agent 3 validation, has 5 distinct checks 
def validate_cluster_output(raw: str, filtered_papers: list) -> dict | None:
    try:
        match = re.search(r'\{.*\}', raw, re.DOTALL) # Altered to account for chnage of returned output {}
        # re.DOTALL handles multiline output
        if not match:
            raise json.JSONDecodeError("No JSON object found", raw, 0)
        raw_json = match.group(0)
        while raw_json.startswith('{{') and raw_json.endswith('}}'):
            raw_json = raw_json[1:-1]
        clustered = json.loads(raw_json)

    except json.JSONDecodeError:
        print("\n⚠️  Agent 3 output is not valid JSON.")
        print("Raw output:")
        print(raw)
        return None

    # Before touching any of the nested data passed back, we do a quick check on top level structure
    # If required keys exists in clustered keys - agent may have returned cluster = {} instead of themes = {} correct flow
    # Returns hard None 
    required_keys = {"themes", "total_papers", "total_themes"}
    if not required_keys.issubset(clustered.keys()):
        missing = required_keys - clustered.keys()
        print(f"\n⚠️  Agent 3 output missing required keys: {missing}")
        return None

    filtered_ids      = {p["id"] for p in filtered_papers}
    all_clustered_ids = []
    issues            = []

    # Separate full themes from lone-paper themes
    valid_themes = []
    lone_papers  = []

    for theme in clustered["themes"]:
        theme_papers = theme.get("papers", [])

        if len(theme_papers) < 2:
            print(f"\n⚠️  Theme '{theme.get('name', 'unnamed')}' has only "
                  f"{len(theme_papers)} paper(s) — moving to 'Other Notable Work'.")
            lone_papers.extend(theme_papers)
        else:
            valid_themes.append(theme)

    # Collect lone papers into a catch-all section
    if lone_papers:
        valid_themes.append({
            "name": "Other Notable Work",
            "description": (
                "Papers that offer valuable insights this week but did not "
                "cluster with others into a shared research theme."
            ),
            "papers": lone_papers,
        })
        clustered["themes"]       = valid_themes
        clustered["total_themes"] = len(valid_themes)

    # Check all paper IDs are real and count them
    for theme in clustered["themes"]:
        for paper in theme.get("papers", []):
            pid = paper.get("id")
            all_clustered_ids.append(pid)
            if pid not in filtered_ids:
                issues.append(f"Hallucinated paper ID in clustering: {pid}")

    seen       = set()
    duplicates = set()
    for pid in all_clustered_ids:
        if pid in seen:
            duplicates.add(pid)
        seen.add(pid)

    if duplicates:
        issues.append(f"Duplicate papers across themes: {duplicates}")

    actual_total = len(all_clustered_ids)
    if clustered["total_papers"] != actual_total:
        clustered["total_papers"] = actual_total

    if issues:
        print(f"\n⚠️  Agent 3 validation issues:")
        for issue in issues:
            print(f"   - {issue}")
        return None

    print(
        f"\n✅ Agent 3 valid — {clustered['total_themes']} themes, "
        f"{clustered['total_papers']} papers, all IDs verified."
    )
    for theme in clustered["themes"]:
        print(f"   [{len(theme['papers'])} papers] {theme['name']}")
        print(f"             {theme['description']}")

    return clustered


def validate_writer_output(raw: str, clustered: dict) -> str | None:
    if not raw or not raw.strip():
        print("\n⚠️  Agent 4 returned empty output.")
        return None

    required_sections = ["introduction", "spotlight", "what to watch"]
    missing = [s for s in required_sections if s not in raw.lower()]
    if missing:
        print(f"\n⚠️  Agent 4 output missing sections: {missing}")
        return None

    theme_names = [
        t["name"] for t in clustered.get("themes", [])
        if t["name"] != "Other Notable Work"
    ]
    missing_themes = [t for t in theme_names if t.lower() not in raw.lower()]
    if missing_themes:
        print(f"\n⚠️  Agent 4 output missing theme sections: {missing_themes}")
        return None

    print(f"\n✅ Agent 4 valid — all sections present, {len(theme_names)} themes covered.")
    return raw.strip()

