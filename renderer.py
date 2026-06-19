import glob
import json
import os
import re
from datetime import datetime, timedelta


# ─── Colour palette ──────────────────────────────────────────────────────────

PALETTE = [
    {
        "header":       "#D85A30",
        "card_bg":      "#FAECE7",
        "border":       "#D85A30",
        "badge_bg":     "#D85A30",
        "card_outline": False,
    },
    {
        "header":       "#BA7517",
        "card_bg":      "#FAEEDA",
        "border":       "#BA7517",
        "badge_bg":     "#BA7517",
        "card_outline": False,
    },
    {
        "header":       "#5F5E5A",
        "card_bg":      "#F1EFE8",
        "border":       "#5F5E5A",
        "badge_bg":     "#5F5E5A",
        "card_outline": True,
    },
]


def get_theme_palette(index: int) -> dict:
    return PALETTE[index % len(PALETTE)]


# ─── Text helpers ─────────────────────────────────────────────────────────────

def safe_text(text: str) -> str:
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("—", "&mdash;")
    text = text.replace("–", "&ndash;")
    text = text.replace("‘", "&lsquo;")
    text = text.replace("’", "&rsquo;")
    text = text.replace("“", "&ldquo;")
    text = text.replace("”", "&rdquo;")
    text = text.replace("…", "&hellip;")
    text = text.replace("•", "&bull;")
    return text


def bold_to_html(text: str, bold_colour: str = "#1A1A18") -> str:
    return re.sub(
        r'\*\*(.+?)\*\*',
        lambda m: (
            f'<strong style="color:{bold_colour};font-weight:700;">'
            f'{m.group(1)}</strong>'
        ),
        text,
    )


# ─── Markdown parsing ─────────────────────────────────────────────────────────

def parse_markdown(md: str) -> list:
    sections = []
    parts = re.split(r'\n(?=## )', md.strip())
    for part in parts:
        lines = part.strip().split("\n")
        heading = re.sub(r'^#+\s*', '', lines[0]).strip()
        body = "\n".join(lines[1:]).strip()
        sections.append({"heading": heading, "body": body})
    return sections


def extract_theme_description(body: str) -> str:
    """Return the italic description line (*text*) from a theme body, or ''."""
    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue
        if re.match(r'^[\*\-]\s+\*\*', line):
            break
        if line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            return line.strip("*").strip()
    return ""


def extract_narrative_paragraph(body: str) -> str:
    """Return narrative paragraph text from a theme body (non-description, non-bullet lines)."""
    lines = []
    for line in body.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("*") or line.startswith("-"):
            continue
        lines.append(line)
    return " ".join(lines).strip()


def extract_paper_descriptions(sections: list) -> dict:
    """
    Parse Agent 4 markdown bullets across all theme sections.
    Returns {normalised_title: description} where normalised = lowercase stripped.
    Falls back gracefully if a bullet has no separator.
    """
    descs = {}
    for sec in sections:
        h = sec["heading"].lower()
        if h in ("introduction", "intro", "spotlight") or "watch" in h:
            continue
        for line in sec["body"].split("\n"):
            line = line.strip()
            if not re.match(r'^[\*\-]\s+\*\*', line):
                continue
            # Strip bullet marker
            line = re.sub(r'^[\*\-]\s+', '', line)
            # Match **Title** — description  (em dash, en dash, or hyphen)
            m = re.match(r'\*\*(.+?)\*\*\s*[—–\-]\s*(.*)', line)
            if m:
                title = m.group(1).strip()
                desc  = m.group(2).strip()
                if desc:
                    descs[title.lower()] = desc
    return descs


# ─── Metadata helpers ─────────────────────────────────────────────────────────

def get_issue_number() -> int:
    files = glob.glob("outputs/cluster_*.json")
    return max(len(files), 1)


def get_prior_theme_names() -> set:
    files = sorted(glob.glob("outputs/cluster_*.json"))
    if len(files) < 2:
        return set()
    try:
        with open(files[-2]) as f:
            data = json.load(f)
        return {t["name"].lower() for t in data.get("themes", [])}
    except Exception:
        return set()


def compute_stats(clustered: dict) -> dict:
    all_scores = [
        p["relevance_score"]
        for t in clustered.get("themes", [])
        for p in t.get("papers", [])
        if isinstance(p.get("relevance_score"), (int, float))
    ]
    avg = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0
    return {
        "total_selected": clustered.get("total_papers", 0),
        "total_themes":   clustered.get("total_themes", 0),
        "avg_score":      avg,
    }


