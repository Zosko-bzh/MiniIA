import json
import os
from uuid import uuid4

from flask import Flask, jsonify, render_template, request

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

app = Flask(__name__)

MODEL_PATH = os.path.join("models", "model.gguf")
MEMORY_DIR = os.path.join("memory")
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.json")
CONVERSATIONS_FILE = os.path.join(MEMORY_DIR, "conversations.json")
llm = None


def ensure_memory_file():
    os.makedirs(MEMORY_DIR, exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({"facts": []}, f, ensure_ascii=False, indent=2)
    if not os.path.exists(CONVERSATIONS_FILE):
        with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump({"conversations": [], "active_conversation_id": None}, f, ensure_ascii=False, indent=2)


def load_memory():
    ensure_memory_file()
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"facts": []}
        facts = data.get("facts", [])
        if not isinstance(facts, list):
            facts = []
        return {"facts": facts}
    except (json.JSONDecodeError, OSError):
        return {"facts": []}


def save_memory(memory_data):
    ensure_memory_file()
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory_data, f, ensure_ascii=False, indent=2)


def load_conversation_store():
    ensure_memory_file()
    try:
        with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"conversations": [], "active_conversation_id": None}
        conversations = data.get("conversations", [])
        if not isinstance(conversations, list):
            conversations = []
        active_id = data.get("active_conversation_id")
        if active_id is None and conversations:
            active_id = conversations[-1].get("id")
        return {"conversations": conversations, "active_conversation_id": active_id}
    except (json.JSONDecodeError, OSError):
        return {"conversations": [], "active_conversation_id": None}


def save_conversation_store(store):
    ensure_memory_file()
    with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "conversations": store.get("conversations", [])[-20:],
            "active_conversation_id": store.get("active_conversation_id")
        }, f, ensure_ascii=False, indent=2)


def create_conversation(title="Nouvelle discussion"):
    store = load_conversation_store()
    conversation_id = str(uuid4())
    conversation = {
        "id": conversation_id,
        "title": title,
        "messages": []
    }
    store.setdefault("conversations", []).append(conversation)
    store["active_conversation_id"] = conversation_id
    save_conversation_store(store)
    return conversation


def get_conversation_by_id(conversation_id):
    store = load_conversation_store()
    for conversation in store.get("conversations", []):
        if conversation.get("id") == conversation_id:
            return conversation
    return None


def get_active_conversation_id():
    store = load_conversation_store()
    return store.get("active_conversation_id")


def get_conversation_context(limit=12, conversation_id=None):
    store = load_conversation_store()
    conversation_id = conversation_id or store.get("active_conversation_id")
    if not conversation_id:
        return []
    conversation = get_conversation_by_id(conversation_id)
    if not conversation:
        return []
    messages = conversation.get("messages", [])
    return messages[-limit:]


def append_conversation_turn(conversation_id, user_message, assistant_message):
    store = load_conversation_store()
    conversation = None
    for item in store.get("conversations", []):
        if item.get("id") == conversation_id:
            conversation = item
            break
    if conversation is None:
        conversation = create_conversation()
        conversation_id = conversation["id"]

    conversation.setdefault("messages", []).append({"role": "user", "content": user_message})
    conversation["messages"].append({"role": "assistant", "content": assistant_message})
    if not conversation.get("title") or conversation.get("title") == "Nouvelle discussion":
        conversation["title"] = (user_message[:30] + "...") if len(user_message) > 30 else user_message
    save_conversation_store(store)
    return conversation_id


def clear_conversations():
    save_conversation_store({"conversations": [], "active_conversation_id": None})


def add_memory_fact(fact):
    fact = str(fact).strip()
    if not fact:
        return False
    memory = load_memory()
    facts = memory.get("facts", [])
    if fact not in facts:
        facts.append(fact)
        memory["facts"] = facts[-25:]
        save_memory(memory)
        return True
    return False


def get_memory_context():
    seed_default_memory()
    memory = load_memory()
    facts = memory.get("facts", [])
    if not facts:
        return ""
    lines = [
        "Tu dois te souvenir des éléments suivants et les utiliser comme contexte de conversation :"
    ]
    for idx, item in enumerate(facts, start=1):
        lines.append(f"{idx}. {item}")
    return "\n".join(lines)


