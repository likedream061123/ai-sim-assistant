"""LLM 解析层（多服务商）: 中文工程问题 → 结构化 JSON。

只做"人话→参数"翻译，不做任何计算。数值交给引擎。
LLM 输出结构化 JSON，解析失败或不识别场景抛 ValueError（app 层兜底手动表单）。

多服务商：全部走 OpenAI 兼容 API（OpenAI SDK 指定 base_url 即可），
用户选服务商 + 填对应 key；缺 key 抛 ValueError。
"""
from __future__ import annotations

import json
import os
from openai import OpenAI

SCENARIOS = ("pendulum", "heat", "beam", "vessel", "rc_circuit", "pipe_flow")

# 主流服务商（OpenAI 兼容端点）。model 为默认模型，env 为环境变量名。
PROVIDERS: dict[str, dict] = {
    "deepseek": {
        "label": "DeepSeek", "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat", "env": "DEEPSEEK_API_KEY",
        "hint": "性价比高、中文强，本项目默认",
    },
    "openai": {
        "label": "OpenAI (GPT)", "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini", "env": "OPENAI_API_KEY",
        "hint": "需海外网络",
    },
    "zhipu": {
        "label": "智谱 GLM", "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash", "env": "ZHIPU_API_KEY",
        "hint": "glm-4-flash 有免费额度",
    },
    "dashscope": {
        "label": "通义千问", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus", "env": "DASHSCOPE_API_KEY",
        "hint": "阿里云百炼",
    },
    "moonshot": {
        "label": "Kimi (Moonshot)", "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k", "env": "MOONSHOT_API_KEY",
        "hint": "长文本表现好",
    },
    "siliconflow": {
        "label": "硅基流动", "base_url": "https://api.siliconflow.cn/v1",
        "model": "deepseek-ai/DeepSeek-V3", "env": "SILICONFLOW_API_KEY",
        "hint": "聚合多开源模型",
    },
}


def _client(api_key: str | None = None, provider: str = "deepseek") -> OpenAI:
    """按服务商建 OpenAI 兼容 client。key 优先级: 入参 > 该服务商自己的环境变量。

    各服务商 key 互不通用（不能拿 DeepSeek key 打智谱端点），所以不跨商兜底。
    """
    cfg = PROVIDERS.get(provider) or PROVIDERS["deepseek"]
    key = api_key or os.environ.get(cfg["env"])
    if not key:
        raise ValueError(f"缺少 {cfg['label']} API Key（{cfg['env']}）")
    return OpenAI(api_key=key, base_url=cfg["base_url"])


