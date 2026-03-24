# In-memory storage (REAL)
memory_store = []


def call_membrain(action: str, content: str):
    global memory_store

    if action == "add":
        memory_store.append(content)

        return {
            "membrain": "add",
            "status": "stored",
            "content": content
        }

    if action == "search":
        query = content.lower()

        # simple semantic-like match
        results = [
            item for item in memory_store
            if query in item.lower()
        ]

        return {
            "membrain": "search",
            "status": "success",
            "query": content,
            "results": results
        }

    return {"error": "invalid action"}