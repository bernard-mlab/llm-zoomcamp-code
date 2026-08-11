"""Chainlit chat UI for the arxiv agent.

- @cl.on_message -> arxiv_agent.agent_loop -> render answer with cited arxiv_ids
- Thumbs up/down feedback -> stub for Phase 6 Langfuse
- Sidebar shows last retrieval (mode, #results)
"""
from __future__ import annotations

import re

import chainlit as cl
from arxiv_agent.agent import agent_loop
from arxiv_agent.tools.fetch import fetch_arxiv

ARXIV_ID_PATTERN = re.compile(r"arxiv:(\d{4}\.\d{4,5})")


@cl.on_chat_start
async def init():
    await cl.Message(
        content="Hi! I'm an arXiv research assistant. Ask me about CS.AI/CL/LG papers and I'll search and answer with citations.",
    ).send()


@cl.on_message
async def main(message: cl.Message):
    question = message.content
    msg = cl.Message(content="")
    await msg.send()

    async with cl.Step(name="agent_loop", type="run") as step:
        step.language = "markdown"
        answer = agent_loop(question)
        step.output = answer

    cited_ids = ARXIV_ID_PATTERN.findall(answer)

    msg.content = answer

    if cited_ids:
        elements = []
        for arxiv_id in cited_ids:
            try:
                paper = fetch_arxiv(arxiv_id)
                if paper:
                    title = paper.get("title", "Unknown")
                    summary = paper.get("summary", "")[:200]
                    url = f"https://arxiv.org/abs/{arxiv_id}"
                    elements.append(
                        cl.Text(
                            name=f"[arxiv:{arxiv_id}]",
                            content=f"**{title}**\n\n{summary}...\n\n[Open on arXiv]({url})",
                            display="side",
                        )
                    )
            except Exception:
                pass
        if elements:
            msg.elements = elements

    await msg.update()

    fb = await cl.AskActionMessage(
        actions=[
            cl.Action(name="thumbs_up", value="up", label="👍 Good answer"),
            cl.Action(name="thumbs_down", value="down", label="👎 Needs work"),
        ],
    ).send()

    cl.user_session.set("last_feedback", fb.get("value") if fb else None)