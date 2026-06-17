from crewai import Task
from agents import fetcher_agent, filter_agent
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
