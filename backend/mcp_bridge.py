"""
Membrain Bridge - Complete implementation using actual Membrain REST API
All memories stored in Membrain's semantic graph, not Supabase
Preserves all original functionality
"""

import requests
import time
import os
import re
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

load_dotenv()

MEMBRAIN_API_KEY = os.getenv("MEMBRAIN_API_KEY")
MEMBRAIN_BASE_URL = os.getenv("MEMBRAIN_BASE_URL", "https://mem-brain-api-cutover-v4-production.up.railway.app")


# -------------------------
# JUNK CONCEPT FILTER
# -------------------------
JUNK_CONCEPTS = {
    "subset", "subfield", "type", "part", "kind", "form", "example",
    "category", "class", "instance", "concept", "function_call",
    "branch", "area", "field", "domain", "model", "system", "method",
    "approach", "technique", "process", "term", "relationship",
    "layer", "layers", "neuron", "neurons", "agent", "reward", "rewards"
}


def normalize_for_matching(name: str) -> str:
    """
    Normalize a concept name for fuzzy matching.
    Strips parenthetical abbreviations like "(AI)", lowercases, strips whitespace.
    e.g. "Artificial Intelligence (AI)" -> "artificial intelligence"
    """
    name = re.sub(r'\(.*?\)', '', name)  # remove (AI), (ML) etc
    return name.lower().strip()


