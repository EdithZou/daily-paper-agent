"""Deep paper analysis with user-configurable LLM prompts."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from src.db import Paper

logger = logging.getLogger(__name__)

# Default analysis sections — user can override all of these in config.yaml
DEFAULT_SECTIONS = [
    {
        "name": "核心问题",
        "prompt": (
            "这篇论文要解决的核心问题是什么？"
            "研究背景和动机是什么？现有方法的局限性在哪里？"
        ),
    },
    {
        "name": "方法与贡献",
        "prompt": (
            "作者提出了什么方法？关键技术创新点是什么？"
            "主要贡献（技术贡献、实验贡献、理论贡献）有哪些？"
        ),
    },
    {
        "name": "方法深度解析",
        "prompt": (
            "对方法进行深入技术解析："
            "核心模块的工作原理是什么？关键设计选择及其理由是什么？"
            "与已有方法（如光流、可变形卷积、Transformer等）的主要区别是什么？"
            "该方法在计算效率、泛化性、可训练性上的优劣如何？"
        ),
    },
    {
        "name": "研究洞见",
        "prompt": (
            "结合以下研究方向，分析这篇文章的洞见和启发：\n"
            "- 视频帧插值（Video Frame Interpolation）\n"
            "- 视频超分辨率（Video Super-Resolution）\n"
            "- 参考帧视频超分辨率（Reference-based VSR）\n"
            "- 稀疏时序上下文（Sparse Temporal Context）\n"
            "- 胶囊内窥镜图像重建（Capsule Endoscopy Reconstruction）\n"
            "- 病理切片WSI流式传输（Telepathology WSI Streaming）\n"
            "- 超声图像重建（Ultrasound Reconstruction）\n\n"
            "请具体说明：哪些技术思路或模块设计可以迁移借鉴？有哪些潜在的实验设计启发？"
        ),
    },
]


def _build_prompt(paper: Paper, sections: list[dict]) -> str:
    authors_str = ", ".join(paper.authors[:5])
    if len(paper.authors) > 5:
        authors_str += f" 等（共{len(paper.authors)}位作者）"

    section_text = "\n\n".join(
        f"### {i + 1}. {s['name']}\n{s['prompt']}"
        for i, s in enumerate(sections)
    )

    kw = "、".join(paper.matched_keywords) if paper.matched_keywords else "无"

    return (
        f"请用中文对以下论文进行深度解读，按照下方章节结构逐一回答，内容尽量具体、深入。\n\n"
        f"---\n"
        f"**标题：** {paper.title}\n"
        f"**作者：** {authors_str}\n"
        f"**发表日期：** {paper.published}\n"
        f"**分类：** {', '.join(paper.categories)}\n"
        f"**链接：** {paper.link}\n"
        f"**匹配关键词：** {kw}\n\n"
        f"**英文摘要：**\n{paper.abstract}\n"
        f"---\n\n"
        f"{section_text}"
    )


def _call_anthropic(prompt: str, model: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "未设置 ANTHROPIC_API_KEY 环境变量。\n"
            "请运行：export ANTHROPIC_API_KEY='sk-ant-...'"
        )
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def analyze_paper(paper: Paper, analysis_config: dict) -> str:
    """Run deep analysis and return Markdown string."""
    provider = analysis_config.get("provider", "anthropic")
    model = analysis_config.get("model", "claude-sonnet-4-6")
    sections = analysis_config.get("sections", DEFAULT_SECTIONS)

    prompt = _build_prompt(paper, sections)

    if provider == "anthropic":
        return _call_anthropic(prompt, model)

    raise ValueError(f"不支持的 provider: {provider}。目前支持：anthropic")


def save_analysis(content: str, paper: Paper, output_dir: str) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # sanitise title for filename (keep first 40 chars, replace spaces)
    safe_title = paper.title[:40].replace(" ", "_").replace("/", "-")
    path = out / f"{paper.arxiv_id}_{safe_title}.md"
    header = (
        f"# 深度解读：{paper.title}\n\n"
        f"- **arXiv ID:** {paper.arxiv_id}\n"
        f"- **链接:** [{paper.link}]({paper.link})\n"
        f"- **发表日期:** {paper.published}\n\n"
        f"---\n\n"
    )
    path.write_text(header + content, encoding="utf-8")
    return path
