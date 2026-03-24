"""
AI Tutor with Membrain Knowledge Graph - Professional Edition
Enhanced with Split Layout Login/Register Page
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


def backend_post(path: str, payload: Dict[str, Any], timeout: int = 20) -> Dict[str, Any]:
    """POST helper for backend API with consistent error shape."""
    url = f"{BACKEND_API_URL.rstrip('/')}/{path.lstrip('/')}"
    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}


def backend_get(path: str, timeout: int = 20) -> Dict[str, Any]:
    """GET helper for backend API with consistent error shape."""
    url = f"{BACKEND_API_URL.rstrip('/')}/{path.lstrip('/')}"
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)}

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
        "show_login_form": False,
        "show_register_form": False,
        "auth_error": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def register_user(email: str, password: str, name: str) -> Dict:
    """Register a new user via backend."""
    if USE_MOCK_MODE:
        if email and password and name:
            st.session_state.logged_in = True
            st.session_state.user_id = f"mock_user_{int(time.time())}"
            st.session_state.user_email = email
            st.session_state.user_name = name
            return {"success": True, "message": "✅ Registration successful (Mock Mode)!"}
        return {"success": False, "error": "Missing fields"}

    result = backend_post("/signup", {"email": email, "password": password})
    if not result["ok"]:
        return {"success": False, "error": f"Backend unavailable: {result['error']}"}

    payload = result["data"]
    if payload.get("status") == "success":
        st.session_state.logged_in = True
        st.session_state.user_id = payload.get("user_id")
        st.session_state.user_email = email
        st.session_state.user_name = name or email.split("@")[0]
        st.session_state.auth_token = payload.get("access_token")
        st.session_state.show_login_form = False
        st.session_state.show_register_form = False
        return {"success": True, "message": "✅ Registration successful! Welcome to AI Tutor!"}

    return {"success": False, "error": payload.get("message", "Registration failed")}

def login_user(email: str, password: str) -> Dict:
    """Login existing user via backend."""
    if USE_MOCK_MODE:
        # Mock mode - only allow demo credentials
        if email == "demo@example.com" and password == "password123":
            st.session_state.logged_in = True
            st.session_state.user_id = f"mock_user_{int(time.time())}"
            st.session_state.user_email = email
            st.session_state.user_name = "Demo User"
            st.session_state.show_login_form = False
            st.session_state.show_register_form = False
            return {"success": True, "message": "✅ Welcome back, Demo User!"}
        elif email and password:
            return {"success": False, "error": "Invalid credentials. Use demo@example.com / password123"}
        return {"success": False, "error": "Please enter email and password"}

    result = backend_post("/login", {"email": email, "password": password})
    if not result["ok"]:
        return {"success": False, "error": f"Backend unavailable: {result['error']}"}

    payload = result["data"]
    if payload.get("status") == "success":
        user_name = email.split("@")[0]
        st.session_state.logged_in = True
        st.session_state.user_id = payload.get("user_id")
        st.session_state.user_email = email
        st.session_state.user_name = user_name
        st.session_state.auth_token = payload.get("access_token")
        st.session_state.show_login_form = False
        st.session_state.show_register_form = False
        return {"success": True, "message": f"✅ Welcome back, {user_name}!"}

    return {"success": False, "error": payload.get("message", "Invalid email or password")}

def logout_user():
    """Logout current user"""
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_email = None
    st.session_state.user_name = None
    st.session_state.auth_token = None
    st.session_state.show_login_form = False
    st.session_state.show_register_form = False

# ============================================
# MOCK DATA
# ============================================

MOCK_CONCEPTS = [
    {"id": "c1", "name": "Artificial Intelligence", "category": "core", "difficulty": "beginner", "content": "AI is the simulation of human intelligence in machines. It encompasses various subfields including machine learning, computer vision, and natural language processing.", "connections": 5, "notes": []},
    {"id": "c2", "name": "Machine Learning", "category": "core", "difficulty": "intermediate", "content": "Machine Learning enables systems to learn from data without explicit programming. It uses algorithms that improve through experience.", "connections": 8, "notes": []},
    {"id": "c3", "name": "Deep Learning", "category": "advanced", "difficulty": "advanced", "content": "Deep Learning uses neural networks with multiple layers to learn hierarchical representations of data.", "connections": 6, "notes": []},
    {"id": "c4", "name": "Neural Networks", "category": "advanced", "difficulty": "advanced", "content": "Neural Networks are computing systems inspired by biological neural networks that constitute animal brains.", "connections": 7, "notes": []},
    {"id": "c5", "name": "Supervised Learning", "category": "core", "difficulty": "intermediate", "content": "Supervised Learning uses labeled data to train models to predict outcomes.", "connections": 4, "notes": []},
    {"id": "c6", "name": "Unsupervised Learning", "category": "core", "difficulty": "intermediate", "content": "Unsupervised Learning finds patterns and structures in unlabeled data.", "connections": 4, "notes": []},
]

MOCK_RELATIONSHIPS = [
    {"source": "c1", "target": "c2", "description": "is the broader field that includes"},
    {"source": "c2", "target": "c3", "description": "is a subset that uses neural networks"},
    {"source": "c3", "target": "c4", "description": "is built on"},
    {"source": "c2", "target": "c5", "description": "includes"},
    {"source": "c2", "target": "c6", "description": "includes"},
]

MOCK_RECOMMENDATIONS = {
    "weak_concepts": [
        {"name": "Neural Networks", "reason": "Low connection density", "suggested_action": "Review fundamental concepts"},
        {"name": "Unsupervised Learning", "reason": "Limited practice examples", "suggested_action": "Complete clustering exercises"}
    ],
    "next_to_learn": [
        {"name": "Reinforcement Learning", "reason": "Strong prerequisite knowledge", "estimated_time": "2 hours"},
        {"name": "Transformers", "reason": "High demand in industry", "estimated_time": "3 hours"}
    ],
    "revise_now": [
        {"name": "Machine Learning Basics", "reason": "Last reviewed 2 weeks ago", "importance": "High"},
        {"name": "Supervised Learning Algorithms", "reason": "Upcoming assessment", "importance": "Medium"}
    ],
    "learning_path": [
        {"step": 1, "concept": "Artificial Intelligence", "status": "completed"},
        {"step": 2, "concept": "Machine Learning", "status": "in_progress"},
        {"step": 3, "concept": "Supervised Learning", "status": "pending"},
        {"step": 4, "concept": "Neural Networks", "status": "pending"},
        {"step": 5, "concept": "Deep Learning", "status": "pending"}
    ]
}

# ============================================
# SMART NOTE CATEGORIZATION
# ============================================

def extract_topics_from_note(note_content: str) -> List[str]:
    """Extract relevant topics from note content"""
    topics = []
    note_lower = note_content.lower()
    
    topic_keywords = {
        "Artificial Intelligence": ["ai", "artificial intelligence", "intelligence", "smart machines"],
        "Machine Learning": ["machine learning", "ml", "learning algorithms", "predictive models"],
        "Deep Learning": ["deep learning", "dl", "neural networks", "deep neural"],
        "Neural Networks": ["neural network", "neuron", "activation function", "backpropagation"],
        "Supervised Learning": ["supervised", "labeled data", "classification", "regression"],
        "Unsupervised Learning": ["unsupervised", "unlabeled", "clustering", "dimensionality reduction"],
        "Reinforcement Learning": ["reinforcement", "reward", "agent", "policy", "q-learning"],
        "Natural Language Processing": ["nlp", "text", "language", "sentiment", "transformer"],
        "Computer Vision": ["vision", "image", "object detection", "convolutional", "cnn"],
        "Transformers": ["transformer", "attention", "bert", "gpt", "llm"]
    }
    
    for topic, keywords in topic_keywords.items():
        for keyword in keywords:
            if keyword in note_lower:
                topics.append(topic)
                break
    
    return list(set(topics))

def auto_categorize_note(note_content: str) -> str:
    """Automatically determine category for a note"""
    note_lower = note_content.lower()
    
    categories = {
        "core": ["fundamental", "basic", "introduction", "overview", "concept"],
        "advanced": ["advanced", "complex", "deep", "cutting-edge", "research"],
        "application": ["application", "implementation", "use case", "practical", "real-world"],
        "theory": ["theory", "mathematical", "algorithm", "principle", "foundation"]
    }
    
    scores = {cat: 0 for cat in categories}
    for cat, keywords in categories.items():
        for keyword in keywords:
            if keyword in note_lower:
                scores[cat] += 1
    
    return max(scores, key=scores.get) if max(scores.values()) > 0 else "core"

# ============================================
# MEMBRAIN CLIENT
# ============================================

class MembrainClient:
    def __init__(self, api_key: str, base_url: str, mock_mode: bool = False):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.mock_mode = mock_mode
        self.headers = {"Content-Type": "application/json"}
    
    def add_concept(self, concept_name: str, category: str = "core", tags: List[str] = None) -> Dict:
        if self.mock_mode:
            time.sleep(0.5)
            new_id = f"mock_{int(time.time())}"
            MOCK_CONCEPTS.append({
                "id": new_id, "name": concept_name, "category": category,
                "difficulty": "intermediate", "content": f"Concept: {concept_name}\nCategory: {category}",
                "connections": 0, "notes": []
            })
            return {"success": True, "memory_id": new_id, "message": f"✨ '{concept_name}' added to knowledge graph!"}

        user_id = st.session_state.get("user_id")
        if not user_id:
            return {"success": False, "error": "No active user session"}

        result = backend_post("/add_concept", {
            "concept_name": concept_name,
            "category": category or "core",
            "tags": tags or [],
            "user_id": user_id
        })
        
        if not result["ok"]:
            return {"success": False, "error": f"Backend request failed: {result['error']}"}

        payload = result["data"]
        return {
            "success": payload.get("success", True),
            "memory_id": payload.get("memory_id", concept_name),
            "message": payload.get("message", f"✨ '{concept_name}' added!")
        }
    
    def add_note(self, note_title: str, note_content: str, concept_id: str = None) -> Dict:
        if self.mock_mode:
            time.sleep(0.5)
            topics = extract_topics_from_note(note_content)
            category = auto_categorize_note(note_content)
            
            matched_concepts = []
            for concept in MOCK_CONCEPTS:
                if concept["name"].lower() in note_content.lower() or any(topic.lower() in concept["name"].lower() for topic in topics):
                    matched_concepts.append(concept["id"])
                    if "notes" not in concept:
                        concept["notes"] = []
                    concept["notes"].append({
                        "id": f"note_{int(time.time())}",
                        "title": note_title,
                        "content": note_content,
                        "timestamp": datetime.now().isoformat()
                    })
            
            if not matched_concepts and topics:
                new_concept_name = topics[0]
                new_id = f"mock_{int(time.time())}"
                MOCK_CONCEPTS.append({
                    "id": new_id, "name": new_concept_name, "category": category,
                    "difficulty": "intermediate", "content": f"Auto-created from note about {new_concept_name}",
                    "connections": 0, "notes": [{
                        "id": f"note_{int(time.time())}",
                        "title": note_title,
                        "content": note_content,
                        "timestamp": datetime.now().isoformat()
                    }]
                })
                matched_concepts = [new_id]
            
            return {
                "success": True, 
                "message": f"📝 Note added! Linked to {len(matched_concepts)} concept(s)",
                "matched_concepts": matched_concepts,
                "topics": topics,
                "category": category
            }

        user_id = st.session_state.get("user_id")
        if not user_id:
            return {"success": False, "error": "No active user session"}

        result = backend_post("/add_note", {"text": note_content, "user_id": user_id})
        if not result["ok"]:
            return {"success": False, "error": f"Backend request failed: {result['error']}"}

        payload = result["data"]
        concepts = payload.get("concepts", [])
        return {
            "success": True,
            "message": f"📝 Note added! Linked to {len(concepts)} concept(s)",
            "matched_concepts": concepts,
            "topics": concepts,
            "category": "core"
        }
    
    def get_concept_notes(self, concept_id: str) -> List[Dict]:
        if self.mock_mode:
            for concept in MOCK_CONCEPTS:
                if concept["id"] == concept_id:
                    return concept.get("notes", [])
        return []
    
    def search_concepts(self, query: str, k: int = 10) -> List[Dict]:
        if self.mock_mode:
            query_lower = query.lower()
            return [{"id": c["id"], "name": c["name"], "content": c["content"], 
                    "score": round(random.uniform(0.7, 0.95), 2), "tags": [c.get("category", "concept")]} 
                    for c in MOCK_CONCEPTS if query_lower in c["name"].lower()][:k]

        user_id = st.session_state.get("user_id")
        if not user_id:
            return []

        result = backend_post("/search", {"query": query, "user_id": user_id})
        if not result["ok"]:
            return []

        payload = result["data"]
        tool_results = payload.get("results", []) if isinstance(payload, dict) else []
        values: List[str] = []
        for item in tool_results:
            if isinstance(item, dict):
                values.extend(item.get("results", []))

        return [
            {
                "id": f"search_{idx}",
                "name": content,
                "content": content,
                "score": 1.0,
                "tags": ["memory"]
            }
            for idx, content in enumerate(values[:k])
        ]
    
    def get_knowledge_graph(self) -> Dict:
        if self.mock_mode:
            return {"nodes": MOCK_CONCEPTS, "edges": MOCK_RELATIONSHIPS}

        user_id = st.session_state.get("user_id")
        if not user_id:
            return {"nodes": [], "edges": []}

        result = backend_get(f"/graph/{user_id}")
        if not result["ok"]:
            return {"nodes": [], "edges": []}

        payload = result["data"]
        raw_nodes = payload.get("nodes", [])
        raw_edges = payload.get("edges", [])

        # Adapt backend graph shape to frontend renderer shape.
        nodes = [
            {
                "id": node.get("id"),
                "name": node.get("label", str(node.get("id"))),
                "category": "core",
                "difficulty": "intermediate",
                "content": node.get("label", ""),
                "connections": 0,
                "notes": []
            }
            for node in raw_nodes
        ]

        return {"nodes": nodes, "edges": raw_edges}
    
    def get_recommendations(self) -> Dict:
        if self.mock_mode:
            return MOCK_RECOMMENDATIONS

        user_id = st.session_state.get("user_id")
        if not user_id:
            return {"weak_concepts": [], "next_to_learn": [], "revise_now": [], "learning_path": []}

        result = backend_get(f"/recommend/{user_id}")
        if not result["ok"]:
            return {"weak_concepts": [], "next_to_learn": [], "revise_now": [], "learning_path": []}

        payload = result["data"]
        weak_raw = payload.get("weak_concepts", [])
        next_raw = payload.get("next_to_learn", [])
        revise_raw = payload.get("revise", [])

        return {
            "weak_concepts": [
                {"name": c, "reason": "Low mastery", "suggested_action": "Review fundamentals"}
                for c in weak_raw
            ],
            "next_to_learn": [
                {"name": c, "reason": "Next recommended by backend", "estimated_time": "30-60 mins"}
                for c in next_raw
            ],
            "revise_now": [
                {"name": c, "importance": "High"}
                for c in revise_raw
            ],
            "learning_path": [
                {"step": idx + 1, "concept": c, "status": "pending"}
                for idx, c in enumerate(next_raw)
            ]
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
    st.markdown(f"""
    <div class="toast-notification" style="background: linear-gradient(135deg, {'#4caf50' if type == 'success' else '#ff9800'}, {'#2e7d32' if type == 'success' else '#f57c00'});">
        {message}
    </div>
    """, unsafe_allow_html=True)

def show_mastery_bar(concept_name: str, mastery_percentage: int):
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
# GRAPH VISUALIZATION
# ============================================

def create_interactive_graph(nodes: List[Dict], edges: List[Dict]) -> Network:
    net = Network(height="650px", width="100%", bgcolor="#1a1a2e", font_color="white", notebook=False, cdn_resources="remote")
    
    net.set_options("""
    var options = {
        "nodes": {
            "shape": "dot", "size": 45, "borderWidth": 2,
            "font": {"size": 14, "face": "Arial", "color": "white"},
            "shadow": {"enabled": true, "size": 15}
        },
        "edges": {
            "smooth": {"type": "continuous"},
            "font": {"size": 11, "align": "middle", "background": "#2d2d44", "color": "#ffffff"},
            "color": {"color": "#4a4a6a", "highlight": "#ff6b6b", "hover": "#4caf50"},
            "width": 2.5,
            "arrows": {"to": {"enabled": true}}
        },
        "physics": {
            "forceAtlas2Based": {"gravitationalConstant": -120, "springLength": 200},
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 200}
        },
        "interaction": {"hover": true, "tooltipDelay": 150, "navigationButtons": true}
    }
    """)
    
    color_map = {"core": "#4caf50", "advanced": "#ff9800", "application": "#2196f3", "theory": "#9c27b0"}
    
    # Get set of valid node IDs
    valid_node_ids = {node.get("id") for node in nodes}
    
    # Calculate actual connection counts based on edges (only for edges between existing nodes)
    connection_count = {}
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        # Only count edges where both nodes exist
        if source in valid_node_ids and target in valid_node_ids:
            connection_count[source] = connection_count.get(source, 0) + 1
            connection_count[target] = connection_count.get(target, 0) + 1
    
    for node in nodes:
        node_id = node.get("id")
        node_name = node.get("name")
        category = node.get("category", "core")
        color = color_map.get(category, "#ff5722")
        note_count = len(node.get("notes", []))
        actual_connections = connection_count.get(node_id, 0)
        
        net.add_node(node_id, label=node_name, 
                    title=f"<b>{node_name}</b><br>Category: {category}<br>📝 Notes: {note_count}<br>🔗 Connections: {actual_connections}", 
                    color=color, size=50 if node.get("difficulty") == "advanced" else 40)
    
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        # Only add edges where both nodes exist
        if source in valid_node_ids and target in valid_node_ids:
            description = edge.get("description") or "Connection"
            label = (description[:20] + "...") if len(description) > 20 else description
            net.add_edge(source, target, 
                        title=description, 
                        label=label)
    
    return net

def analyze_graph_metrics(G: nx.Graph) -> Dict:
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
# SPLIT LAYOUT AUTHENTICATION PAGE
# ============================================

def show_split_auth_page():
    """Display split layout with About on left and Auth on right"""
    
    # Create two columns
    left_col, right_col = st.columns([1.2, 0.8], gap="large")
    
    with left_col:
        st.markdown("""
        <div style="animation: fadeInUp 0.6s ease-out;">
            <div style="text-align: center; margin-bottom: 30px;">
                <div style="font-size: 80px; animation: floatPulse 3s ease-in-out infinite;">🧠</div>
                <h1 style="font-size: 48px;">AI Tutor</h1>
                <p style="font-size: 18px; color: #b0b0b0;">Adaptive Learning Powered by Knowledge Graphs</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # About Section
        st.markdown("""
        <div class="glass-card" style="margin-bottom: 20px;">
            <h2 style="text-align: center;">📚 About AI Tutor</h2>
            <p style="line-height: 1.8;">AI Tutor is an intelligent learning platform that uses semantic memory and knowledge graphs to help you master new concepts. Our system:</p>
            <ul style="line-height: 2;">
                <li>✨ Visualizes relationships between concepts</li>
                <li>🎯 Provides personalized learning recommendations</li>
                <li>🔍 Enables semantic search across your knowledge base</li>
                <li>📊 Tracks your learning progress and mastery</li>
                <li>🧠 Uses Membrain's semantic memory technology</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Key Features Section
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
    
    with right_col:
        st.markdown("""
        <div style="animation: fadeInScale 0.5s ease-out;">
            <div class="glass-card">
                <h3 style="text-align: center;">🚀 Get Started</h3>
                <p style="text-align: center; color: #b0b0b0; margin-bottom: 20px;">Choose an option to continue</p>
        """, unsafe_allow_html=True)
        
        # Login Button
        if st.button("🔐 Login", use_container_width=True, key="main_login_btn"):
            st.session_state.show_login_form = True
            st.session_state.show_register_form = False
            st.rerun()
        
        # Register Button
        if st.button("📝 Sign Up", use_container_width=True, key="main_register_btn"):
            st.session_state.show_login_form = False
            st.session_state.show_register_form = True
            st.rerun()
        
        st.markdown("---")
        
        # Show Login Form if selected
        if st.session_state.show_login_form:
            st.markdown("#### 🔐 Login to Your Account")
            
            email = st.text_input("Email", placeholder="your@email.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
            
            if st.button("Login", use_container_width=True, key="login_submit"):
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
        
        # Show Register Form if selected
        elif st.session_state.show_register_form:
            st.markdown("#### 📝 Create New Account")
            
            name = st.text_input("Full Name", placeholder="John Doe", key="reg_name")
            email = st.text_input("Email", placeholder="your@email.com", key="reg_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="••••••••", key="reg_confirm")
            
            if st.button("Sign Up", use_container_width=True, key="register_submit"):
                if not name or not email or not password:
                    st.warning("Please fill all fields")
                elif password != confirm_password:
                    st.error("Passwords do not match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    result = register_user(email, password, name)
                    if result["success"]:
                        show_toast(result["message"])
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(result["error"])
        
        else:
            # Default state - show welcome message
            st.markdown("""
            <div style="text-align: center; padding: 40px 0;">
                <div style="font-size: 48px;">✨</div>
                <p style="color: #b0b0b0;">Select Login or Sign Up to continue your learning journey</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div></div>", unsafe_allow_html=True)

# ============================================
# MAIN APP CONTENT
# ============================================

def init_session_state():
    defaults = {
        "graph_data": None,
        "selected_concept": None,
        "search_results": [],
        "refresh_graph": False,
        "membrain_client": None,
        "use_mock_mode": USE_MOCK_MODE,
        "selected_topic": None,
        "recent_notes": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    if st.session_state.membrain_client is None:
        st.session_state.membrain_client = MembrainClient(
            "", BACKEND_API_URL, st.session_state.use_mock_mode
        )

def show_main_app():
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
        
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()
        
        st.markdown("---")
        
        # Add Concept Section
        st.markdown("### ✨ Add New Concept")
        with st.form("add_concept_form", clear_on_submit=True):
            concept_name = st.text_input("Concept Name", placeholder="e.g., Reinforcement Learning")
            category = st.selectbox("Category", ["core", "advanced", "application", "theory"])
            difficulty = st.selectbox("Difficulty", ["beginner", "intermediate", "advanced"])
            tags = st.text_input("Tags", placeholder="ai, ml, algorithms")
            
            if st.form_submit_button("➕ Add to Graph", use_container_width=True) and concept_name:
                with st.spinner(f"Adding '{concept_name}'..."):
                    tag_list = [t.strip() for t in tags.split(",") if t.strip()] + [category, difficulty]
                    result = st.session_state.membrain_client.add_concept(concept_name, category, tag_list)
                    if result["success"]:
                        show_toast(result["message"])
                        st.session_state.refresh_graph = True
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', 'Unknown error')}")
        
        st.markdown("---")
        
        # Add Note Section
        st.markdown("### 📝 Add Smart Note")
        with st.form("add_note_form", clear_on_submit=True):
            note_title = st.text_input("Note Title", placeholder="e.g., Understanding Backpropagation")
            note_content = st.text_area("Note Content", placeholder="Write your notes here... The system will automatically link them to relevant concepts!", height=150)
            
            if st.form_submit_button("📌 Save Note", use_container_width=True) and note_title and note_content:
                with st.spinner("Processing note and linking to concepts..."):
                    result = st.session_state.membrain_client.add_note(note_title, note_content)
                    if result["success"]:
                        show_toast(result["message"])
                        if result.get("matched_concepts"):
                            show_toast(f"🔗 Linked to {len(result['matched_concepts'])} concept(s)", "info")
                        if result.get("topics"):
                            show_toast(f"📚 Detected topics: {', '.join(result['topics'])}", "info")
                        st.session_state.refresh_graph = True
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ {result.get('error', 'Unknown error')}")
        
        st.markdown("---")
        
        # Search
        st.markdown("### 🔍 Search")
        search_query = st.text_input("", placeholder="What do you want to learn about?")
        if search_query:
            with st.spinner("Searching..."):
                st.session_state.search_results = st.session_state.membrain_client.search_concepts(search_query)
        
        st.markdown("---")
        
        # Stats
        if st.session_state.graph_data:
            nodes = st.session_state.graph_data.get("nodes", [])
            edges = st.session_state.graph_data.get("edges", [])
            G = nx.Graph()
            for node in nodes:
                G.add_node(node.get("id"), **node)
            for edge in edges:
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
    
    # Main content
    st.markdown("""
    <div class="main-header">
        <h1>📚 Your Knowledge Graph</h1>
        <p>Add concepts to build your graph | Add notes that auto-link to topics</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Knowledge Graph", "🎯 Learning Dashboard", "📝 Notes & Concepts", "🔍 Search"])
    
    with tab1:
        if st.session_state.refresh_graph or not st.session_state.graph_data:
            with st.spinner("Loading knowledge graph..."):
                st.session_state.graph_data = st.session_state.membrain_client.get_knowledge_graph()
                st.session_state.refresh_graph = False
        
        if st.session_state.graph_data:
            nodes = st.session_state.graph_data.get("nodes", [])
            edges = st.session_state.graph_data.get("edges", [])
            
            if nodes:
                net = create_interactive_graph(nodes, edges)
                graph_html = "knowledge_graph.html"
                net.save_graph(graph_html)
                with open(graph_html, 'r', encoding='utf-8') as f:
                    st.components.v1.html(f.read(), height=650)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info("💡 **Tips:** Hover over edges to see relationships")
                with col2:
                    st.success("🎯 **Interact:** Drag to rearrange | Zoom with scroll")
                with col3:
                    st.markdown("""
                    <div class="glass-card" style="padding: 10px;">
                        <b>🎨 Legend:</b><br>
                        <span style="color: #4caf50;">●</span> Core | <span style="color: #ff9800;">●</span> Advanced<br>
                        <span style="color: #2196f3;">●</span> Applications | <span style="color: #9c27b0;">●</span> Theory
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("No concepts yet. Add your first concept using the sidebar!")
    
    with tab2:
        st.markdown("### 🎯 Adaptive Learning Dashboard")
        
        with st.spinner("Analyzing..."):
            recommendations = st.session_state.membrain_client.get_recommendations()
        
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
        if st.session_state.graph_data:
            for node in st.session_state.graph_data.get("nodes", [])[:5]:
                mastery = random.randint(30, 95)
                show_mastery_bar(node.get("name"), mastery)
    
    with tab3:
        st.markdown("### 📝 Your Notes & Concepts")
        
        if st.session_state.graph_data:
            nodes = st.session_state.graph_data.get("nodes", [])
            
            concept_options = [c.get("name") for c in nodes]
            selected_concept_name = st.selectbox("Select a concept to view its notes:", concept_options if concept_options else ["No concepts yet"])
            
            if selected_concept_name != "No concepts yet":
                selected_concept = next((c for c in nodes if c.get("name") == selected_concept_name), None)
                if selected_concept:
                    st.markdown(f"""
                    <div class="glass-card">
                        <h3>📘 {selected_concept.get('name')}</h3>
                        <p>{selected_concept.get('content')}</p>
                        <div style="display: flex; gap: 10px;">
                            <span>🏷️ {selected_concept.get('category')}</span>
                            <span>📊 {selected_concept.get('difficulty')}</span>
                            <span>🔗 {selected_concept.get('connections')} connections</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    notes = selected_concept.get("notes", [])
                    if notes:
                        st.markdown("#### 📝 Related Notes")
                        for note in notes:
                            with st.expander(f"📄 {note.get('title')}"):
                                st.markdown(note.get('content'))
                                st.caption(f"Added: {note.get('timestamp', 'Recently')}")
                    else:
                        st.info("No notes yet. Add notes in the sidebar and they'll automatically link to relevant concepts!")
        else:
            st.info("Add concepts to start building your knowledge base!")
    
    with tab4:
        st.markdown("### 🔍 Search Results")
        
        if st.session_state.search_results:
            for result in st.session_state.search_results[:10]:
                with st.expander(f"📖 {result.get('name')} (Relevance: {result.get('score', 0):.2f})"):
                    st.markdown(result.get('content', 'No description'))
                    if st.button(f"View Details", key=f"view_{result.get('id')}"):
                        st.session_state.selected_concept = result
                        st.rerun()
        else:
            st.info("🔎 Enter a search query in the sidebar to find concepts")

# ============================================
# MAIN
# ============================================

def main():
    st.set_page_config(page_title="AI Tutor", page_icon="✨", layout="wide")
    add_custom_css()
    init_auth_state()
    init_session_state()
    
    if st.session_state.use_mock_mode and st.session_state.logged_in:
        st.info("🎨 **Demo Mode** - Using sample data. Set USE_MOCK_MODE=false and run backend for real data.")
    
    if st.session_state.logged_in:
        show_main_app()
    else:
        show_split_auth_page()

if __name__ == "__main__":
    main()