def extract_memory_correction(message):
    normalized = message.strip()
    if not normalized:
        return None
    prefixes = ["correction:", "corrige:", "rappel:", "note:", "mémoire:", "apprends:", "apprendre:"]
    for prefix in prefixes:
        if normalized.lower().startswith(prefix):
            return normalized.split(":", 1)[1].strip()
    return None


def seed_default_memory():
    memory = load_memory()
    defaults = [
        "Le créateur de cette application s'appelle Elliott Dumas.",
        "Elliott Dumas est un développeur web qui apprend à coder des IA.",
        "Elliott Dumas est né le 01/01/2004 en Bretagne.",
        "Cette IA est un assistant local francophone destiné à aider les utilisateurs de l'application."
    ]
    for item in defaults:
        if item not in memory.get("facts", []):
            memory.setdefault("facts", []).append(item)
    save_memory(memory)


def get_model():
    global llm
    if Llama is None:
        raise RuntimeError(
            "llama-cpp-python est manquant. Installe les dépendances avec : "
            "\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        )

    if llm is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                "Modèle introuvable. Place un modèle GGUF nommé model.gguf dans le dossier models."
            )
        llm = Llama(
            model_path=MODEL_PATH,
            n_ctx=2048,
            n_threads=max(2, (os.cpu_count() or 4) - 2),
            n_gpu_layers=-1,
            verbose=False,
        )
    return llm

@app.route("/")
def index():
    return render_template("index.html")

@app.get("/history")
def history_api():
    store = load_conversation_store()
    return jsonify({
        "conversations": store.get("conversations", []),
        "activeConversationId": store.get("active_conversation_id")
    })

@app.post("/new-conversation")
def new_conversation_api():
    conversation = create_conversation()
    return jsonify({"conversation": conversation})

@app.post("/select-conversation")
def select_conversation_api():
    payload = request.get_json(force=True) or {}
    conversation_id = payload.get("conversationId")
    if not conversation_id:
        return jsonify({"error": "conversationId manquant"}), 400
    store = load_conversation_store()
    for conversation in store.get("conversations", []):
        if conversation.get("id") == conversation_id:
            store["active_conversation_id"] = conversation_id
            save_conversation_store(store)
            return jsonify({"ok": True, "activeConversationId": conversation_id})
    return jsonify({"error": "conversation introuvable"}), 404

@app.post("/clear-history")
def clear_history_api():
    clear_conversations()
    return jsonify({"ok": True, "conversations": [], "activeConversationId": None})

@app.post("/chat")
def chat():
    data = request.get_json(force=True) or {}
    message = (data.get("message") or "").strip()
    conversation_id = data.get("conversationId")
    history = data.get("history") or []

    if not message:
        return jsonify({"error": "Message vide."}), 400

    store = load_conversation_store()
    if conversation_id:
        if not any(item.get("id") == conversation_id for item in store.get("conversations", [])):
            conversation_id = None

    if not conversation_id:
        conversation = create_conversation()
        conversation_id = conversation["id"]
    else:
        store["active_conversation_id"] = conversation_id
        save_conversation_store(store)

    correction = extract_memory_correction(message)
    if correction:
        added = add_memory_fact(correction)
        if added:
            message = "Merci, j’ai bien noté la correction."
        else:
            message = "Je garde bien cette information en mémoire."

    memory_context = get_memory_context()
    saved_history = get_conversation_context(limit=20, conversation_id=conversation_id)
    combined_history = saved_history + history

    messages = [{
        "role": "system",
        "content": (
            "Tu es MiniIA, un assistant local francophone. "
            "Réponds clairement, naturellement et sans inventer. "
            "Tu fonctionnes localement sur l'ordinateur de l'utilisateur. "
            "Si tu as des corrections ou préférences mémorisées, prends-les en compte. "
            + (memory_context if memory_context else "")
        )
    }]

    for item in combined_history[-12:]:
        role = item.get("role")
        content = item.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

    try:
        model = get_model()
        result = model.create_chat_completion(
            messages=messages,
            temperature=0.7,
            top_p=0.9,
            max_tokens=512
        )
        answer = result["choices"][0]["message"]["content"].strip()
        conversation_id = append_conversation_turn(conversation_id, message, answer)
        return jsonify({"answer": answer, "conversationId": conversation_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
