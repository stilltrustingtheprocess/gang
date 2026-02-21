#!/usr/bin/env python3
"""Deployment Strategy Assistant — Rob virtual assistant."""

import anthropic

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


def main():
    client = anthropic.Anthropic()
    messages = []

    print("Deployment Strategy Assistant (type 'exit' or 'quit' to stop)\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Assistant: Thanks for calling, and I hope you have a great rest of your day. Goodbye.")
            break

        messages.append({"role": "user", "content": user_input})

        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1024,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=messages,
        ) as stream:
            print("Assistant: ", end="", flush=True)
            response_text = ""
            for text in stream.text_stream:
                print(text, end="", flush=True)
                response_text += text
            print()

        messages.append({"role": "assistant", "content": response_text})


if __name__ == "__main__":
    main()
