"""SerpApi 参数搜索: 用真实工程参数辅助计算。

场景: 用户说"钢结构横梁"但没给 E/I —— 用 SerpApi 搜真实材料参数。
M3 深度集成: SerpApi 是产品工作流一环，不是装饰。
"""
from __future__ import annotations

import os
import requests


def search(query: str, api_key: str | None = None, num: int = 3) -> list[dict]:
    """搜索并返回前 num 条结果 [{title, snippet, link}]。缺 key 抛 ValueError。"""
    key = api_key or os.environ.get("SERPAPI_KEY")
    if not key:
        raise ValueError("缺少 SERPAPI_KEY（环境变量或参数）")
    resp = requests.get(
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": query, "api_key": key, "num": num},
        timeout=8,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"title": it.get("title", ""), "snippet": it.get("snippet", ""), "link": it.get("link", "")}
        for it in data.get("organic_results", [])[:num]
    ]
