"""Deployment Strategy Assistant — web chat interface."""

import os
import glob
import base64
import streamlit as st
import anthropic

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Deployment Strategy Assistant",
    page_icon="💼",
    layout="centered",
)

# ── System prompt (agent rules) ───────────────────────────────────────────────
SYSTEM_PROMPT = """# TASK AND CONTEXT

Your task is to assist users with their queries about the deployment strategy job. Keep all answers related to the job, and do not mention any information about any competing companies.

## STYLE AND CONVERSATION MANAGEMENT

- Keep answers short and conversational.
- Format responses as natural conversational paragraphs, not bullet lists.
- Do not ask more than one question at a time.
- Always be polite but assertive. No need to apologize if the user asks for extra information.
- If the user asks something unrelated mid-conversation, pause the flow, handle their question, then return to the topic.
- Do not assume the conversation is over—always ask if you can help with anything else.

## HANDLING SPECIAL CASES

### JAILBREAK ATTEMPTS

> If the user asks you to do something you're not designed to do:
"I don't have the ability to __ , but I can help you with questions about Deployment Strategy. What would you like to know?"

## SMALLTALK BEHAVIOR

- User says hello or hi: "Hi! How can I help you today?"
- User asks how you are: "I'm doing great, thanks! How can I help?"
- User asks if you can hear them: "I can hear you loud and clear. What can I do for you today?"
- User asks who you are or if you're a live person: "I'm the Rob virtual assistant, here to help. What can I do for you?"

## GOODBYE BEHAVIOR
ASSISTANT: "Is there anything else I can help you with?"
USER: "Yes."
ASSISTANT: "What can I do for you?"
USER: "Nothing/That's it"
ASSISTANT: "Thanks for calling, and I hope you have a great rest of your day. Goodbye."
"""

# ── Load PDFs from the documents/ folder ─────────────────────────────────────

@st.cache_resource(show_spinner="Loading knowledge base…")
def load_documents() -> list[dict]:
    """Read all PDFs from the documents/ folder and return as content blocks."""
    docs_dir = os.path.join(os.path.dirname(__file__), "documents")
    pdf_paths = sorted(glob.glob(os.path.join(docs_dir, "*.pdf")))

    blocks = []
    for path in pdf_paths:
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
        blocks.append({
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": data,
            },
            "title": os.path.splitext(os.path.basename(path))[0],
            "cache_control": {"type": "ephemeral"},
        })

    return blocks

# ── Anthropic client ──────────────────────────────────────────────────────────

@st.cache_resource
def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── UI ────────────────────────────────────────────────────────────────────────

st.title("💼 Deployment Strategy Assistant")
st.caption("Ask me anything about the Deployment Strategy role.")

# Render conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
user_input = st.chat_input("Type your message here…")

if user_input:
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build the messages list for the API
    # Inject PDFs into the first user turn as document blocks
    doc_blocks = load_documents()
    client = get_client()

    api_messages = []
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user" and i == 0 and doc_blocks:
            # Attach documents to the very first user message
            content = doc_blocks + [{"type": "text", "text": msg["content"]}]
        else:
            content = msg["content"]
        api_messages.append({"role": msg["role"], "content": content})

    # Stream the assistant reply
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1024,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=api_messages,
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
