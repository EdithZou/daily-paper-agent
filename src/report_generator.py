"""Generate daily Markdown report."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from src.db import Paper

_ACTION_MAP = {
    "Must Read": "仔细阅读 (read carefully)",
    "Worth Skim": "略读方法部分 (skim method section)",
    "Low Priority": "暂时忽略 (ignore for now)",
}

_RELEVANCE_NOTE_MAP = {
    "Must Read": "该论文与您的核心研究方向高度吻合。",
    "Worth Skim": "该论文与您的研究方向有一定相关性，值得关注。",
    "Low Priority": "该论文与您的研究方向关联较弱，可暂时跳过。",
}


def _paper_block(paper: Paper, idx: int) -> str:
    authors_str = ", ".join(paper.authors[:5])
    if len(paper.authors) > 5:
        authors_str += f" et al. ({len(paper.authors)} authors)"
    cats = ", ".join(paper.categories)
    kw = ", ".join(paper.matched_keywords) if paper.matched_keywords else "—"
    action = _ACTION_MAP.get(paper.priority, "")
    relevance_note = _RELEVANCE_NOTE_MAP.get(paper.priority, "")

    deep = (
        f"\n<details><summary>📖 深度解读（点击展开）</summary>\n\n"
        f"{paper.deep_analysis}\n\n"
        f"</details>\n"
        if paper.deep_analysis
        else ""
    )

    return f"""\
### {idx}. {paper.title}

| 字段 | 内容 |
|------|------|
| **Authors** | {authors_str} |
| **Link** | [{paper.link}]({paper.link}) |
| **Published** | {paper.published} |
| **Categories** | {cats} |
| **Relevance score** | {paper.relevance_score:.2f} / 10 |
| **Priority** | **{paper.priority}** |
| **Matched keywords** | {kw} |

**中文摘要：** {paper.summary_zh}

**与研究的关联：** {relevance_note}匹配关键词：{kw}。

**建议操作：** {action}
{deep}
---
"""


def generate_report(papers: list[Paper], report_date: date, dry_run: bool = False) -> str:
    must_read = [p for p in papers if p.priority == "Must Read"]
    worth_skim = [p for p in papers if p.priority == "Worth Skim"]
    low_priority = [p for p in papers if p.priority == "Low Priority"]

    lines = [
        f"# Daily Paper Report — {report_date}",
        "",
        f"> Generated on {report_date}{'  *(dry-run — not saved to DB)*' if dry_run else ''}",
        "",
        "## Summary",
        "",
        f"- Total new papers: **{len(papers)}**",
        f"- Must Read: **{len(must_read)}**",
        f"- Worth Skim: **{len(worth_skim)}**",
        f"- Low Priority: **{len(low_priority)}**",
        "",
    ]

    if must_read:
        lines += ["## Must Read", ""]
        for i, p in enumerate(must_read, 1):
            lines.append(_paper_block(p, i))

    if worth_skim:
        lines += ["## Worth Skim", ""]
        for i, p in enumerate(worth_skim, 1):
            lines.append(_paper_block(p, i))

    if low_priority:
        lines += [
            "## Low Priority",
            "",
            "<details><summary>Expand low-priority papers</summary>",
            "",
        ]
        for i, p in enumerate(low_priority, 1):
            lines.append(_paper_block(p, i))
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)


def save_report(content: str, reports_dir: str, report_date: date) -> Path:
    out_dir = Path(reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{report_date}.md"
    path.write_text(content, encoding="utf-8")
    return path
