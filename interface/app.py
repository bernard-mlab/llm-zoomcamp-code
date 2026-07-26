"""Chainlit chat UI for the arxiv agent. Phase 5.

- renders assistant answers with cited arxiv_id badges
- thumbs up/down -> langfuse score
- sidebar shows last retrieval (mode, #results)
"""
from __future__ import annotations


async def main():  # placeholder signature will become chainlit.on_message
    # Phase 5: import chainlit, on_message -> arxiv_agent.agent_loop -> render
    raise NotImplementedError("Phase 5")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())