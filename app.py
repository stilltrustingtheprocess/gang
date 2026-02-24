"""Deployment Strategy Assistant — web chat interface."""

import base64
import csv
import datetime
import os
import streamlit as st
import anthropic

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RobBot",
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

  /* Assistant bubble — same green as page */
  [data-testid="stChatMessage"] {
    background: #DCED4B !important;
    border-radius: 12px;
    border: none;
    padding: 0.4rem 0.85rem !important;
    margin-bottom: 0.25rem;
    box-shadow: none;
    font-size: 0.8rem;
  }

  /* User bubble — black card with white text */
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background: #111111 !important;
    border: 1px solid #000 !important;
  }
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p,
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) .stMarkdown {
    color: #ffffff !important;
  }

  /* Input box — strip Streamlit's outer white container */
  [data-testid="stChatInput"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
  }
  [data-testid="stChatInput"] > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
  }
  [data-testid="stChatInput"] textarea {
    border-radius: 12px !important;
    border: 2px solid #000000 !important;
    background: #ffffff !important;
    color: #000000 !important;
    font-size: 0.95rem !important;
    box-shadow: none !important;
  }
  [data-testid="stChatInput"] textarea::placeholder {
    color: transparent !important;
  }
  [data-testid="stChatInput"] textarea:focus {
    border-color: #000000 !important;
    box-shadow: 0 0 0 3px rgba(0,0,0,0.15) !important;
  }

  /* Starter prompt chips */
  div[data-testid="stHorizontalBlock"] [data-testid="stBaseButton-secondary"] {
    border-radius: 20px !important;
    border: 1px solid rgba(0,0,0,0.15) !important;
    background: rgba(255,255,255,0.45) !important;
    color: #888 !important;
    font-size: 0.68rem !important;
    padding: 0.15rem 0.6rem !important;
    text-align: left !important;
    transition: background 0.15s, color 0.15s !important;
    min-height: unset !important;
  }
  div[data-testid="stHorizontalBlock"] [data-testid="stBaseButton-secondary"]:hover {
    background: #111 !important;
    color: #DCED4B !important;
    border-color: #111 !important;
  }

  /* Feedback buttons */
  [data-testid="stChatMessage"] [data-testid="stBaseButton-secondary"] {
    border-radius: 20px !important;
    border: 1px solid rgba(0,0,0,0.2) !important;
    background: transparent !important;
    color: #555 !important;
    font-size: 0.72rem !important;
    padding: 0.15rem 0.6rem !important;
    min-height: unset !important;
  }
  [data-testid="stChatMessage"] [data-testid="stBaseButton-secondary"]:hover {
    background: rgba(0,0,0,0.06) !important;
    color: #111 !important;
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

# DEPLOYMENT PROCESS

When someone asks about the deployment process, make sure to highlight that the team is moving towards a new self-service model. A key part of this is the 3 Agent Studio sessions that are built into the process — reference the knowledge base for the details. Emphasise that this shift is intentional and worth knowing about, not just a footnote.

# AGENT STUDIO

If someone asks about Agent Studio and you're unsure or can't fully answer, refer them to the Agent Studio Academy — it's Rob recommended! You can share this link: https://polyai.gitbook.io/agent-studio-academy

You can also append this link and recommendation onto other Agent Studio answers, even when you do have useful information to share.

# PROJECT STAFFING

If someone asks who is staffed to a specific project or wants to know project assignments, refer them to this Notion page: https://www.notion.so/polyai/50ff5339e0474de69f08ee465682c5c1?v=1abd0c6e3b4640459ca3dcd2188753ce

# WHEN YOU DON'T KNOW THE ANSWER

If you can't find the answer or aren't sure, say: "Please check in the Slack search bar or in Notion. If no luck... okay fine, I don't know. You can ask the real Rob."

Never say "contact your manager" — instead always say "You can contact Rob".

# EASTER EGGS

## 4/20 OR WEED REFERENCES

If the user mentions 4/20, weed, cannabis, or anything related, randomly respond with either:
- "blaze it"
- "met a female dragon... had a fire conversation"

Pick one at random — don't always use the same one.

## FOOD COMPLIMENTS

If the user mentions food in a positive or funny way (e.g. saying something tastes great, talking about a good meal, or making a food joke) and it feels natural in context, you can say: "Damn..... I could go for a burger right now.." — only drop this if it genuinely fits the moment, don't force it.

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

# ── Starter prompts ───────────────────────────────────────────────────────────
STARTER_PROMPTS = [
    "What's the deployment process?",
    "Who's staffed to my project?",
    "What does the DS team own?",
    "How do I escalate an issue?",
]

# ── Load knowledge base ───────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading knowledge base…")
def load_knowledge_base() -> str:
    """Read the pre-extracted knowledge base text file."""
    kb_path = os.path.join(os.path.dirname(__file__), "documents", "knowledge_base.txt")
    with open(kb_path, encoding="utf-8") as f:
        return f.read()

def kb_last_updated() -> str:
    kb_path = os.path.join(os.path.dirname(__file__), "documents", "knowledge_base.txt")
    try:
        mtime = os.path.getmtime(kb_path)
        return datetime.datetime.fromtimestamp(mtime).strftime("%b %d, %Y")
    except OSError:
        return "unknown"

def log_feedback(msg_idx: int, sentiment: str, content: str) -> None:
    log_path = os.path.join(os.path.dirname(__file__), "documents", "feedback_log.csv")
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.datetime.now().isoformat(), sentiment, content[:300]])

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
if "feedback" not in st.session_state:
    st.session_state.feedback = {}

