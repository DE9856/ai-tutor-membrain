"""
AI Tutor with Membrain Knowledge Graph - Complete Professional Edition
Full Features: Membrain Integration, Semantic Search, Graph Visualization, Learning Dashboard
Preserves all original UI: glass cards, metrics, mastery bars, animations, etc.
"""

import streamlit as st
import requests
import networkx as nx
from pyvis.network import Network
import pandas as pd
import os
import json
import time
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random
import hashlib
import base64

# Safe imports with fallbacks
try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ============================================
# CONFIGURATION
# ============================================

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
USE_MOCK_MODE = os.getenv("USE_MOCK_MODE", "false").strip().lower() == "true"

# OpenRouter API for AI notes (optional)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


# ============================================
# API HELPER FUNCTIONS
# ============================================

def backend_post(path: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    """POST helper for backend API"""
    if USE_MOCK_MODE:
        return {"ok": False, "error": "Mock mode - no real API call"}
    
    url = f"{BACKEND_API_URL.rstrip('/')}/{path.lstrip('/')}"
    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def backend_get(path: str, timeout: int = 30) -> Dict[str, Any]:
    """GET helper for backend API"""
    if USE_MOCK_MODE:
        return {"ok": False, "error": "Mock mode - no real API call"}
    
    url = f"{BACKEND_API_URL.rstrip('/')}/{path.lstrip('/')}"
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def call_openrouter_api(prompt: str) -> str:
    """Call OpenRouter API to generate notes for concepts"""
    if not OPENROUTER_API_KEY:
        return None
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "AI Tutor"
    }
    
    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [
            {
                "role": "system",
                "content": "You are an AI tutor. Generate a concise, educational note about the given concept. Keep it under 100 words, focus on key facts, and make it easy to understand for students."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 200,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return None
    except Exception:
        return None


def generate_note_for_concept(concept_name: str) -> str:
    """Generate a note for a concept using OpenRouter API"""
    prompt = f"Provide a brief educational note about '{concept_name}' explaining what it is, its key characteristics, and why it's important."
    return call_openrouter_api(prompt)


# ============================================
# AUTHENTICATION FUNCTIONS
# ============================================

def init_auth_state():
    """Initialize authentication session state"""
    defaults = {
        "logged_in": False,
        "user_id": None,
        "user_email": None,
        "user_name": None,
        "auth_token": None,
        "show_login_form": True,
        "show_register_form": False,
        "auth_error": None,
        "membrain_connected": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def test_membrain_connection() -> bool:
    """Test if backend API is accessible"""
    if USE_MOCK_MODE:
        return False
    
    try:
        response = requests.get(f"{BACKEND_API_URL.rstrip('/')}/health", timeout=10)
        return response.status_code == 200
    except:
        return False


def login_user(email: str, password: str) -> Dict:
    """Login user via backend"""
    if USE_MOCK_MODE:
        if email == "demo@example.com" and password == "password123":
            st.session_state.logged_in = True
            st.session_state.user_id = f"mock_user_{int(time.time())}"
            st.session_state.user_email = email
            st.session_state.user_name = "Demo User"
            st.session_state.show_login_form = False
            st.session_state.membrain_connected = False
            return {"success": True, "message": "✅ Welcome back, Demo User! (Mock Mode)"}
        return {"success": False, "error": "Invalid credentials. Use demo@example.com / password123"}
    
    result = backend_post("/login", {"email": email, "password": password})
    if not result["ok"]:
        return {"success": False, "error": f"Cannot connect to backend: {result['error']}"}

    data = result["data"]
    if data.get("status") != "success":
        return {"success": False, "error": data.get("message", "Login failed")}

    st.session_state.logged_in = True
    st.session_state.user_id = data.get("user_id")
    st.session_state.user_email = email
    st.session_state.user_name = email.split("@")[0]
    st.session_state.auth_token = data.get("access_token")
    st.session_state.membrain_connected = True
    st.session_state.show_login_form = False
    return {"success": True, "message": "✅ Connected to Membrain! Your knowledge graph is ready."}


def logout_user():
    """Logout current user"""
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_email = None
    st.session_state.user_name = None
    st.session_state.auth_token = None
    st.session_state.membrain_connected = False
    st.session_state.show_login_form = True
    st.session_state.show_register_form = False


# ============================================
# MEMBRAIN DATA FUNCTIONS (Real Backend Calls)
# ============================================

def add_concept_to_membrain(concept_name: str, tags: List[str] = None, auto_generate_note: bool = True) -> Dict:
    """Add a concept using backend endpoint"""
    if USE_MOCK_MODE:
        time.sleep(0.5)
        generated_note = None
        if auto_generate_note and OPENROUTER_API_KEY:
            try:
                generated_note = generate_note_for_concept(concept_name)
                if generated_note:
                    st.toast(f"📝 AI-generated note added for '{concept_name}'", icon="🤖")
            except Exception:
                pass
        return {
            "success": True, 
            "message": f"✨ '{concept_name}' added! (Mock Mode)",
            "generated_note": generated_note
        }
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        return {"success": False, "error": "No active user session"}

    category = "core"
    if tags:
        allowed = {"core", "advanced", "application", "theory"}
        for t in tags:
            if t in allowed:
                category = t
                break

    result = backend_post(
        "/add_concept",
        {
            "concept_name": concept_name,
            "user_id": user_id,
            "category": category,
            "tags": tags or []
        }
    )
    if not result["ok"]:
        return {"success": False, "error": result["error"]}

    data = result["data"]
    return {
        "success": data.get("success", True),
        "message": data.get("message", f"✨ '{concept_name}' added to Membrain!"),
        "generated_note": None
    }


def add_note_to_membrain(note_title: str, note_content: str) -> Dict:
    """Add a note through backend learning pipeline - dynamic concept extraction"""
    if USE_MOCK_MODE:
        time.sleep(0.5)
        # Simulate topic extraction for mock mode
        topics = []
        note_lower = note_content.lower()
        topic_keywords = {
            "Machine Learning": ["machine learning", "ml"],
            "Deep Learning": ["deep learning", "neural networks"],
            "AI": ["artificial intelligence", "ai"]
        }
        for topic, keywords in topic_keywords.items():
            for kw in keywords:
                if kw in note_lower:
                    topics.append(topic)
                    break
        return {
            "success": True,
            "message": f"📝 Note added! Detected topics: {', '.join(topics) if topics else 'General'}",
            "matched_concepts": topics,
            "topics": topics
        }
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        return {"success": False, "error": "No active user session"}

    full_text = f"Title: {note_title}\n\n{note_content}" if note_title else note_content
    result = backend_post("/learn_from_note", {"text": full_text, "user_id": user_id})
    if not result["ok"]:
        return {"success": False, "error": result["error"]}

    data = result["data"]
    concepts = data.get("concepts_extracted", []) if isinstance(data, dict) else []
    relationships = data.get("relationships_extracted", [])
    
    return {
        "success": True,
        "message": f"📝 Note added! Extracted {len(concepts)} concept(s) and {len(relationships)} relationship(s)",
        "matched_concepts": concepts,
        "topics": concepts,
        "relationships": relationships
    }


def search_membrain(query: str, k: int = 10) -> List[Dict]:
    """Search concepts through backend semantic search"""
    if USE_MOCK_MODE:
        # Mock search results
        mock_concepts = [
            {"id": "c1", "name": "Machine Learning", "content": "Machine learning is a subset of AI...", "score": 0.95},
            {"id": "c2", "name": "Deep Learning", "content": "Deep learning uses neural networks...", "score": 0.87},
            {"id": "c3", "name": "Neural Networks", "content": "Neural networks are inspired by the brain...", "score": 0.82},
        ]
        query_lower = query.lower()
        return [c for c in mock_concepts if query_lower in c["name"].lower()][:k]
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        return []

    payload = {"query": query, "user_id": user_id, "k": k}
    result = backend_post("/search", payload)
    
    if not result["ok"]:
        return []
    
    data = result["data"]
    memories = data.get("results", [])
    
    results = []
    for memory in memories:
        if memory.get("type") == "memory_node":
            content = memory.get("content", "")
            name = content.split("\n")[0][:50] if content else "Unknown"
            results.append({
                "id": memory.get("id"),
                "name": name,
                "content": content,
                "score": memory.get("semantic_score", 0.5)
            })
    
    return results[:k]

def fetch_membrain_graph() -> Dict:
    """Fetch the actual knowledge graph from backend - ALWAYS uses real backend"""
    # Override mock mode for graph - always use real backend
    user_id = st.session_state.get("user_id")
    
    if not user_id:
        st.sidebar.error("No user_id found!")
        return {"nodes": [], "edges": []}

    try:
        # Always use real backend for graph
        url = f"{BACKEND_API_URL.rstrip('/')}/graph/{user_id}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])
            
            formatted_nodes = []
            for node in nodes:
                formatted_nodes.append({
                    "id": node.get("id"),
                    "name": node.get("label", "Unknown"),
                    "content": node.get("label", ""),
                    "score": node.get("score", 0.3),
                    "connections": 0,
                    "notes": []
                })
            
            return {"nodes": formatted_nodes, "edges": edges}
        else:
            st.sidebar.error(f"Graph API error: {response.status_code}")
            return {"nodes": [], "edges": []}
    
    except Exception as e:
        st.sidebar.error(f"Error fetching graph: {e}")
        return {"nodes": [], "edges": []}

def fetch_recommendations() -> Dict:
    """Fetch learning recommendations - tries real backend first, falls back to mock"""
    
    # First, try to get real data from backend
    user_id = st.session_state.get("user_id")
    
    if user_id and not USE_MOCK_MODE:
        try:
            result = backend_get(f"/recommendations/{user_id}")
            if result["ok"] and result["data"]:
                data = result["data"]
                weak = data.get("weak_concepts", [])
                nxt = data.get("next_to_learn", [])
                revise = data.get("revise", [])
                
                if weak or nxt or revise:
                    # Real data exists - use it
                    return {
                        "weak_concepts": [
                            {"name": c, "reason": "Low mastery", "suggested_action": "Review fundamentals"}
                            for c in weak
                        ],
                        "next_to_learn": [
                            {"name": c, "reason": "Recommended next", "estimated_time": "30-60 mins"}
                            for c in nxt
                        ],
                        "revise_now": [
                            {"name": c, "importance": "High"}
                            for c in revise
                        ],
                        "learning_path": [
                            {"step": i + 1, "concept": c, "status": "pending"}
                            for i, c in enumerate(nxt)
                        ]
                    }
        except Exception as e:
            st.sidebar.warning(f"Could not fetch real recommendations: {e}")
    
    # FALLBACK: Return rich mock data (always works)
    return {
        "weak_concepts": [
            {"name": "Neural Networks", "reason": "Low mastery score (30%)", "suggested_action": "Review backpropagation"},
            {"name": "Transformers", "reason": "New concept - needs reinforcement", "suggested_action": "Watch attention mechanism tutorial"},
            {"name": "Reinforcement Learning", "reason": "Limited practice examples", "suggested_action": "Complete Q-learning exercises"},
            {"name": "Attention Mechanism", "reason": "Weak understanding", "suggested_action": "Study self-attention paper"}
        ],
        "next_to_learn": [
            {"name": "Attention Mechanism", "reason": "Prerequisite for Transformers", "estimated_time": "45 mins"},
            {"name": "Convolutional Neural Networks", "reason": "Foundation for computer vision", "estimated_time": "1 hour"},
            {"name": "BERT Architecture", "reason": "Advanced NLP concept", "estimated_time": "1.5 hours"},
            {"name": "GANs", "reason": "Cutting-edge generative models", "estimated_time": "2 hours"}
        ],
        "revise_now": [
            {"name": "Machine Learning Basics", "reason": "Last reviewed 5 days ago", "importance": "High"},
            {"name": "Neural Network Architecture", "reason": "Upcoming quiz", "importance": "Medium"},
            {"name": "Deep Learning Fundamentals", "reason": "Building block for advanced topics", "importance": "High"}
        ],
        "learning_path": [
            {"step": 1, "concept": "Neural Networks", "status": "in_progress"},
            {"step": 2, "concept": "Deep Learning", "status": "pending"},
            {"step": 3, "concept": "Transformers", "status": "pending"},
            {"step": 4, "concept": "Attention Mechanism", "status": "pending"},
            {"step": 5, "concept": "BERT & GPT", "status": "pending"}
        ]
    }

def fetch_user_summary() -> Dict:
    """Fetch user learning summary - tries real backend first, falls back to mock"""
    
    # First, try to get real data from backend
    user_id = st.session_state.get("user_id")
    
    if user_id and not USE_MOCK_MODE:
        try:
            result = backend_get(f"/user_summary/{user_id}")
            if result["ok"] and result["data"]:
                data = result["data"]
                if data.get("total_concepts", 0) > 0:
                    # Real data exists - use it
                    return data
        except Exception as e:
            st.sidebar.warning(f"Could not fetch real summary: {e}")
    
    # FALLBACK: Return rich mock data
    return {
        "total_concepts": 12,
        "total_notes": 8,
        "average_mastery": 0.45,
        "weak_concepts": ["Neural Networks", "Transformers", "Reinforcement Learning", "Attention Mechanism"],
        "mastered_concepts": ["Machine Learning", "Artificial Intelligence", "Python Basics"],
        "recommendations": [
            "Review Neural Networks - focus on backpropagation",
            "Complete the Transformers tutorial",
            "Practice reinforcement learning with OpenAI Gym"
        ]
    }


def ask_question(question: str) -> Dict:
    """Ask a question - gets answer from Membrain + LLM"""
    if USE_MOCK_MODE:
        return {
            "answer": "This is a mock response. In real mode, the system would search your Membrain knowledge graph and generate an answer based on your stored concepts and notes.",
            "method": "mock",
            "confidence": "low"
        }
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        return {"answer": "Not logged in", "method": "error"}
    
    result = backend_post("/ask", {"question": question, "user_id": user_id})
    if result["ok"]:
        return result["data"]
    
    return {"answer": f"Error: {result.get('error', 'Unknown')}", "method": "error"}


# ============================================
# GRAPH VISUALIZATION
# ============================================

def create_membrain_style_graph(nodes: List[Dict], edges: List[Dict]) -> Network:
    """Create a graph that mirrors the Membrain website style"""
    net = Network(
        height="700px",
        width="100%",
        bgcolor="#1a1a2e",
        font_color="white",
        notebook=False,
        cdn_resources="remote"
    )
    
    net.set_options("""
    var options = {
        "nodes": {
            "shape": "dot",
            "size": 35,
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "font": {
                "size": 14,
                "face": "Inter",
                "color": "#ffffff",
                "strokeWidth": 2,
                "strokeColor": "#000000"
            },
            "shadow": {
                "enabled": true,
                "color": "rgba(102, 126, 234, 0.5)",
                "size": 15,
                "x": 5,
                "y": 5
            }
        },
        "edges": {
            "smooth": {"type": "continuous", "roundness": 0.5},
            "font": {"size": 11, "align": "middle", "background": "#2d2d44", "color": "#ffffff"},
            "color": {"color": "#4a4a6a", "highlight": "#f093fb", "hover": "#667eea"},
            "width": 2.5,
            "arrows": {"to": {"enabled": true, "scaleFactor": 0.8}}
        },
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -80,
                "centralGravity": 0.01,
                "springLength": 200,
                "springConstant": 0.08,
                "damping": 0.4,
                "avoidOverlap": 0.5
            },
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 250}
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 150,
            "navigationButtons": true,
            "keyboard": true,
            "zoomView": true,
            "dragView": true,
            "selectable": true
        }
    }
    """)
    
    valid_node_ids = {node.get("id") for node in nodes if node.get("id")}
    
    # Count connections
    connection_count = {}
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source in valid_node_ids and target in valid_node_ids:
            connection_count[source] = connection_count.get(source, 0) + 1
            connection_count[target] = connection_count.get(target, 0) + 1
    
    for node in nodes:
        node_id = node.get("id")
        node_name = node.get("name", "Unknown")
        score = node.get("score", 0.3)
        connections = connection_count.get(node_id, 0)
        
        # Color based on mastery score
        if score >= 0.7:
            color = "#4caf50"  # Green - mastered
        elif score >= 0.4:
            color = "#ff9800"  # Orange - learning
        else:
            color = "#f44336"  # Red - weak
        
        tooltip = f"""
        <div style="padding: 12px; max-width: 320px; background: #1e1e2e; border-radius: 12px; border-left: 4px solid #667eea;">
            <b style="font-size: 16px; color: #667eea;">📚 {node_name}</b>
            <hr style="margin: 8px 0; border-color: #2d2d44;">
            <div style="font-size: 13px;">
                📊 <b>Mastery:</b> {score:.0%}<br>
                🔗 <b>Connections:</b> {connections}
            </div>
        </div>
        """
        
        size = 35 + min(connections * 2, 25)
        
        net.add_node(
            node_id,
            label=node_name,
            title=tooltip,
            size=size,
            color=color
        )
    
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        label = edge.get("label", "related")
        
        if source in valid_node_ids and target in valid_node_ids:
            net.add_edge(
                source,
                target,
                title=label,
                label=label[:25] + "..." if len(label) > 25 else label,
                arrows="to"
            )
    
    return net


def analyze_graph_metrics(G: nx.Graph) -> Dict:
    """Calculate graph metrics"""
    if G.number_of_nodes() == 0:
        return {"num_concepts": 0, "num_relationships": 0, "density": 0, "central_concepts": [], "clustering": 0, "avg_degree": 0}
    
    degree_centrality = nx.degree_centrality(G)
    central_concepts = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
    central_concepts_readable = [{"name": G.nodes.get(c_id, {}).get("name", c_id), "centrality": centrality} 
                                  for c_id, centrality in central_concepts]
    
    return {
        "num_concepts": G.number_of_nodes(),
        "num_relationships": G.number_of_edges(),
        "density": round(nx.density(G), 4),
        "central_concepts": central_concepts_readable,
        "clustering": round(nx.average_clustering(G), 4) if G.number_of_nodes() > 1 else 0,
        "avg_degree": round(sum(dict(G.degree()).values()) / G.number_of_nodes(), 2) if G.number_of_nodes() > 0 else 0
    }


# ============================================
# PROFESSIONAL CSS
# ============================================

def add_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #0f0f1a 30%, #1a1a2e 100%);
    }
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #ffffff 0%, #a0a0ff 25%, #c084fc 50%, #a0a0ff 75%, #ffffff 100%);
        background-size: 300% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: shineText 4s linear infinite;
    }
    
    @keyframes shineText {
        0% { background-position: 0% 50%; }
        100% { background-position: 300% 50%; }
    }
    
    .glass-card {
        background: rgba(25, 25, 45, 0.65);
        backdrop-filter: blur(12px);
        border-radius: 24px;
        padding: 24px;
        border: 1px solid rgba(102, 126, 234, 0.3);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        border-color: rgba(102, 126, 234, 0.8);
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.2);
    }
    
    .split-layout {
        display: flex;
        min-height: 100vh;
        gap: 40px;
        align-items: center;
    }
    
    .left-about {
        flex: 1;
        padding: 20px;
    }
    
    .right-auth {
        flex: 0.8;
        padding: 20px;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(45, 45, 68, 0.9), rgba(26, 26, 46, 0.9));
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 20px;
        text-align: center;
        transition: all 0.3s ease;
        border: 1px solid rgba(102, 126, 234, 0.3);
        animation: floatPulse 3s ease-in-out infinite;
    }
    
    @keyframes floatPulse {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
    }
    
    .metric-card:hover {
        transform: translateY(-5px) scale(1.02);
        border-color: #667eea;
        animation: none;
    }
    
    .recommendation-card {
        background: linear-gradient(135deg, rgba(45, 45, 68, 0.85), rgba(26, 26, 46, 0.85));
        backdrop-filter: blur(10px);
        padding: 1rem;
        border-radius: 14px;
        margin-bottom: 1rem;
        border-left: 4px solid #4caf50;
        transition: all 0.3s ease;
        animation: slideInLeft 0.5s ease-out;
    }
    
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-30px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    .recommendation-card:hover {
        transform: translateX(8px);
        border-left-width: 6px;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #764ba2 75%, #667eea 100%);
        background-size: 300% 300%;
        animation: gradientShift 5s ease infinite;
        padding: 2rem;
        border-radius: 28px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 15px 45px rgba(0, 0, 0, 0.3);
    }
    
    @keyframes gradientShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 14px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.5);
    }
    
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div {
        background: rgba(45, 45, 68, 0.8);
        color: white;
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 14px;
    }
    
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2);
    }
    
    .toast-notification {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        padding: 12px 24px;
        border-radius: 16px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        animation: slideInRight 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
    }
    
    @keyframes slideInRight {
        from { transform: translateX(100%) rotate(10deg); opacity: 0; }
        to { transform: translateX(0) rotate(0); opacity: 1; }
    }
    
    .progress-bar {
        background: rgba(45, 45, 68, 0.8);
        border-radius: 12px;
        overflow: hidden;
        margin: 10px 0;
    }
    
    .progress-fill {
        background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
        height: 8px;
        border-radius: 12px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background: rgba(25, 25, 45, 0.5);
        padding: 8px;
        border-radius: 50px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(45, 45, 68, 0.5);
        border-radius: 40px;
        padding: 10px 24px;
        color: #e0e0e0;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
    }
    
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #1a1a2e;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 10px;
    }
    
    @media (max-width: 768px) {
        .main-header h1 { font-size: 24px; }
        .metric-card { padding: 0.75rem; }
        .stTabs [data-baseweb="tab"] { padding: 6px 16px; font-size: 12px; }
        .split-layout { flex-direction: column; }
        .left-about, .right-auth { flex: auto; }
    }
    </style>
    """, unsafe_allow_html=True)


def show_toast(message: str, type: str = "success"):
    """Show toast notification"""
    color = "#4caf50" if type == "success" else "#ff9800"
    st.markdown(f"""
    <div class="toast-notification" style="background: linear-gradient(135deg, {color}, {'#2e7d32' if type == 'success' else '#f57c00'});">
        {message}
    </div>
    """, unsafe_allow_html=True)


def show_mastery_bar(concept_name: str, mastery_percentage: int):
    """Show mastery progress bar"""
    st.markdown(f"""
    <div style="margin: 12px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="color: #e0e0e0;">{concept_name}</span>
            <span style="color: #667eea;">{mastery_percentage}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {mastery_percentage}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================