# ─── HTML component builders ──────────────────────────────────────────────────

def build_paper_card(paper: dict, palette: dict, agent4_desc: str = "") -> str:
    title  = safe_text(paper.get("title", ""))
    desc   = safe_text(agent4_desc) if agent4_desc else safe_text(paper.get("reason", ""))
    score  = paper.get("relevance_score", "")

    if palette["card_outline"]:
        border_style = (
            f"border:0.5px solid #D3D1C7;"
            f"border-left:3px solid {palette['border']};"
        )
    else:
        border_style = f"border-left:3px solid {palette['border']};"

    return (
        f'<div class="paper-card" '
        f'style="background:{palette["card_bg"]};{border_style}">\n'
        f'  <span class="score-badge" '
        f'style="background:{palette["badge_bg"]};">{score}/10</span>\n'
        f'  <p class="card-title">{title}</p>\n'
        f'  <p class="card-desc">{desc}</p>\n'
        f'</div>'
    )


def build_theme_section(theme: dict, index: int,
                        prior_themes: set,
                        md_body: str = "",
                        paper_descs: dict = None) -> str:
    palette      = get_theme_palette(index)
    name         = theme.get("name", "")
    papers       = theme.get("papers", [])
    paper_count  = len(papers)
    is_new       = bool(prior_themes) and name.lower() not in prior_themes
    margin_top   = "" if index == 0 else "margin-top:6px;"
    plural       = "s" if paper_count != 1 else ""
    new_badge    = '<span class="new-badge">NEW</span>' if is_new else ""

    header = (
        f'<div class="section-header" '
        f'style="background:{palette["header"]};{margin_top}">\n'
        f'  <span class="section-header-left serif">'
        f'{safe_text(name.upper())}{new_badge}</span>\n'
        f'  <span class="papers-pill">{paper_count} paper{plural}</span>\n'
        f'</div>'
    )

    description = extract_theme_description(md_body)
    desc_html   = (
        f'  <p class="theme-desc">{safe_text(description)}</p>\n'
        if description else ""
    )

    narrative = extract_narrative_paragraph(md_body)
    narrative_html = (
        f'  <p style="font-size:13px;line-height:1.75;color:#1A1A18;'
        f'margin-bottom:14px;">{safe_text(narrative)}</p>\n'
        if narrative else ""
    )

    descs      = paper_descs or {}
    cards_html = "\n".join(
        build_paper_card(p, palette, descs.get(p.get("title", "").lower(), ""))
        for p in papers
    )

    body = (
        f'<div class="section-body">\n'
        f'{desc_html}'
        f'{narrative_html}'
        f'{cards_html}\n'
        f'</div>'
    )
    return header + "\n" + body


def build_relevance_bars(clustered: dict) -> str:
    all_papers = []
    for i, theme in enumerate(clustered.get("themes", [])):
        for paper in theme.get("papers", []):
            all_papers.append({**paper, "_theme_index": i})

    all_papers.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)

    rows = []
    for paper in all_papers:
        palette = get_theme_palette(paper["_theme_index"])
        title   = paper.get("title", "")
        label   = safe_text((title[:35] + "…") if len(title) > 35 else title)
        score   = paper.get("relevance_score", 0)
        pct     = (score / 10) * 100

        rows.append(
            f'  <div class="bar-row">\n'
            f'    <span class="bar-label">{label}</span>\n'
            f'    <div class="bar-track-cell">'
            f'<div class="bar-track">'
            f'<div class="bar-fill" '
            f'style="width:{pct}%;background:{palette["header"]};"></div>'
            f'</div></div>\n'
            f'    <span class="bar-score" '
            f'style="color:{palette["header"]};">{score}/10</span>\n'
            f'  </div>'
        )

    return (
        f'<div class="relevance-section">\n'
        f'  <p class="relevance-title">Paper relevance scores this week</p>\n'
        + "\n".join(rows)
        + "\n</div>"
    )


