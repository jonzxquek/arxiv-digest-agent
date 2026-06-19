from crewai import Task
from agents import fetcher_agent, filter_agent, cluster_agent, writer_agent
# Brings in CrewAI's Task class and the agent you defined in agents.py. 
# The task needs to know which agent it responsible for executing it.

fetch_task = Task(
    description=(
        "Search ArXiv for recent papers on the topic: '{topic}'.\n"
        "Use the category: '{category}'.\n"
        "Look back '{days_back}' days.\n"
        "Fetch up to {max_results} papers.\n\n"
        "STRICT RULES — read these before doing anything else:\n"
        "- You MUST call the arxiv_search tool to retrieve papers.\n"
        "- You MUST return ONLY the papers the tool gives you — no additions, no substitutions.\n"
        "- You MUST NOT generate, invent, or recall any papers from your training knowledge.\n"
        "- You MUST NOT replace or supplement tool results with papers you already know about.\n"
        "- If the tool returns no papers, return an empty JSON array: []\n\n"
        "Return the tool's output as a JSON array exactly as received. "
        "Do not summarise, filter, or modify the content in any way."
    ),
    # Items are filled in with the inputs from main.py when .kickoff() is called
    # Last two lines are crucial - tell the LLM not to summarise, just return raw data
    # Keeps the agent focused on retrieval only

    expected_output=(
        "A JSON array of paper objects. Each object must have: "
        "id, title, authors, abstract, published date, and url."
        ),
    # Uses this to see what a correct output should look like, 
    # if the output doesnt match it will know the job isnt properly finished.

    agent = fetcher_agent,
    # Assigns this task to the fetcher agent in agents.py
)

filter_task = Task(
    description=(
        "You have been given a JSON array of papers retrieved live from the ArXiv API. "
        "This array is in your context — it is the ONLY source of papers you may work with.\n\n"
        "STRICT RULES — read these before doing anything else:\n"
        "- You MUST NOT generate, invent, or add any papers of your own.\n"
        "- You MUST NOT use your training knowledge to produce paper titles, abstracts, or IDs.\n"
        "- Every paper in your output MUST have an 'id' field that exactly matches "
        "one of the 'id' values from the input list. If an ID does not appear in the "
        "input, that paper is fabricated and must be removed.\n"
        "- If you are unsure whether a paper came from the input, exclude it.\n\n"
        "YOUR TASK:\n"
        "1. Parse the JSON array from your context. Count how many papers are in it "
        "and state that count internally before proceeding.\n"
        "2. For each paper in that list — and only those papers — score it 1-10 "
        "for relevance to the topic: '{topic}'.\n"
        "   Score 10: The paper's PRIMARY contribution directly advances {topic}. "
        "The abstract names {topic} as the central subject. Reserve this for papers "
        "where {topic} IS the research, not a tool or application domain.\n"
        "   Score 9:  Strongly focused on {topic} but with meaningful secondary scope — "
        "e.g. applied to a specific subdomain, or {topic} combined with one other method.\n"
        "   Score 7-8: {topic} is a core component but the paper is broader — "
        "uses {topic} as a technique within a larger system, or benchmarks it against others.\n"
        "   Score 6:  {topic} is clearly present and substantive but not the main focus — "
        "one section or contribution among several unrelated ones.\n"
        "   Score 1-5: {topic} is only mentioned tangentially or in passing — exclude these.\n"
        "3. Keep only papers scoring 6 or above.\n"
        "4. For each kept paper, copy ALL original fields exactly as received, "
        "then add two new fields: 'relevance_score' (integer) and 'reason' "
        "(one sentence referencing specific content from that paper's abstract).\n\n"
        "OUTPUT FORMAT:\n"
        "Return ONLY a raw JSON array starting with [ and ending with ]. "
        "No markdown, no code fences, no explanation text, no preamble."
    ),
    expected_output=(
        "A raw JSON array where every object: "
        "(1) has an 'id' field exactly matching one from the input list, "
        "(2) contains all original fields copied verbatim from the input, "
        "(3) has a 'relevance_score' integer between 6 and 10, "
        "(4) has a 'reason' string citing specific content from that paper's abstract. "
        "No fabricated papers. No papers with IDs not present in the input."
    ),
    agent=filter_agent,
    context=[fetch_task]
)

