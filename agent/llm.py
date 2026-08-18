"""DeepSeek 解析层: 中文工程问题 → 结构化 JSON。

只做"人话→参数"翻译，不做任何计算。数值交给引擎。
LLM 输出结构化 JSON，解析失败或不识别场景抛 ValueError（app 层兜底手动表单）。
"""
from __future__ import annotations

import json
import os
from openai import OpenAI

SCENARIOS = ("pendulum", "heat", "beam", "vessel")
BASE_URL = "https://api.deepseek.com"


def _client(api_key: str | None = None) -> OpenAI:
    key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("缺少 DEEPSEEK_API_KEY（环境变量或参数）")
    return OpenAI(api_key=key, base_url=BASE_URL)


def parse_query(text: str, api_key: str | None = None) -> dict:
    """把一句中文工程问题解析为 {"scenario": ..., "params": {...}}。

    失败/不识别场景时抛 ValueError。
    """
    sys_prompt = (
        "你是工程计算参数解析器。用户用中文描述一个工程问题，你识别场景并提取参数，只输出 JSON。\n"
        "场景只能是: pendulum(单摆/摆) heat(钢件冷却/热处理/降温) beam(梁/挠度/弯曲) vessel(压力容器/壁厚)。\n"
        "参数用 camelCase，沿用字段名: \n"
        "  pendulum: th0_deg(初始角度度) w0(初始角速度) t_end(时长) m l g c\n"
        "  heat: L(半宽m) T0(初始°C) T_wall(介质°C) T_target(目标°C) alpha\n"
        "  beam: L(梁长m) P(荷载N) a(距左端m) E(弹性模量Pa) I(惯性矩m^4)\n"
        "  vessel: P(内压Pa) D(内径m) sigma_allow(许用应力Pa) t_given(给定壁厚m)\n"
        "只填用户明确提到的参数，缺的不要编造。单位换算: MPa→Pa 乘1e6，mm→m 除1000，kN→N 乘1000，GPa→Pa 乘1e9。\n"
        '输出格式: {"scenario": "...", "params": {...}}'
    )
    try:
        resp = _client(api_key).chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": text}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        data = json.loads(resp.choices[0].message.content)
        if data.get("scenario") not in SCENARIOS:
            raise ValueError(f"场景不识别: {data.get('scenario')}")
        return data
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"解析失败: {e}") from e


def explain(scenario: str, data: dict, api_key: str | None = None) -> str:
    """对计算结果生成 ≤80 字大白话解读（结果区展示）。"""
    sys_prompt = (
        "你是工程仿真助手，用不超过80字的大白话解释一次计算的结果。"
        "面向非专业用户，说清楚'结果是什么、合理吗、要注意什么'。"
    )
    try:
        resp = _client(api_key).chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": f"场景={scenario}，关键数据={json.dumps(data, ensure_ascii=False)}"}],
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception:
        return "（AI 解读暂不可用，请直接看数据和图）"