def _find_md_body(theme_name: str, md_sections_map: dict) -> str:
    """Fuzzy-match a cluster theme name to a markdown section using first-4-word overlap."""
    theme_words = theme_name.lower().split()[:4]
    theme_4     = " ".join(theme_words)
    theme_set   = set(theme_words)

    best_body  = ""
    best_score = 0

    for key, body in md_sections_map.items():
        key_words = key.split()[:4]
        key_4     = " ".join(key_words)
        key_set   = set(key_words)

        if theme_4 in key_4 or key_4 in theme_4:
            return body

        shared = len(theme_set & key_set)
        if shared >= 2 and shared > best_score:
            best_score = shared
            best_body  = body

    return best_body


# ─── Full HTML document ───────────────────────────────────────────────────────

def build_html(sections: list, clustered: dict,
               topic: str, date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        dt = datetime.now()

    display_date = dt.strftime("%d %B %Y")
    start_dt     = dt - timedelta(days=7)

    if start_dt.month == dt.month:
        week_range = f"{start_dt.day}&ndash;{dt.strftime('%d %B %Y')}"
    else:
        week_range = (
            f"{start_dt.strftime('%d %B')}&ndash;{dt.strftime('%d %B %Y')}"
        )

    issue_number = get_issue_number()
    prior_themes = get_prior_theme_names()
    themes       = clustered.get("themes", [])

    # Extract Agent 4 per-paper descriptions from markdown bullets
    paper_descs = extract_paper_descriptions(sections)

    # Bucket markdown sections
    intro_body     = ""
    spotlight_body = ""
    watch_body     = ""
    md_sections_map: dict = {}
    for sec in sections:
        h = sec["heading"].lower()
        if h in ("introduction", "intro"):
            intro_body = sec["body"]
        elif "spotlight" in h:
            spotlight_body = sec["body"]
        elif "watch" in h:
            watch_body = sec["body"]
        else:
            md_sections_map[h] = sec["body"]

    # ── 1. Topbar ─────────────────────────────────────────────────────────────
    topbar = (
        f'<div class="topbar">\n'
        f'  <span class="topbar-left">ArXiv Research Digest</span>\n'
        f'  <span class="topbar-right">'
        f'{safe_text(display_date)} &middot; Issue #{issue_number}</span>\n'
        f'</div>'
    )

    # ── 2. Cover ──────────────────────────────────────────────────────────────
    subtitle   = f"cs.AI &middot; 7-day window &middot; Week of {week_range}"
    intro_html = bold_to_html(safe_text(intro_body)) if intro_body else ""
    cover = (
        f'<div class="cover">\n'
        f'  <h1 class="cover-title serif">{safe_text(topic)}</h1>\n'
        f'  <p class="cover-subtitle">{subtitle}</p>\n'
        f'  <p class="intro-para">{intro_html}</p>\n'
        f'</div>'
    )

    # ── 3. Stats bar ──────────────────────────────────────────────────────────
    if themes:
        s = compute_stats(clustered)
        stats_html = (
            f'<div class="stats-bar">\n'
            f'  <div class="stat-cell">\n'
            f'    <span class="stat-number">{s["total_selected"]}</span>\n'
            f'    <span class="stat-label">Papers Selected</span>\n'
            f'  </div>\n'
            f'  <div class="stat-cell">\n'
            f'    <span class="stat-number">{s["total_themes"]}</span>\n'
            f'    <span class="stat-label">Themes Identified</span>\n'
            f'  </div>\n'
            f'  <div class="stat-cell" style="border-right:none;">\n'
            f'    <span class="stat-number">{s["avg_score"]}</span>\n'
            f'    <span class="stat-label">Avg Relevance Score</span>\n'
            f'  </div>\n'
            f'</div>'
        )
    else:
        stats_html = ""

    # ── 4. Relevance bars ─────────────────────────────────────────────────────
    bars_html = build_relevance_bars(clustered) if themes else ""

    # ── 5. Theme sections ─────────────────────────────────────────────────────
    theme_sections_html = ""
    if themes:
        theme_sections_html = "\n".join(
            build_theme_section(
                theme, i, prior_themes,
                _find_md_body(theme.get("name", ""), md_sections_map),
                paper_descs,
            )
            for i, theme in enumerate(themes)
        )

    # ── 6. Spotlight ──────────────────────────────────────────────────────────
    if spotlight_body:
        body_safe      = bold_to_html(safe_text(spotlight_body), bold_colour="#fff")
        spotlight_html = (
            f'<div class="section-header" style="background:#712B13;">\n'
            f'  <span class="section-header-left serif">'
            f'&#9670; Spotlight</span>\n'
            f'</div>\n'
            f'<div class="spotlight-body"><p>{body_safe}</p></div>'
        )
    else:
        spotlight_html = ""

    # ── 7. What to Watch ──────────────────────────────────────────────────────
    if watch_body:
        watch_html = (
            f'<div class="section-header" style="background:#444441;">\n'
            f'  <span class="section-header-left serif">'
            f'&#8594; What to Watch</span>\n'
            f'</div>\n'
            f'<div class="watch-body"><p>{safe_text(watch_body)}</p></div>'
        )
    else:
        watch_html = ""

    # ── 8. Footer ─────────────────────────────────────────────────────────────
    footer = (
        f'<div class="footer">\n'
        f'  <span class="footer-left">ArXiv Research Digest &middot; '
        f'Generated by AI Pipeline</span>\n'
        f'  <span class="footer-right">{safe_text(display_date)} &middot; '
        f'{safe_text(topic)}</span>\n'
        f'</div>'
    )

    # ── CSS ───────────────────────────────────────────────────────────────────
    css = """
    @page { size: A4; margin: 0; }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      background: #F1EFE8;
      font-family: Arial, Helvetica, sans-serif;
      font-weight: 400;
      color: #1A1A18;
      font-size: 13px;
    }

    .serif { font-family: Georgia, 'Times New Roman', serif; }

    /* 1. Topbar — float layout */
    .topbar {
      background: #D85A30;
      height: 44px;
      padding: 0 28px;
      overflow: hidden;
      line-height: 44px;
    }
    .topbar-left {
      float: left;
      color: white;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }
    .topbar-right { float: right; color: #F5C4B3; font-size: 11px; }

    /* 2. Cover */
    .cover { padding: 32px 28px 0; }
    .cover-title {
      font-size: 30px;
      font-weight: 700;
      color: #1A1A18;
      letter-spacing: -0.02em;
      line-height: 1.2;
      margin-bottom: 6px;
    }
    .cover-subtitle { font-size: 12px; color: #888780; margin-bottom: 16px; }
    .intro-para {
      font-size: 13px;
      line-height: 1.75;
      border-left: 3px solid #D85A30;
      padding-left: 14px;
      margin-bottom: 20px;
    }

    /* 3. Stats bar — table layout */
    .stats-bar {
      display: table;
      width: 100%;
      border-spacing: 0;
      border-top: 1px solid #D3D1C7;
      border-bottom: 1px solid #D3D1C7;
    }
    .stat-cell {
      display: table-cell;
      width: 33.33%;
      text-align: center;
      vertical-align: middle;
      padding: 12px 8px;
      border-right: 1px solid #D3D1C7;
    }
    .stat-number {
      display: block;
      font-size: 20px;
      font-weight: 700;
      color: #D85A30;
      line-height: 1;
      margin-bottom: 4px;
    }
    .stat-label {
      display: block;
      font-size: 10px;
      color: #888780;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    /* 4. Relevance bars — table layout */
    .relevance-section { padding: 14px 28px 18px; background: #F1EFE8; }
    .relevance-title {
      font-size: 10px;
      font-weight: 700;
      color: #888780;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 10px;
    }
    .bar-row {
      display: table;
      width: 100%;
      border-spacing: 0;
      margin-bottom: 6px;
    }
    .bar-label {
      display: table-cell;
      font-size: 10px;
      color: #5F5E5A;
      width: 150px;
      vertical-align: middle;
      white-space: nowrap;
      overflow: hidden;
    }
    .bar-track-cell {
      display: table-cell;
      vertical-align: middle;
      padding: 0 8px;
    }
    .bar-track {
      background: #D3D1C7;
      height: 6px;
      border-radius: 4px;
      overflow: hidden;
    }
    .bar-fill { height: 6px; border-radius: 4px; }
    .bar-score {
      display: table-cell;
      font-size: 10px;
      font-weight: 700;
      width: 32px;
      text-align: right;
      vertical-align: middle;
    }

    /* 5. Section headers — float layout */
    .section-header {
      overflow: hidden;
      padding: 9px 28px;
    }
    .section-header-left {
      float: left;
      color: white;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      line-height: 1.8;
    }
    .new-badge {
      background: rgba(255,255,255,0.25);
      color: white;
      font-size: 9px;
      font-weight: 700;
      padding: 1px 7px;
      border-radius: 20px;
      margin-left: 8px;
      font-family: Arial, Helvetica, sans-serif;
      vertical-align: middle;
    }
    .papers-pill {
      float: right;
      background: rgba(255,255,255,0.22);
      color: white;
      font-size: 10px;
      font-weight: 700;
      padding: 4px 9px;
      border-radius: 20px;
      line-height: 1.6;
    }

    /* 5b. Section body */
    .section-body { padding: 12px 28px 8px; background: #F1EFE8; }
    .theme-desc {
      font-size: 12px;
      font-style: italic;
      color: #5F5E5A;
      margin-bottom: 10px;
      line-height: 1.6;
    }

    /* Paper cards — float badge */
    .paper-card {
      border-radius: 0 8px 8px 0;
      padding: 10px 12px 8px;
      margin-bottom: 8px;
      overflow: hidden;
    }
    .score-badge {
      float: right;
      color: white;
      font-size: 9px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 20px;
      white-space: nowrap;
      margin-left: 8px;
    }
    .card-title {
      font-size: 12px;
      font-weight: 700;
      color: #1A1A18;
      line-height: 1.4;
    }
    .card-desc { font-size: 11px; color: #5F5E5A; line-height: 1.6; margin-top: 3px; }

    /* 6. Spotlight */
    .spotlight-body {
      background: #993C1D;
      padding: 14px 28px 18px;
      font-size: 13px;
      line-height: 1.75;
      color: #FAECE7;
    }

    /* 7. What to Watch */
    .watch-body {
      padding: 14px 28px 20px;
      background: #F1EFE8;
      font-size: 13px;
      font-style: italic;
      line-height: 1.75;
      color: #1A1A18;
    }

    /* 8. Footer — float layout */
    .footer {
      border-top: 1px solid #D3D1C7;
      padding: 10px 28px;
      overflow: hidden;
      font-size: 10px;
      color: #B4B2A9;
      background: #F1EFE8;
    }
    .footer-left { float: left; }
    .footer-right { float: right; }

    /* Content wrapper — 75% width, centred */
    .content-wrap {
      max-width: 75%;
      margin: 0 auto;
    }
    """

    inner_parts = [
        cover, stats_html, bars_html,
        theme_sections_html, spotlight_html, watch_html, footer,
    ]
    inner_html = "\n".join(p for p in inner_parts if p)

    return (
        f'<!DOCTYPE html>\n'
        f'<html lang="en">\n'
        f'<head>\n'
        f'  <meta charset="UTF-8">\n'
        f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'  <title>ArXiv Research Digest &mdash; '
        f'{safe_text(display_date)}</title>\n'
        f'  <style>\n{css}\n  </style>\n'
        f'</head>\n'
        f'<body>\n'
        f'{topbar}\n'
        f'<div class="content-wrap">\n'
        f'{inner_html}\n'
        f'</div>\n'
        f'</body>\n</html>'
    )


# ─── Entry point ──────────────────────────────────────────────────────────────

def generate_pdf(md_path: str, pdf_path: str,
                 topic: str = "", clustered: dict = None):
    from weasyprint import HTML as WeasyHTML

    with open(md_path, "r", encoding="utf-8") as f:
        md = f.read()

    sections = parse_markdown(md)

    stem        = os.path.splitext(os.path.basename(md_path))[0]
    date_match  = re.search(r'\d{4}-\d{2}-\d{2}', stem)
    date_str    = (
        date_match.group(0) if date_match
        else datetime.now().strftime("%Y-%m-%d")
    )

    html_str  = build_html(sections, clustered or {}, topic, date_str)

    html_path = os.path.join(os.path.dirname(md_path), stem + ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_str)
    print(f"HTML preview saved to {html_path} — open in browser to preview")

    WeasyHTML(string=html_str).write_pdf(pdf_path)
    print(f"PDF saved to {pdf_path}")


if __name__ == "__main__":
    today        = datetime.now().strftime("%Y-%m-%d")
    md_path      = f"outputs/digest_{today}.md"
    pdf_path     = f"outputs/digest_{today}.pdf"
    cluster_path = f"outputs/cluster_{today}.json"
    with open(cluster_path) as f:
        clustered = json.load(f)
    generate_pdf(
        md_path, pdf_path,
        topic="Retrieval Augmented Generation",
        clustered=clustered,
    )
