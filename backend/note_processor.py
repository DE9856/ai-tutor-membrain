from agent import run_agent


# -------------------------
# SPLIT LARGE NOTES
# -------------------------
def split_into_chunks(text, max_len=200):
    words = text.split()
    chunks = []
    current = []

    for word in words:
        current.append(word)
        if len(" ".join(current)) > max_len:
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))

    return chunks


# -------------------------
# EXTRACT CONCEPTS (LLM)
# -------------------------
def extract_concepts(note_text):
    prompt = f"""
Extract ONLY core learning concepts from the text.

STRICT RULES:
- MAX 3 concepts ONLY
- Each concept MUST be 1-3 words
- NO sentences
- NO explanations
- NO prefixes like "Here are..."
- NO numbering

Return ONLY bullet points.

Text:
{note_text}
"""

    response = run_agent(prompt, use_tools=False)

    # 🔥 DEBUG PRINT (IMPORTANT)
    print("AGENT RESPONSE:", response)

    # -------------------------
    # HANDLE RESPONSE TYPES
    # -------------------------
    if isinstance(response, dict):
        if "final_answer" in response and response["final_answer"]:
            return response["final_answer"]
        
        if "response" in response and response["response"]:
            return response["response"]

    return ""

# -------------------------
# CLEAN OUTPUT
# -------------------------
def clean_concepts(text):
    if not text:
        return []

    lines = text.split("\n")
    concepts = []

    for line in lines:
        line = line.strip("-• ").strip()

        # remove numbering like "1. "
        if "." in line and line.split(".")[0].isdigit():
            line = line.split(".", 1)[1].strip()

        # ❌ remove junk patterns
        if (
            not line
            or "here are" in line.lower()
            or "concept" in line.lower()
            or "function_call" in line.lower()
            or "membrain" in line.lower()
            or len(line) > 30
            or len(line.split()) > 4
        ):
            continue

        concepts.append(line)

    # Deduplicate while preserving model-provided order.
    return list(dict.fromkeys(concepts))
# -------------------------
# MAIN PIPELINE
# -------------------------
def store_note_in_membrain(note_text):
    chunks = split_into_chunks(note_text)

    all_concepts = []
    results = []

    for chunk in chunks:
        raw = extract_concepts(chunk)
        concepts = clean_concepts(raw)[:3]  # limit to top 3 concepts per chunk

        for concept in concepts:
            prompt = f"""
Store this concept using membrain_add.

ONLY call tool.

Content:
{concept}
"""
            result = run_agent(prompt)
            results.append(result)

        all_concepts.extend(concepts)

    return {
        "concepts": all_concepts,
        "stored": results
    }