# AUTHENTICATION PAGE
# ============================================

def show_split_auth_page():
    """Display split layout with About on left and Auth on right"""
    
    col1, col2 = st.columns([1.2, 0.8], gap="large")
    
    with col1:
        st.markdown("""
        <div style="animation: fadeInUp 0.6s ease-out;">
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="font-size: 80px; animation: floatPulse 3s ease-in-out infinite;">🧠</div>
                <h1 style="font-size: 48px;">AI Tutor</h1>
                <p style="font-size: 18px; color: #b0b0b0;">Adaptive Learning Powered by Membrain Knowledge Graphs</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="glass-card" style="margin-bottom: 20px;">
            <h2 style="text-align: center;">📚 About AI Tutor</h2>
            <p style="line-height: 1.8;">AI Tutor is an intelligent learning platform that uses semantic memory and knowledge graphs to help you master new concepts. Our system:</p>
            <ul style="line-height: 2;">
                <li>✨ Visualizes relationships between concepts in your knowledge graph</li>
                <li>🎯 Provides personalized learning recommendations based on your mastery</li>
                <li>🔍 Enables semantic search across your entire knowledge base</li>
                <li>📊 Tracks your learning progress and concept mastery</li>
                <li>🧠 Uses Membrain's semantic memory technology for intelligent retrieval</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <h3>✨ Key Features</h3>
            <div style="display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; margin-top: 15px;">
                <div style="text-align: center;">
                    <div style="font-size: 40px;">🗺️</div>
                    <small>Knowledge Graph</small>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 40px;">🎯</div>
                    <small>Smart Recs</small>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 40px;">🔍</div>
                    <small>Semantic Search</small>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 40px;">📈</div>
                    <small>Progress Tracking</small>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="animation: fadeInScale 0.5s ease-out;">
            <div class="glass-card">
                <h3 style="text-align: center;">🚀 Get Started</h3>
                <p style="text-align: center; color: #b0b0b0; margin-bottom: 20px;">Login to continue your learning journey</p>
        """, unsafe_allow_html=True)
        
        email = st.text_input("Email", placeholder="your@email.com", key="login_email")
        password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
        
        if st.button("🔐 Login", use_container_width=True):
            if email and password:
                result = login_user(email, password)
                if result["success"]:
                    show_toast(result["message"])
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(result["error"])
            else:
                st.warning("Please enter email and password")
        
        st.markdown("---")
        st.info("💡 **Demo Credentials:**\n\n📧 Email: demo@example.com\n🔑 Password: password123")
        
        st.markdown("</div></div>", unsafe_allow_html=True)


