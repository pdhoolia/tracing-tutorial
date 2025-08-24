from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

from tracing_tutorial.supervisor_demo import build_app


class _FallbackModel:
    def __init__(self, model: str = "stub-model") -> None:
        self.model = model

    def invoke(self, messages):
        return AIMessage(content=(
            "Here's a light coding joke (fallback): Why do programmers prefer dark mode? "
            "Because light attracts bugs."
        ))


def main() -> None:
    # Load environment variables from .env file
    load_dotenv()
    
    # Import and initialize tracing BEFORE creating the model
    # This ensures the model creation is also instrumented
    from tracing_tutorial.tracing.backends import configure_tracing
    configure_tracing(os.getenv("OTEL_SERVICE_NAME", "tracing-tutorial"))
    
    # Model selection; default to gpt-4o-mini for cost if available
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if os.getenv("OPENAI_API_KEY"):
        model = ChatOpenAI(model=model_name)
    else:
        # Fallback so the tutorial runs without external creds
        model = _FallbackModel(model=model_name)

    app = build_app(model)

    result = app.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Share a joke to relax and start vibe coding for my next project idea.",
                }
            ]
        }
    )

    for m in result["messages"]:
        try:
            m.pretty_print()
        except Exception:
            print(m)


if __name__ == "__main__":
    main()