def parse_query(text: str, api_key: str | None = None, provider: str = "deepseek") -> dict:
    """把一句中文工程问题解析为 {"scenario": ..., "params": ..., "recommended": ...}。

    失败/不识别场景时抛 ValueError。provider 见 PROVIDERS 键。
    """
    sys_prompt = (
        "你是工程计算参数解析器。用户用中文描述一个工程问题，你识别场景并提取参数，只输出 JSON。\n"
        "场景只能是: pendulum(单摆/摆) heat(钢件冷却/热处理/降温) beam(梁/挠度/弯曲) vessel(压力容器/壁厚) "
        "rc_circuit(RC电路/电容/充电) pipe_flow(管道/压降/流量)。\n"
        "判别场景（先看词，再看结构）：\n"
        "- beam：有【梁/简支梁/钢梁/挠度/弯矩/跨度/支承/集中力/荷载】，例：『4米简支梁中点受10kN，最大挠度多少』『钢梁跨中挠度是否超限』『工字钢梁集中力算挠度』\n"
        "- pendulum：有【摆/单摆/钟摆/摆动/周期/摆角】，例：『1米单摆的周期』『摆从30度松手求运动』\n"
        "- heat：有【冷却/降温/热处理/温度场/钢件/淬火/升温】，例：『钢件800度冷到100度要多久』『钢件热处理冷却过程』\n"
        "- vessel：有【压力容器/内压/壁厚/筒体/许用应力/储罐】，例：『内压1MPa容器要多厚』『筒体壁厚校核』\n"
        "- rc_circuit：有【电容/电阻/RC电路/充电/放电/时间常数/电压源】，例：『100微法电容经1千欧电阻充到90%要多久』『RC电路的时间常数』\n"
        "- pipe_flow：有【管道/水管/压降/流速/管径/流量/雷诺数/泵送】，例：『100米50mm钢管20方每小时压降多少』『水管内径5cm流量20m³/h算压降』\n"
        "含『梁』或『挠度』的绝不判 pendulum；含『电容/电阻』的判 rc_circuit；含『管道/管径/流量』的判 pipe_flow。\n"
        "参数用 camelCase，沿用字段名: \n"
        "  pendulum: th0_deg(初始角度度) w0(初始角速度) t_end(时长) m l g c\n"
        "  heat: L(半宽m) T0(初始°C) T_wall(介质°C) T_target(目标°C) alpha\n"
        "  beam: L(梁长m) P(荷载N) a(距左端m) E(弹性模量Pa) I(惯性矩m^4)\n"
        "  vessel: P(内压Pa) D(内径m) sigma_allow(许用应力Pa) t_given(给定壁厚m)\n"
        "  rc_circuit: R(电阻Ω) C(电容F) V_s(源电压V) charge_percent(充电目标百分比%)\n"
        "  pipe_flow: Q(流量m³/s) D(内径m) L(管长m) epsilon rho mu\n"
        "只填用户明确提到的参数，缺的不要编造。单位换算: MPa→Pa 乘1e6，mm→m 除1000，kN→N 乘1000，GPa→Pa 乘1e9，"
        "μF→F 乘1e-6，kΩ→Ω 乘1000，m³/h→m³/s 除3600，L/s→m³/s 除1000。\n"
        "用户没说全关键参数时，对每个缺失参数在 recommended 里给工程常识推荐值（供用户一键采纳）："
        "{\"value\": 数字, \"reason\": \"≤12字理由\"}。参考：钢弹性模量E≈206e9 Pa、Q235许用应力≈1.6e8 Pa、"
        "常见工字钢惯性矩I≈2e-5~1e-4 m⁴、单摆摆长l≈1 m、g=9.81、容器壁厚t≈0.25·P·D/σ、"
        "RC时间常数τ=RC 充到90%约2.3τ、水管经济流速1~3m/s、钢管粗糙度ε≈4.5e-5 m。"
        "只推荐缺失参数，已给的不要推荐。\n"
        '输出格式: {"scenario": "...", "params": {...}, "recommended": {...}}'
    )
    cfg = PROVIDERS.get(provider) or PROVIDERS["deepseek"]
    try:
        resp = _client(api_key, provider).chat.completions.create(
            model=cfg["model"],
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


def explain(scenario: str, data: dict, api_key: str | None = None,
            provider: str = "deepseek", lang: str = "zh") -> str:
    """对计算结果生成 ≤80 字大白话解读（结果区展示）。

    lang 跟随 UI：zh → 中文解读；en → 英文解读（评审/演示默认）。
    """
    cfg = PROVIDERS.get(provider) or PROVIDERS["deepseek"]
    if lang == "en":
        sys_prompt = (
            "You are an engineering simulation assistant. Explain the result of a "
            "calculation in plain English, at most 80 words, for a non-expert user. "
            "Say clearly: what the result is, whether it is reasonable, and what to watch out for."
        )
    else:
        sys_prompt = (
            "你是工程仿真助手，用不超过80字的大白话解释一次计算的结果。"
            "面向非专业用户，说清楚'结果是什么、合理吗、要注意什么'。"
        )
    try:
        resp = _client(api_key, provider).chat.completions.create(
            model=cfg["model"],
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": f"场景={scenario}，关键数据={json.dumps(data, ensure_ascii=False)}"}],
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception:
        return "（AI 解读暂不可用，请直接看数据和图）"
