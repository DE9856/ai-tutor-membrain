from supabase_client import supabase


def call_membrain(action: str, content: str):
    if action == "add":
        supabase.table("memories").insert({
            "content": content
        }).execute()

        return {
            "membrain": "add",
            "status": "stored",
            "content": content
        }

    if action == "search":
        query = content.lower()

        response = supabase.table("memories").select("*").execute()

        results = [
            item["content"]
            for item in response.data
            if query in item["content"].lower()
        ]

        return {
            "membrain": "search",
            "status": "success",
            "query": content,
            "results": results
        }

    return {"error": "invalid action"}