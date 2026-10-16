#!/usr/bin/env python3
"""Heuristic anti-AI style checker for WiseInvest drafts."""
from __future__ import annotations

import re
import sys
from pathlib import Path

PHRASE_LIMITS = {
    "不是": 8,
    "而是": 5,
    "真正": 5,
    "这意味着": 1,
    "换句话说": 1,
    "综合来看": 0,
    "这一点非常重要": 0,
    "我对": 3,
}

GENERIC_PHRASES = {
    "机会与风险并存": "正确废话",
    "未来值得持续关注": "正确废话",
    "市场最终会回归基本面": "正确废话",
    "好公司不等于好价格": "高频模板句，需具体化",
    "财报是财报，股价是股价": "用户已明确嫌重复",
    "均线不是估值": "空泛套话",
    "逐个验货": "AI套话",
    "必涨": "确定性收益承诺",
    "稳赚": "确定性收益承诺",
}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_draft.py <draft.md>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        return 2

    text = path.read_text(encoding="utf-8")
    issues: list[str] = []

    for phrase, limit in PHRASE_LIMITS.items():
        count = text.count(phrase)
        if count > limit:
            issues.append(f"“{phrase}”出现{count}次，建议不超过{limit}次")

    for phrase, reason in GENERIC_PHRASES.items():
        if phrase in text:
            issues.append(f"发现“{phrase}”：{reason}")

    marker_count = sum(text.count(m) for m in ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "➡️", "→"))
    if marker_count > 7:
        issues.append(f"符号化分段较多（{marker_count}处）")

    headings = re.findall(r"^#{1,4}\s+", text, flags=re.MULTILINE)
    if len(headings) > 5:
        issues.append(f"小标题较多（{len(headings)}个），可能像研报")

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    short_paras = sum(1 for p in paragraphs if len(p) < 28)
    if paragraphs and short_paras / len(paragraphs) > 0.55:
        issues.append("短段落占比过高，可能出现AI式逐句换行")

    numbered_observations = len(re.findall(r"(?:接下来|重点关注|观察).*?(?:\n|：)", text))
    if numbered_observations >= 2:
        issues.append("存在多组‘接下来观察’式清单，建议压缩")

    if issues:
        print("检查发现：")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("基础去AI化检查通过。仍需人工核验事实与真人语感。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
