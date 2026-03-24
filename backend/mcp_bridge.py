from supabase_client import supabase


def call_membrain(action: str, content: str, user_id: str):
    # -------------------------
    # ADD MEMORY
    # -------------------------
    if action == "add":
        # 🔍 check duplicates ONLY for this user
        response = supabase.table("memories") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()

        existing = [
            item["content"].lower()
            for item in response.data
        ]

        if content.lower() in existing:
            return {
                "membrain": "add",
                "status": "duplicate_skipped",
                "content": content,
                "user_id": user_id
            }

        # ✅ insert if new
        supabase.table("memories").insert({
            "content": content,
            "user_id": user_id
        }).execute()

        return {
            "membrain": "add",
            "status": "stored",
            "content": content,
            "user_id": user_id
        }

    # -------------------------
    # SEARCH MEMORY
    # -------------------------
    if action == "search":
        query = content.lower()

        # 🔥 ONLY THIS USER'S DATA
        response = supabase.table("memories") \
            .select("*") \
            .eq("user_id", user_id) \
            .execute()

        results = list(set([
            item["content"]
            for item in response.data
            if query in item["content"].lower()
        ]))

        return {
            "membrain": "search",
            "status": "success",
            "query": content,
            "results": results,
            "user_id": user_id
        }

    return {"error": "invalid action"}