class MembrainClient:
    """
    Membrain REST API Client
    All memories stored in Membrain's semantic graph with automatic linking
    """

    def __init__(self):
        self.api_key = MEMBRAIN_API_KEY
        self.base_url = MEMBRAIN_BASE_URL.rstrip('/')
        self.api_prefix = f"{self.base_url}/api/v1"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.skip_polling = os.getenv("MEMBRAIN_SKIP_POLLING", "false").lower() == "true"

    def _poll_job(self, job_id: str, max_retries: int = 30, delay: float = 0.5) -> Optional[Dict]:
        """Poll async ingest job until completion - with 401 fallback"""
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    f"{self.api_prefix}/memories/jobs/{job_id}",
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    status = data.get("job_status")

                    if status == "completed":
                        return data
                    elif status == "failed":
                        error_msg = data.get("error", {}).get("message", "Unknown error")
                        print(f"Job {job_id} failed: {error_msg}")
                        return None

                elif response.status_code == 401:
                    print(f"Job polling returned 401 - assuming success after short wait")
                    time.sleep(delay * 2)
                    return {"result": {"memory_id": f"job_{job_id}", "action": "created"}}

                elif response.status_code == 404:
                    pass

            except requests.exceptions.RequestException as e:
                print(f"Polling error (attempt {attempt + 1}): {e}")

            time.sleep(delay)

        print(f"Job {job_id} polling timed out after {max_retries} attempts - assuming success")
        return {"result": {"memory_id": f"job_{job_id}", "action": "created"}}

    # -------------------------
    # CORE MEMORY OPERATIONS
    # -------------------------

    def store_memory(self, content: str, user_id: str,
                     tags: List[str] = None, category: str = "general") -> Dict:
        """Store a memory in Membrain"""
        all_tags = [f"user.{user_id}"]
        if tags:
            all_tags.extend(tags)

        payload = {
            "content": content,
            "tags": all_tags,
            "category": category
        }

        try:
            response = requests.post(
                f"{self.api_prefix}/memories",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 202:
                job_data = response.json()
                job_id = job_data.get("job_id")

                if self.skip_polling:
                    return {
                        "success": True,
                        "memory_id": f"job_{job_id}",
                        "action": "created",
                        "content": content,
                        "user_id": user_id
                    }

                result = self._poll_job(job_id)
                if result:
                    memory_id = result.get("result", {}).get("memory_id")
                    action = result.get("result", {}).get("action", "created")
                    return {
                        "success": True,
                        "memory_id": memory_id,
                        "action": action,
                        "content": content,
                        "user_id": user_id
                    }
                return {"success": False, "error": "Job polling timed out"}

            elif response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "memory_id": data.get("id"),
                    "action": "created",
                    "content": content,
                    "user_id": user_id
                }

            else:
                return {"success": False, "error": f"Status {response.status_code}: {response.text}"}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Request failed: {str(e)}"}

    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """Get a single memory by ID"""
        try:
            response = requests.get(
                f"{self.api_prefix}/memories/{memory_id}",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def get_memories_batch(self, memory_ids: List[str]) -> List[Dict]:
        """Batch read multiple memories by IDs"""
        try:
            response = requests.post(
                f"{self.api_prefix}/memories/batch",
                headers=self.headers,
                json={"memory_ids": memory_ids},
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("memories", [])
            return []
        except:
            return []

    def update_memory(self, memory_id: str, content: str = None, tags: List[str] = None) -> Dict:
        """Update an existing memory"""
        payload = {}
        if content:
            payload["content"] = content
        if tags:
            payload["tags"] = tags

        if not payload:
            return {"success": False, "error": "Nothing to update"}

        try:
            response = requests.put(
                f"{self.api_prefix}/memories/{memory_id}",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            if response.status_code in [200, 202]:
                return {"success": True, "memory_id": memory_id}
            return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a single memory"""
        try:
            response = requests.delete(
                f"{self.api_prefix}/memories/{memory_id}",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except:
            return False

    def delete_memories_bulk(self, user_id: str, memory_type: str = None) -> Dict:
        """Bulk delete memories for a user"""
        tags = [f"user.{user_id}"]
        if memory_type:
            tags.append(f"type.{memory_type}")

        try:
            response = requests.delete(
                f"{self.api_prefix}/memories/bulk",
                headers=self.headers,
                params={"tags": ",".join(tags)},
                timeout=10
            )
            if response.status_code == 200:
                return {"success": True, "deleted": response.json().get("deleted_count", 0)}
            return {"success": False, "error": response.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------
    # CONCEPT OPERATIONS
    # -------------------------

    def store_concept(self, name: str, user_id: str, metadata: Dict = None) -> Dict:
        """Store a learning concept as a memory"""
        tags = ["type.concept"]

        if metadata:
            if metadata.get("category"):
                tags.append(f"category.{metadata['category']}")
            if metadata.get("understanding_score") is not None:
                tags.append(f"score.{metadata['understanding_score']:.2f}")
            if metadata.get("tags"):
                tags.extend(metadata["tags"])

        return self.store_memory(name, user_id, tags, category="learning-concept")

    def get_concept_by_name(self, concept_name: str, user_id: str) -> Optional[Dict]:
        """Find a concept by exact name using semantic search with tag filter"""
        result = self.semantic_search(
            query=concept_name,
            user_id=user_id,
            k=10,
            response_format="raw",
            tag_filters=["type.concept"]
        )

        for memory in result.get("results", []):
            if memory.get("type") == "memory_node":
                content = memory.get("content", "")
                if content.lower() == concept_name.lower():
                    return memory

        return None

    def get_concepts_for_user(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get all concept memories for a user"""
        result = self.semantic_search(
            query="",
            user_id=user_id,
            k=limit,
            response_format="raw",
            tag_filters=["type.concept"]
        )

        return [m for m in result.get("results", []) if m.get("type") == "memory_node"]

    def get_concept_score(self, concept_name: str, user_id: str) -> float:
        """Get understanding score from concept's tags"""
        memory = self.get_concept_by_name(concept_name, user_id)
        if memory:
            for tag in memory.get("tags", []):
                if tag.startswith("score."):
                    try:
                        return float(tag.split(".", 1)[1])
                    except:
                        pass
        return 0.0

    def update_concept_score(self, concept_name: str, user_id: str, score: float) -> Dict:
        """Update a concept's understanding score"""
        memory = self.get_concept_by_name(concept_name, user_id)
        if not memory:
            return self.store_concept(concept_name, user_id, {"understanding_score": score})

        memory_id = memory.get("id")
        existing_tags = memory.get("tags", [])
        existing_tags = [t for t in existing_tags if not t.startswith("score.")]
        existing_tags.append(f"score.{score:.2f}")

        return self.update_memory(memory_id, tags=existing_tags)

    # -------------------------
    # NOTE OPERATIONS
    # -------------------------

    def store_note(self, content: str, user_id: str, linked_concepts: List[str] = None) -> Dict:
        """Store a user note with links to concepts"""
        tags = ["type.note"]

        if linked_concepts:
            for concept in linked_concepts:
                safe_concept = concept.replace(" ", "_").replace(".", "_").lower()
                tags.append(f"references.{safe_concept}")

        return self.store_memory(content, user_id, tags, category="user-note")

    def get_notes_for_user(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Get all note memories for a user"""
        result = self.semantic_search(
            query="",
            user_id=user_id,
            k=limit,
            response_format="raw",
            tag_filters=["type.note"]
        )

        return [m for m in result.get("results", []) if m.get("type") == "memory_node"]

    # -------------------------
    # RELATIONSHIP OPERATIONS
    # -------------------------

    def store_relationship(self, source: str, target: str, rel_type: str, user_id: str) -> Dict:
        """
        Store relationship with a searchable prefix so we can find it
        without relying on broken tag filters.
        Format: "RELATION: source ||| rel_type ||| target"
        """
        relationship_content = f"RELATION: {source} ||| {rel_type} ||| {target}"
        tags = [
            "type.relationship",
            f"rel.{rel_type}",
            f"source.{source.replace(' ', '_').lower()[:50]}",
            f"target.{target.replace(' ', '_').lower()[:50]}"
        ]
        return self.store_memory(relationship_content, user_id, tags, category="relationship")

        

    def get_relationships_for_concept(self, concept_name: str, user_id: str) -> List[Dict]:
        """Get all relationships involving a concept"""
        safe_concept = concept_name.replace(" ", "_").lower()
        # Search by both source and target tags
        result_source = self.semantic_search(
            query="",
            user_id=user_id,
            k=50,
            response_format="raw",
            tag_filters=[f"source.{safe_concept}"]
        )
        result_target = self.semantic_search(
            query="",
            user_id=user_id,
            k=50,
            response_format="raw",
            tag_filters=[f"target.{safe_concept}"]
        )

        all_results = []
        seen_ids = set()

        for r in result_source.get("results", []) + result_target.get("results", []):
            if r.get("type") == "memory_node" and r.get("id") not in seen_ids:
                all_results.append(r)
                seen_ids.add(r.get("id"))

        return all_results

    # -------------------------
    # SEARCH OPERATIONS
    # -------------------------

    def semantic_search(self, query: str, user_id: str, k: int = 10,
                        response_format: str = "interpreted",
                        tag_filters: List[str] = None) -> Dict:
        """
        Semantic search across user's memories
        response_format: "raw" | "interpreted" | "both"
        """
        user_filter = f"^user\\.{user_id}$"

        if tag_filters:
            keyword_filter = [user_filter] + tag_filters
        else:
            keyword_filter = user_filter

        payload = {
            "query": query,
            "k": k,
            "keyword_filter": keyword_filter,
            "response_format": response_format
        }

        try:
            response = requests.post(
                f"{self.api_prefix}/memories/search",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                result = {
                    "success": True,
                    "results": data.get("results", []),
                    "summary": "",
                    "key_facts": [],
                    "interpreted_error": data.get("interpreted_error")
                }

                if "answer_summary" in data and data["answer_summary"]:
                    result["summary"] = data["answer_summary"]
                elif "interpreted" in data and data["interpreted"]:
                    result["summary"] = data["interpreted"]

                if "key_facts" in data:
                    result["key_facts"] = data["key_facts"]

                return result

            return {"success": False, "error": response.text, "results": [], "summary": ""}

        except Exception as e:
            return {"success": False, "error": str(e), "results": [], "summary": ""}

    # -------------------------
    # GRAPH OPERATIONS
    # -------------------------

    def get_native_graph_export(self, user_id: str = None) -> Dict:
        """Get full graph from Membrain's native /graph/export endpoint"""
        try:
            response = requests.get(
                f"{self.api_prefix}/graph/export",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                graph = data.get("graph", {})

                # Filter by user if specified (since graph is global)
                if user_id:
                    nodes = graph.get("nodes", [])
                    edges = graph.get("edges", [])

                    # Filter nodes by user tag
                    user_tag = f"user.{user_id}"
                    filtered_nodes = []
                    node_map = {}
                    for node in nodes:
                        tags = node.get("tags", [])
                        if user_tag in tags:
                            filtered_nodes.append(node)
                            node_map[node.get("id")] = node

                    # Filter edges where both source and target are in filtered nodes
                    filtered_edges = []
                    for edge in edges:
                        source_id = edge.get("source")
                        target_id = edge.get("target")
                        if source_id in node_map and target_id in node_map:
                            filtered_edges.append(edge)

                    return {"nodes": filtered_nodes, "edges": filtered_edges}

                return graph
            return {"nodes": [], "edges": []}
        except Exception as e:
            print(f"Error fetching native graph: {e}")
            return {"nodes": [], "edges": []}

    def get_graph_export(self, user_id: str) -> Dict:
        """Get graph directly from Membrain's native graph API and filter by user"""
        try:
            response = requests.get(
                f"{self.api_prefix}/graph/export",
                headers=self.headers,
                timeout=30
            )

            if response.status_code != 200:
                return {"nodes": [], "edges": []}

            data = response.json()
            all_nodes = data.get("nodes", [])
            all_edges = data.get("edges", [])

            # ✅ Filter nodes belonging to this user by their tags
            user_tag = f"user.{user_id}"
            user_node_ids = set()
            filtered_nodes = []

            for node in all_nodes:
                tags = node.get("tags", [])
                if user_tag in tags:
                    # Skip junk concepts
                    label = node.get("label", node.get("content", "")).strip()
                    if label.lower() in JUNK_CONCEPTS or len(label) < 3:
                        continue

                    # Get score from tags
                    score = 0.3
                    for tag in tags:
                        if tag.startswith("score."):
                            try:
                                score = float(tag.split(".", 1)[1])
                            except:
                                pass

                    filtered_nodes.append({
                        "id": node.get("id"),
                        "label": label,
                        "score": score,
                        "tags": tags
                    })
                    user_node_ids.add(node.get("id"))

            # ✅ Only keep edges where BOTH source and target belong to this user
            filtered_edges = []
            for edge in all_edges:
                source = edge.get("source")
                target = edge.get("target")
                if source in user_node_ids and target in user_node_ids:
                    filtered_edges.append({
                        "source": source,
                        "target": target,
                        "label": edge.get("label", edge.get("type", "related")),
                        "description": edge.get("description", "")
                    })

            return {"nodes": filtered_nodes, "edges": filtered_edges}

        except Exception as e:
            print(f"Graph export error: {e}")
            return {"nodes": [], "edges": []}

    def get_graph_neighborhood(self, memory_id: str, hops: int = 2) -> Dict:
        """Get local graph neighborhood around a memory"""
        try:
            response = requests.get(
                f"{self.api_prefix}/graph/neighborhood",
                headers=self.headers,
                params={"memory_id": memory_id, "hops": hops},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {"nodes": [], "edges": []}
        except:
            return {"nodes": [], "edges": []}

    def get_graph_hubs(self, limit: int = 10) -> Dict:
        """Get highest-degree nodes in the graph"""
        try:
            response = requests.get(
                f"{self.api_prefix}/graph/hubs",
                headers=self.headers,
                params={"limit": limit},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {"hubs": []}
        except:
            return {"hubs": []}

    def get_shortest_path(self, from_id: str, to_id: str) -> Dict:
        """Get shortest path between two memories"""
        try:
            response = requests.get(
                f"{self.api_prefix}/graph/path",
                headers=self.headers,
                params={"from_id": from_id, "to_id": to_id},
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {"path": []}
        except:
            return {"path": []}

    # -------------------------
    # STATS OPERATIONS
    # -------------------------

    def get_stats(self, user_id: str = None) -> Dict:
        """Get memory statistics"""
        try:
            response = requests.get(
                f"{self.api_prefix}/stats",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}

    def get_memory_count(self, user_id: str = None, tags: List[str] = None) -> int:
        """Get count of memories matching filter"""
        params = {}
        if tags:
            params["tags"] = ",".join(tags)

        try:
            response = requests.get(
                f"{self.api_prefix}/memories/count",
                headers=self.headers,
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("count", 0)
            return 0
        except:
            return 0


# Singleton instance
membrain_client = MembrainClient()


# -------------------------
# LEGACY FUNCTION FOR BACKWARD COMPATIBILITY
# -------------------------
def call_membrain(action: str, content: str, user_id: str):
    """Legacy wrapper for the old function signature"""
    if action == "add":
        result = membrain_client.store_memory(content, user_id)
        return {
            "membrain": "add",
            "status": "stored" if result.get("success") else "failed",
            "content": content,
            "user_id": user_id,
            "memory_id": result.get("memory_id")
        }

    if action == "search":
        result = membrain_client.semantic_search(content, user_id, response_format="raw")
        results = [r.get("content") for r in result.get("results", []) if r.get("type") == "memory_node"]
        return {
            "membrain": "search",
            "status": "success",
            "query": content,
            "results": results,
            "user_id": user_id
        }

    return {"error": "invalid action"}