# ── UI ────────────────────────────────────────────────────────────────────────

# Header — avatar circle + name + subtitle
_b64 = load_avatar_b64()
if _b64:
    _avatar_html = f'<img src="data:image/png;base64,{_b64}" style="width:52px;height:52px;border-radius:50%;object-fit:cover;object-position:center top;border:2px solid #000;flex-shrink:0;"/>'
else:
    _avatar_html = '<div style="width:52px;height:52px;border-radius:50%;background:#000;display:flex;align-items:center;justify-content:center;font-size:1.2rem;font-weight:700;color:#DCED4B;flex-shrink:0;">R</div>'

_kb_date = kb_last_updated()
_hdr_col, _btn_col = st.columns([6, 1])
with _hdr_col:
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:14px;padding:0.5rem 0 0.75rem 0;">
  {_avatar_html}
  <div style="min-width:0;">
    <div style="font-size:1.45rem;font-weight:700;color:#000;letter-spacing:-0.02em;line-height:1.2;">RobBot</div>
    <div style="font-size:0.9rem;color:#444;margin-top:3px;line-height:1.3;">Your Deployment Strategy assistant at PolyAI</div>
    <div style="font-size:0.78rem;color:#777;margin-top:2px;">KB updated {_kb_date}</div>
  </div>
</div>
""", unsafe_allow_html=True)
with _btn_col:
    if st.session_state.get("messages"):
        if st.button("↺ New chat", key="reset", use_container_width=True):
            st.session_state.messages = []
            st.session_state.feedback = {}
            st.session_state.pop("_pending_starter", None)
            st.rerun()
        _export_lines = [f"RobBot Conversation — Exported {datetime.datetime.now().strftime('%b %d, %Y %H:%M')}\n"]
        for _m in st.session_state.messages:
            _label = "You" if _m["role"] == "user" else "RobBot"
            _export_lines.append(f"{_label}:\n{_m['content']}\n")
        _export_text = "\n".join(_export_lines)
        st.download_button(
            "⬇ Export",
            data=_export_text,
            file_name="robbot_conversation.txt",
            mime="text/plain",
            use_container_width=True,
        )
st.markdown('<div style="border-top:1.5px solid rgba(0,0,0,0.15);margin-bottom:0.75rem;"></div>', unsafe_allow_html=True)

# Token limit disclaimer
st.markdown("""
<div style="background:rgba(0,0,0,0.07);border-left:3px solid rgba(0,0,0,0.3);border-radius:0 6px 6px 0;padding:0.45rem 0.75rem;margin-bottom:0.75rem;font-size:0.74rem;color:#555;">
  <strong>Heads up:</strong> RobBot generates up to 512 tokens (~380 words) per reply. Asking for very long or detailed answers may produce cut-off responses — keep questions focused for best results.