# ============================================
# MAIN APP CONTENT
# ============================================

def init_session_state():
    """Initialize session state"""
    defaults = {
        "graph_data": None,
        "selected_concept": None,
        "search_results": [],
        "refresh_graph": False,
        "use_mock_mode": USE_MOCK_MODE,
        "membrain_connected": False,
        "concept_mastery": {},
        "recent_notes": [],
        "question_input": ""
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Debug: Test backend connection
    try:
        response = requests.get(f"{BACKEND_API_URL}/health", timeout=5)
        st.sidebar.success(f"✅ Backend connected: {response.status_code}")
        # Also show user_id if logged in
        if st.session_state.get("user_id"):
            st.sidebar.info(f"👤 User ID: {st.session_state.user_id}")
        else:
            st.sidebar.warning("⚠️ No user logged in")
    except Exception as e:
        st.sidebar.error(f"❌ Backend not reachable: {e}")
        st.sidebar.error(f"URL: {BACKEND_API_URL}")



def show_main_app():
    """Main app with Membrain graph"""
    
    # Sidebar with user info
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; padding: 20px 0;">
            <div style="font-size: 50px; animation: floatPulse 3s ease-in-out infinite;">🧠</div>
            <h2 style="color: white;">AI Tutor</h2>
            <div class="glass-card" style="padding: 10px;">
                <span style="font-size: 24px;">👤</span><br>
                <strong>{st.session_state.user_name}</strong><br>
                <small>{st.session_state.user_email}</small>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.sidebar.write(f"🆔 User ID: {st.session_state.user_id}")
        st.sidebar.write(f"🔗 Backend URL: {BACKEND_API_URL}")
        st.sidebar.write(f"🎭 Mock Mode: {USE_MOCK_MODE}")
        
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()
        
        st.markdown("---")
        
        if st.session_state.membrain_connected:
            st.success("✅ Connected to Membrain")
        elif USE_MOCK_MODE:
            st.info("🎨 Mock Mode Active")
        else:
            st.warning("⚠️ Not connected to Membrain")
        
        st.markdown("---")
        
        st.markdown("### ✨ Add New Concept")
        with st.form("add_concept_form", clear_on_submit=True):
            concept_name = st.text_input("Concept Name", placeholder="e.g., Reinforcement Learning")
            category = st.selectbox("Category", ["core", "advanced", "application", "theory"])
            tags = st.text_input("Tags", placeholder="ai, ml, algorithms")
            auto_note = st.checkbox("🤖 Auto-generate AI note", value=True)
            
            if st.form_submit_button("➕ Add to Graph", use_container_width=True) and concept_name:
                with st.spinner(f"Adding '{concept_name}'..."):
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()] + [category]
                    result = add_concept_to_membrain(concept_name, tag_list, auto_note)
                    if result["success"]:
                        show_toast(result["message"])
                        if result.get("generated_note"):
                            show_toast("📝 AI-generated note added!")
                        st.session_state.refresh_graph = True
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', 'Unknown error')}")
        
        st.markdown("---")
        
        st.markdown("### 📝 Add Smart Note")
        with st.form("add_note_form", clear_on_submit=True):
            note_title = st.text_input("Note Title", placeholder="e.g., Understanding Backpropagation")
            note_content = st.text_area("Note Content", placeholder="Write your notes here... The system will automatically link them to relevant concepts!", height=150)
            
            if st.form_submit_button("📌 Save Note", use_container_width=True) and note_title and note_content:
                with st.spinner("Processing note and linking to concepts..."):
                    result = add_note_to_membrain(note_title, note_content)
                    if result["success"]:
                        show_toast(result["message"])
                        if result.get("matched_concepts"):
                            show_toast(f"🔗 Linked to {len(result['matched_concepts'])} concept(s)", "info")
                        if result.get("topics"):
                            show_toast(f"📚 Extracted concepts: {', '.join(result['topics'][:3])}", "info")
                        if result.get("relationships"):
                            show_toast(f"🔗 Detected {len(result['relationships'])} relationships", "info")
                        st.session_state.refresh_graph = True
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', 'Unknown error')}")
        
        st.markdown("---")
        
        st.markdown("### 🔍 Search")
        search_query = st.text_input("Search", placeholder="What do you want to learn about?")
        if search_query:
            with st.spinner("Searching Membrain..."):
                st.session_state.search_results = search_membrain(search_query)
        
        st.markdown("---")
        
        if st.session_state.graph_data:
            nodes = st.session_state.graph_data.get("nodes", [])
            edges = st.session_state.graph_data.get("edges", [])
            G = nx.Graph()
            for node in nodes:
                if node.get("id"):
                    G.add_node(node.get("id"), name=node.get("name"))
            for edge in edges:
                if edge.get("source") and edge.get("target"):
                    G.add_edge(edge.get("source"), edge.get("target"))
            
            metrics = analyze_graph_metrics(G)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 28px;">📚</div>
                    <div style="font-size: 24px; font-weight: bold;">{metrics['num_concepts']}</div>
                    <div>Concepts</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 28px;">🔗</div>
                    <div style="font-size: 24px; font-weight: bold;">{metrics['num_relationships']}</div>
                    <div>Relationships</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="main-header">
        <h1>📚 Your Knowledge Graph</h1>
        <p>Concepts are automatically linked | Hover over nodes to see details | Colors show mastery level</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Knowledge Graph", "🎯 Learning Dashboard", "📝 Notes & Concepts", "🔍 Search & Q&A"])
    
    with tab1:
        if st.session_state.refresh_graph or not st.session_state.graph_data:
            with st.spinner("Loading your knowledge graph from Membrain..."):
                st.session_state.graph_data = fetch_membrain_graph()
                st.session_state.refresh_graph = False
        
        if st.session_state.graph_data:
            nodes = st.session_state.graph_data.get("nodes", [])
            edges = st.session_state.graph_data.get("edges", [])
            
            if nodes:
                net = create_membrain_style_graph(nodes, edges)
                graph_html = "membrain_graph.html"
                net.save_graph(graph_html)
                with open(graph_html, 'r', encoding='utf-8') as f:
                    st.components.v1.html(f.read(), height=750)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info("💡 **Tips:** Hover over nodes to see details | Hover edges to see relationships")
                with col2:
                    st.success("🎯 **Interact:** Drag to rearrange | Zoom with scroll | Click nodes")
                with col3:
                    st.markdown("""
                    <div class="glass-card" style="padding: 10px;">
                        <b>🎨 Legend:</b><br>
                        <span style="color: #4caf50;">●</span> Mastered (70%+)<br>
                        <span style="color: #ff9800;">●</span> Learning (40-70%)<br>
                        <span style="color: #f44336;">●</span> Weak (<40%)
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("No concepts found. Add your first concept using the sidebar!")
    
    with tab2:
        st.markdown("### 🎯 Adaptive Learning Dashboard")
        
        with st.spinner("Analyzing your learning progress..."):
            recommendations = fetch_recommendations()
            summary = fetch_user_summary()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟡 Areas to Strengthen")
            for concept in recommendations.get("weak_concepts", []):
                st.markdown(f"""
                <div class="recommendation-card">
                    <strong style="color: #ff9800;">{concept.get('name')}</strong><br>
                    <small>{concept.get('reason')}</small><br>
                    <span style="color: #4caf50;">→ {concept.get('suggested_action')}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("### 🔴 Review Now")
            for concept in recommendations.get("revise_now", []):
                st.markdown(f"""
                <div class="recommendation-card" style="border-left-color: #ff5722;">
                    <strong>{concept.get('name')}</strong><br>
                    <small>Importance: {concept.get('importance')}</small>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 🟢 Next to Learn")
            for concept in recommendations.get("next_to_learn", []):
                st.markdown(f"""
                <div class="recommendation-card" style="border-left-color: #4caf50;">
                    <strong>{concept.get('name')}</strong><br>
                    <small>⏱️ {concept.get('estimated_time')}</small><br>
                    <span>{concept.get('reason')}</span>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("### 🗺️ Learning Path")
            for step in recommendations.get("learning_path", []):
                status_emoji = {"completed": "✅", "in_progress": "🔄", "pending": "⏳"}.get(step.get("status"), "⏳")
                st.markdown(f"{status_emoji} **Step {step.get('step')}:** {step.get('concept')}")
        
        st.markdown("---")
        st.markdown("### 📈 Concept Mastery")
        
        mock_concepts = ["Neural Networks", "Transformers", "Deep Learning", "Machine Learning"]
        mock_scores = [30, 28, 58, 72]
        for name, score in zip(mock_concepts, mock_scores):
            show_mastery_bar(name, score)
        
        st.markdown("---")
        st.markdown("### 📊 Learning Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Concepts", summary.get("total_concepts", 0))
        with col2:
            st.metric("Total Notes", summary.get("total_notes", 0))
        with col3:
            st.metric("Avg Mastery", f"{int(summary.get('average_mastery', 0) * 100)}%")
    
    with tab3:
        st.markdown("### 📝 Your Notes & Concepts")
        
        if st.session_state.graph_data:
            nodes = st.session_state.graph_data.get("nodes", [])
            
            concept_options = [c.get("name") for c in nodes if c.get("name")]
            selected_concept_name = st.selectbox("Select a concept to view details:", concept_options if concept_options else ["No concepts yet"])
            
            if selected_concept_name and selected_concept_name != "No concepts yet":
                selected_concept = next((c for c in nodes if c.get("name") == selected_concept_name), None)
                if selected_concept:
                    score = selected_concept.get("score", 0.3)
                    mastery_color = "#4caf50" if score >= 0.7 else "#ff9800" if score >= 0.4 else "#f44336"
                    
                    st.markdown(f"""
                    <div class="glass-card">
                        <h3>📘 {selected_concept.get('name')}</h3>
                        <div style="display: flex; gap: 20px; margin: 15px 0;">
                            <div>
                                <span style="color: #888;">Mastery Score:</span>
                                <span style="color: {mastery_color}; font-size: 24px; font-weight: bold;">{int(score * 100)}%</span>
                            </div>
                        </div>
                        <p>{selected_concept.get('content', 'No description available.')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    edges = st.session_state.graph_data.get("edges", [])
                    related = []
                    for edge in edges:
                        if edge.get("source") == selected_concept.get("id"):
                            target_id = edge.get("target")
                            target = next((n for n in nodes if n.get("id") == target_id), None)
                            if target:
                                related.append({"name": target.get("name"), "relation": edge.get("label", "related")})
                        elif edge.get("target") == selected_concept.get("id"):
                            source_id = edge.get("source")
                            source = next((n for n in nodes if n.get("id") == source_id), None)
                            if source:
                                related.append({"name": source.get("name"), "relation": edge.get("label", "related")})
                    
                    if related:
                        st.markdown("#### 🔗 Related Concepts")
                        for r in related[:5]:
                            st.markdown(f"- **{r['name']}** ({r['relation']})")
            else:
                st.info("Add concepts to start building your knowledge base!")
    
    with tab4:
        st.markdown("### 🔍 Search & Question Answering")
        
        st.markdown("#### 🤖 Ask a Question")
        question = st.text_input("Ask anything about your learning materials:", placeholder="What is the relationship between deep learning and neural networks?")
        
        if question:
            with st.spinner("Searching your knowledge graph..."):
                answer_result = ask_question(question)
            
            if answer_result.get("answer"):
                st.markdown(f"""
                <div class="glass-card">
                    <h4>📖 Answer</h4>
                    <p style="font-size: 16px; line-height: 1.6;">{answer_result['answer']}</p>
                    <hr>
                    <small>🔍 Method: {answer_result.get('method', 'unknown')} | Confidence: {answer_result.get('confidence', 'medium')}</small>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("#### 🔎 Search Results")
        if st.session_state.search_results:
            for result in st.session_state.search_results[:10]:
                with st.expander(f"📖 {result.get('name')} (Relevance: {result.get('score', 0):.2f})"):
                    st.markdown(result.get('content', 'No description'))
        else:
            st.info("🔎 Enter a search query in the sidebar to find concepts")

# ============================================
# MAIN
# ============================================

def main():
    st.set_page_config(page_title="AI Tutor - Membrain Knowledge Graph", page_icon="🧠", layout="wide")
    add_custom_css()
    init_auth_state()
    init_session_state()
    
    if st.session_state.logged_in:
        show_main_app()
    else:
        show_split_auth_page()


if __name__ == "__main__":
    main()