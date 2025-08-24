from __future__ import annotations

from typing import List

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.func import entrypoint, task
from langgraph.graph import add_messages
from langgraph_supervisor import create_supervisor


def build_app(model: ChatOpenAI):
    # Functional API - Agent 1 (Joke Generator)
    @task
    def generate_joke(messages: List[dict]):
        system_message = {"role": "system", "content": "Write a short coding joke"}
        msg = model.invoke([system_message] + messages)
        return msg

    @entrypoint()
    def joke_agent(state: dict):
        joke = generate_joke(state["messages"]).result()
        messages = add_messages(state["messages"], [joke])
        return {"messages": messages}

    joke_agent.name = "joke_agent"

    # Graph API - Agent 2 (Research Expert)
    def web_search(query: str) -> str:
        """Search the web for information (stubbed)."""
        return (
            "Here are the headcounts for each of the FAANG companies in 2024:\n"
            "1. **Facebook (Meta)**: 67,317 employees.\n"
            "2. **Apple**: 164,000 employees.\n"
            "3. **Amazon**: 1,551,000 employees.\n"
            "4. **Netflix**: 14,000 employees.\n"
            "5. **Google (Alphabet)**: 181,269 employees."
        )

    research_agent = create_react_agent(
        model=model,
        tools=[web_search],
        name="research_expert",
        prompt="You are a world class researcher with access to web search. Do not do any math.",
    )

    workflow = create_supervisor(
        [research_agent, joke_agent],
        model=model,
        prompt=(
            "You are a team supervisor managing a research expert and a joke expert. "
            "For current events, use research_agent. "
            "For any jokes, use joke_agent."
        ),
    )

    return workflow.compile()
