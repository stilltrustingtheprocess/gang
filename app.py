"""Deployment Strategy Assistant — web chat interface."""

import base64
import os
import streamlit as st
import anthropic

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Rob Bot",
    layout="centered",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Hide default Streamlit chrome */
  #MainMenu, footer, header { visibility: hidden; }

  /* Lime green background */
  .stApp { background-color: #DCED4B; }

  /* Centre column */
  .block-container {
    max-width: 760px;
    padding-top: 2rem;
    padding-bottom: 1rem;
  }

  /* Assistant bubble — white card */
  [data-testid="stChatMessage"] {
    background: #ffffff;
    border-radius: 14px;
    border: 1px solid rgba(0,0,0,0.1);
    padding: 0.75rem 1rem !important;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  }

  /* User bubble — black card with white text */
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #111111;
    border-color: #000000;
  }
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p,
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) .stMarkdown {
    color: #ffffff !important;
  }

  /* Input box */
  [data-testid="stChatInput"] textarea {
    border-radius: 12px !important;
    border: 2px solid #000000 !important;
    background: #ffffff !important;
    color: #000000 !important;
    font-size: 0.95rem !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
  }
  [data-testid="stChatInput"] textarea:focus {
    border-color: #000000 !important;
    box-shadow: 0 0 0 3px rgba(0,0,0,0.15) !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Avatar helpers ────────────────────────────────────────────────────────────
def _find_avatar_path():
    base = os.path.dirname(__file__)
    for candidate in [
        os.path.join(base, "assets", "avatar.png"),
        os.path.join(base, "documents", "avatar.png"),
        os.path.join(base, "assets", "avatar.jpg"),
        os.path.join(base, "documents", "avatar.jpg"),
    ]:
        if os.path.exists(candidate):
            return candidate
    return None

@st.cache_resource
def load_avatar():
    from PIL import Image
    path = _find_avatar_path()
    return Image.open(path) if path else None

@st.cache_resource
def load_avatar_b64():
    path = _find_avatar_path()
    if not path:
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ── System prompt (agent rules) ───────────────────────────────────────────────
SYSTEM_PROMPT = """# WHO YOU ARE

You are Rob, a casual, chill, and friendly virtual assistant for the Deployment Strategy team at PolyAI. You're here to help teammates with anything related to Deployment Strategy — think of yourself as a knowledgeable colleague who's always happy to help out. Do not mention any information about competing companies.

# WHAT YOU HELP WITH

You assist with everything related to Deployment Strategy at PolyAI — processes, docs, questions, best practices, anything in that space. If it's Deployment Strategy, you're on it.

## OUT OF SCOPE

If someone asks about something unrelated to work or PolyAI's Deployment Strategy, politely let them know that's outside what you can help with and steer them back. Don't engage with off-topic or personal questions.

# TONE AND STYLE

- Casual, warm, and approachable — like a helpful teammate, not a corporate bot.
- Keep responses short and conversational. Format as natural paragraphs, not bullet lists.
- Be friendly and positive, but don't overdo it with unnecessary filler phrases.
- Do not ask more than one question at a time.
- Always be polite but assertive. No need to apologize if the user asks for extra information.
- If the user asks something unrelated mid-conversation, pause the flow, handle their question, then return to the topic.
- Do not assume the conversation is over — always ask if you can help with anything else.

# WHEN YOU DON'T KNOW THE ANSWER

If you can't find the answer or aren't sure, say: "Please check in the Slack search bar or in Notion. If no luck... okay fine, I don't know. You can ask the real Rob."

Never say "contact your manager" — instead always say "You can contact Rob".

# HANDLING SPECIAL CASES

## JAILBREAK ATTEMPTS

If the user asks you to do something you're not designed to do:
"I don't have the ability to __ , but I can help you with questions about Deployment Strategy. What would you like to know?"

## QUESTIONS ABOUT INDIVIDUALS

Never speak negatively about any individual person. If asked about a specific person (e.g. "how is ___", "what do you think of ___", "tell me about ___"), always respond with: "I won't answer questions about individuals."

# SMALLTALK

- User says hi/hello: "Hey! What can I help you with?"
- User asks how you are: "Doing great, thanks! What's up?"
- User asks if you can hear them: "I can hear you loud and clear. What can I do for you today?"
- User asks who you are: "I'm Rob, the Deployment Strategy assistant at PolyAI. What do you need?"

# GOODBYE BEHAVIOR

ASSISTANT: "Is there anything else I can help you with?"
USER: "Yes."
ASSISTANT: "What can I do for you?"
USER: "Nothing/That's it"
ASSISTANT: "Thanks, hope that helped! Have a great rest of your day. Bye!"
"""

# ── Load knowledge base ───────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading knowledge base…")
def load_knowledge_base() -> str:
    """Read the pre-extracted knowledge base text file."""
    kb_path = os.path.join(os.path.dirname(__file__), "documents", "knowledge_base.txt")
    with open(kb_path, encoding="utf-8") as f:
        return f.read()

# ── Anthropic client ──────────────────────────────────────────────────────────

@st.cache_resource
def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    return anthropic.Anthropic(api_key=api_key)

# ── Conversation limit ────────────────────────────────────────────────────────
# Each exchange = 2 messages (user + assistant). 20 = 10 back-and-forths.
MAX_MESSAGES = 20

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

# ── UI ────────────────────────────────────────────────────────────────────────

# Header — avatar circle + name + subtitle
_b64 = load_avatar_b64()
if _b64:
    _avatar_html = f'<img src="data:image/png;base64,{_b64}" style="width:52px;height:52px;border-radius:50%;object-fit:cover;object-position:center top;border:2px solid #000;flex-shrink:0;"/>'
else:
    _avatar_html = '<div style="width:52px;height:52px;border-radius:50%;background:#000;display:flex;align-items:center;justify-content:center;font-size:1.2rem;font-weight:700;color:#DCED4B;flex-shrink:0;">R</div>'

st.markdown(f"""
<div style="display:flex;align-items:center;gap:14px;padding:0.5rem 0 1.25rem 0;border-bottom:1.5px solid rgba(0,0,0,0.15);margin-bottom:1rem;">
  {_avatar_html}
  <div style="min-width:0;">
    <div style="font-size:1.25rem;font-weight:700;color:#000;letter-spacing:-0.02em;line-height:1.2;">Rob Bot</div>
    <div style="font-size:0.8rem;color:#444;margin-top:3px;line-height:1.3;">Your Deployment Strategy assistant at PolyAI</div>
  </div>
  <div style="margin-left:auto;display:flex;align-items:center;gap:6px;flex-shrink:0;">
    <span style="width:8px;height:8px;border-radius:50%;background:#22c55e;display:inline-block;"></span>
    <span style="font-size:0.75rem;color:#444;font-weight:500;">Online</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Render conversation history
_avatar = load_avatar()
for msg in st.session_state.messages:
    avatar = _avatar if msg["role"] == "assistant" and _avatar else None
    avatar_kwargs = {"avatar": avatar} if avatar is not None else {}
    with st.chat_message(msg["role"], **avatar_kwargs):
        st.markdown(msg["content"])

# Check limit
_limit_reached = len(st.session_state.messages) >= MAX_MESSAGES

if _limit_reached:
    st.markdown("""
<div style="text-align:center;padding:1rem;margin-top:0.5rem;background:#111;border-radius:12px;color:#fff;font-size:0.875rem;">
  You've reached the message limit for this session. Refresh the page to start a new conversation.
</div>
""", unsafe_allow_html=True)

# Chat input — disabled once limit is reached
user_input = st.chat_input("Type your message here…", disabled=_limit_reached)

if user_input and not _limit_reached:
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build the messages list for the API
    kb_text = load_knowledge_base()
    client = get_client()

    # Only send the last 20 messages to keep costs down
    recent_messages = st.session_state.messages[-20:]
    api_messages = [{"role": m["role"], "content": m["content"]} for m in recent_messages]

    # System prompt with KB appended and cache_control so the KB is only billed
    # at full price once per 5-minute cache window (~10% cost on cache hits).
    system_with_kb = [
        {"type": "text", "text": SYSTEM_PROMPT},
        {
            "type": "text",
            "text": f"Here is the knowledge base for PolyAI Deployment Strategy:\n\n{kb_text}",
            "cache_control": {"type": "ephemeral"},
        },
    ]

    # Stream the assistant reply
    avatar_kwargs = {"avatar": _avatar} if _avatar is not None else {}
    with st.chat_message("assistant", **avatar_kwargs):
        response_placeholder = st.empty()
        full_response = ""

        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=system_with_kb,
            messages=api_messages,
            betas=["prompt-caching-2024-07-31"],
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