cluster_task = Task(
    description=(
        "You have been given a JSON array of scored, filtered ArXiv papers "
        "on the topic '{topic}'. This array is in your context from the "
        "previous task and is the ONLY source of papers you may work with.\n\n"

        "STRICT RULES:\n"
        "- You MUST NOT invent, generate, or add any papers of your own.\n"
        "- You MUST NOT use training knowledge to produce paper content.\n"
        "- Every paper in your output must have an 'id' that exactly matches "
        "one from the input list.\n"
        "- Do not duplicate papers across themes.\n"
        "- Every theme must contain at least 2 papers. "
        "If any theme would have only 1 paper, move that paper into the "
        "most topically related existing theme — do not leave it alone.\n\n"

        "YOUR TASK:\n"
        "1. Read all paper titles and abstracts carefully.\n"
        "2. Group papers into 3-5 themes that arise from what the papers "
        "actually say — not predefined categories.\n"
        "3. Check every theme: if any has only 1 paper, merge it into the "
        "most topically related theme before finalising.\n"
        "4. Assign each paper to exactly one theme — the one it fits best.\n"
        "5. Name each theme in plain English (5-8 words maximum).\n"
        "6. Write a one-sentence description for each theme that explains "
        "what specifically unifies the papers in it.\n\n"

        "For each paper inside a theme, include only these fields:\n"
        "id, title, relevance_score, reason\n\n"

        "OUTPUT FORMAT:\n"
        "Return ONLY a raw JSON object starting with {{ and ending with }}.\n"
        "No markdown, no code fences, no explanation text, no preamble.\n\n"

        "The JSON must follow this exact structure:\n"
        "{{\n"
        '  "themes": [\n'
        "    {{\n"
        '      "name": "theme name here",\n'
        '      "description": "one sentence explaining what unifies these papers",\n'
        '      "papers": [\n'
        "        {{\n"
        '          "id": "arxiv url",\n'
        '          "title": "paper title",\n'
        '          "relevance_score": 8,\n'
        '          "reason": "one sentence from scoring agent"\n'
        "        }}\n"
        "      ]\n"
        "    }}\n"
        "  ],\n"
        '  "total_papers": 14,\n'
        '  "total_themes": 3\n'
        "}}"
    ),
    expected_output=(
        "A raw JSON object with a 'themes' array. Each theme has: "
        "name (str), description (str), papers (array of objects with "
        "id, title, relevance_score, reason). "
        "Plus top-level fields: total_papers (int), total_themes (int). "
        "No fabricated papers. No duplicate papers across themes. "
        "Every paper id must match one from the input list."
    ),
    agent= cluster_agent,
    context=[filter_task],
)

writer_task = Task(
    description=(
        "You have been given a JSON object containing research papers grouped "
        "into named themes on the topic '{topic}'. This is in your context from "
        "the previous task and is the ONLY source of content you may use.\n\n"

        "STRICT RULES:\n"
        "- You MUST NOT invent, fabricate, or add any papers, findings, or claims "
        "not present in your context.\n"
        "- Do not include raw JSON, paper IDs, code blocks, or relevance scores "
        "in your output.\n"
        "- Write only in clean markdown — headers, paragraphs, and bullet points.\n\n"

        "YOUR TASK:\n"
        "Write a weekly AI research newsletter digest with the following sections "
        "in this exact order:\n\n"
        "1. **Introduction** (2-3 sentences): What was the dominant research "
        "focus this week? What is the single most important pattern across all themes?\n\n"
        "2. **Theme Sections** (one per theme): Use the theme name as a markdown "
        "header (##). Write 2-3 sentences summarising what the papers in that theme "
        "collectively say — not a list of papers, but a synthesised insight. "
        "Then list each paper as a bullet: bold title, followed by one sentence "
        "on its specific contribution.\n\n"
        "3. **Spotlight Paper** (## Spotlight): Pick the single most significant "
        "paper across all themes. Write a short paragraph (3-4 sentences) explaining "
        "what it does, why it matters, and what it changes.\n\n"
        "4. **What to Watch** (## What to Watch): One paragraph (2-3 sentences) "
        "on the open question or emerging direction these papers collectively point toward.\n\n"
        "Write with authority and precision. Every sentence must earn its place."
    ),
    expected_output=(
        "A clean markdown string with four sections in order: Introduction, "
        "one ## section per theme, ## Spotlight, ## What to Watch. "
        "No JSON, no code blocks, no paper IDs, no relevance scores. "
        "All content must be grounded in the papers provided in context."
    ),
    agent=writer_agent,
    context=[cluster_task],
)
