"""Generate Chinese summaries via LLM or template fallback."""
from __future__ import annotations

import logging
import os
from typing import Optional

from src.db import Paper

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
请用中文（约150字）简洁总结以下论文，重点说明：研究问题、方法亮点、主要结果。
请直接输出中文摘要，不需要额外说明。

标题：{title}

摘要（英文）：
{abstract}

匹配到的研究关键词：{keywords}
"""


def _template_summary(paper: Paper) -> str:
    kw_str = "、".join(paper.matched_keywords) if paper.matched_keywords else "（无）"
    abstract_short = paper.abstract[:300] + ("..." if len(paper.abstract) > 300 else "")
    lq = "《"   # 《
    rq = "》"   # 》
    return (
        f"【模板摘要】本文研究{lq}{paper.title}{rq}。"
        f"匹配关键词：{kw_str}。"
        f"英文摘要节选：{abstract_short}"
    )


def _llm_summary(paper: Paper, model: str) -> Optional[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        kw_str = ", ".join(paper.matched_keywords) if paper.matched_keywords else "none"
        prompt = _PROMPT_TEMPLATE.format(
            title=paper.title,
            abstract=paper.abstract[:1500],
            keywords=kw_str,
        )
        msg = client.messages.create(
            model=model,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.warning("LLM summary failed: %s — using template fallback", exc)
        return None


def summarize(paper: Paper, llm_config: dict) -> str:
    provider = llm_config.get("provider", "none")
    model = llm_config.get("model", "claude-haiku-4-5-20251001")

    if provider == "anthropic":
        result = _llm_summary(paper, model)
        if result:
            return result

    return _template_summary(paper)