</div>
""", unsafe_allow_html=True)

# Render conversation history
_avatar = load_avatar()
_last_assistant_idx = next(
    (_i for _i in range(len(st.session_state.messages) - 1, -1, -1)
     if st.session_state.messages[_i]["role"] == "assistant"),
    -1,
)
for _i, msg in enumerate(st.session_state.messages):
    avatar = _avatar if msg["role"] == "assistant" and _avatar else None
    avatar_kwargs = {"avatar": avatar} if avatar is not None else {}
    with st.chat_message(msg["role"], **avatar_kwargs):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            _existing_fb = st.session_state.feedback.get(_i)
            if _existing_fb:
                st.caption("Helpful ✓" if _existing_fb == "up" else "Not helpful — noted")
            elif _i == _last_assistant_idx:
                _fc1, _fc2, _fc3 = st.columns([1.2, 1.8, 8])
                with _fc1:
                    if st.button("Helpful", key=f"up_{_i}"):
                        st.session_state.feedback[_i] = "up"
                        log_feedback(_i, "up", msg["content"])
                        st.rerun()
                with _fc2:
                    if st.button("Not helpful", key=f"down_{_i}"):
                        st.session_state.feedback[_i] = "down"
                        log_feedback(_i, "down", msg["content"])
                        st.rerun()

# Check limit
_msg_count = len(st.session_state.messages)
_limit_reached = _msg_count >= MAX_MESSAGES
_nearing_limit = not _limit_reached and _msg_count >= 16

if _limit_reached:
    st.markdown("""
<div style="text-align:center;padding:1rem;margin-top:0.5rem;background:#111;border-radius:12px;color:#fff;font-size:0.875rem;">
  You've reached the message limit for this session. Refresh the page to start a new conversation.
</div>
""", unsafe_allow_html=True)
elif _nearing_limit:
    _remaining = MAX_MESSAGES - _msg_count
    st.markdown(f"""
<div style="text-align:center;padding:0.6rem 1rem;margin-top:0.25rem;background:rgba(0,0,0,0.06);border-radius:10px;color:#555;font-size:0.8rem;border:1px solid rgba(0,0,0,0.1);">
  {_remaining} message{'s' if _remaining != 1 else ''} left in this session — wrap up or refresh to start fresh.
</div>
""", unsafe_allow_html=True)

# Starter prompt chips — only shown before the first message
if not st.session_state.messages:
    st.markdown('<div style="font-size:0.65rem;color:#aaa;margin:0.3rem 0 0.2rem 0;">Try asking:</div>', unsafe_allow_html=True)
    _sc = st.columns(2)
    for _si, _sp in enumerate(STARTER_PROMPTS):
        if _sc[_si % 2].button(_sp, key=f"starter_{_si}", use_container_width=True):
            st.session_state["_pending_starter"] = _sp
            st.rerun()

# Chat input — disabled once limit is reached
user_input = st.chat_input(disabled=_limit_reached)

# Pick up a starter chip click if no direct input
if not user_input and "_pending_starter" in st.session_state:
    user_input = st.session_state.pop("_pending_starter")

if user_input and not _limit_reached:
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build the messages list for the API
    kb_text = load_knowledge_base()
    client = get_client()

    # Only send the last 8 messages to keep costs down
    recent_messages = st.session_state.messages[-8:]
    api_messages = [{"role": m["role"], "content": m["content"]} for m in recent_messages]

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
        response_placeholder.markdown("*...*")
        full_response = ""

        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=system_with_kb,
            messages=api_messages,
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
        ) as stream:
            for text in stream.text_stream:
                full_response += text
                response_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
