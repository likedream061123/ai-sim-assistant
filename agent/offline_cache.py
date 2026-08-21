"""离线解析缓存 —— 无网络 / 无 API key 也能演示 AI 解析链路。

LLM 不可用时（无 key / 网络失败 / API 报错），对常见示例问题做本地规则匹配，
返回与 llm.parse_query() 相同结构的 {"scenario", "params", "recommended"}，
并标注 source="offline"。不伪装成真 LLM：只覆盖内置示例问题 + 场景关键词兜底，
UI 明确标注「离线解析模式」。

使用:
    from agent import offline_cache
    hit = offline_cache.match_offline(text)   # dict | None
"""
from __future__ import annotations

# 示例问题 → 完整解析。params 只用 app.ASKABLE_PARAMS 白名单内的键，
# 保证与 LLM 一致的「缺失追问」判断：参数给全 → 直接算；缺 → 追问补齐。
# 每条含中英双语问题（评审/演示默认英文，离线也能跑通），匹配时任一命中即可。
_EXAMPLES: list[tuple[str, tuple[str, str], dict]] = [
    ("pendulum", ("摆长1米的单摆，从120度松手，看它的周期和能量",
                  "A 1 m pendulum released from 120 degrees, show its period and energy"),
     {"th0_deg": 120.0, "l": 1.0}),
    ("beam", ("一根4米简支钢梁，距左端1.5米处受10kN集中力，最大挠度多少？",
              "a 4 m simply supported steel beam with 10 kN at 1.5 m from the left, what is the max deflection?"),
     {"L": 4.0, "P": 10000.0, "a": 1.5}),
    ("vessel", ("内压1MPa、内径1米的压力容器，许用应力100MPa，需要多厚壁？",
                "pressure vessel, 1 MPa internal pressure, 1 m inner diameter, 100 MPa allowable stress, how thick?"),
     {"P": 1e6, "D": 1.0, "sigma_allow": 100e6}),
    ("heat", ("半宽0.1米的钢件初始800度，放到20度空气中，中心要多久降到100度？",
              "steel part of half-width 0.1 m at 800 C cooled in 20 C air, how long until the center reaches 100 C?"),
     {"L": 0.1, "T0": 800.0, "T_wall": 20.0, "T_target": 100.0}),
    ("rc_circuit", ("100微法电容经1千欧电阻充到12伏，充到90%要多久？",
                    "100 uF capacitor charged through 1 k-ohm resistor to 12 V, how long to reach 90%?"),
     {"R": 1000.0, "C": 100e-6, "V_s": 12.0, "charge_percent": 90.0}),
    ("pipe_flow", ("100米长、内径50mm的钢管，20方每小时的水压降多少？",
                   "100 m steel pipe, 50 mm inner diameter, 20 m3/h of water, what is the pressure drop?"),
     {"Q": 20.0 / 3600.0, "D": 0.05, "L": 100.0}),
]

# 场景关键词兜底：只识别场景、不填参数（走追问链路，也能演示）。顺序 = 优先级。
# 中文 + 英文关键词并存：英文评审无 key 输入英文也能命中场景（走追问/示例）。
_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("rc_circuit", ("电容", "电阻", "RC", "充电", "放电", "时间常数",
                    "capacitor", "resistor", "rc circuit", "charge to", "time constant")),
    ("pipe_flow", ("管道", "水管", "压降", "流速", "管径", "流量", "雷诺数", "泵送",
                   "pipe", "pressure drop", "flow rate", "pipeline", "hydraulic")),
    ("heat", ("冷却", "降温", "热处理", "钢件", "温度场", "淬火",
              "cooling", "quench", "heat treatment", "steel part", "temperature")),
    ("pendulum", ("摆", "摆动", "钟摆", "单摆", "周期",
                  "pendulum", "swing", "period", "oscillation")),
    ("vessel", ("压力容器", "内压", "壁厚", "筒体", "储罐", "许用应力",
                "pressure vessel", "internal pressure", "wall thickness", "tank")),
    ("beam", ("梁", "挠度", "弯矩", "简支", "钢梁", "集中力", "弯曲",
              "beam", "deflection", "bending moment", "simply supported", "steel beam")),
]


def _norm(s: str) -> str:
    """去掉空白与常见标点，做模糊匹配。"""
    return "".join(ch for ch in s if not ch.isspace() and ch not in "，。？！、：；")


def match_offline(text: str) -> dict | None:
    """本地规则解析一句工程问题。命中返回离线解析结果，未命中返回 None。"""
    if not text or not text.strip():
        return None
    q = _norm(text)
    if not q:
        return None

    # 1) 示例问题：用户输入包含内置示例（点示例卡或近似问法，中英文任一）→ 返回完整解析。
    #    只做「示例 ⊂ 用户输入」单向，避免用户短问题被长示例误抢。
    q_low = text.lower()
    for scenario, examples, params in _EXAMPLES:
        for example in examples:
            if _norm(example) in q or _norm(example) in q_low:
                return {"scenario": scenario, "params": dict(params),
                        "recommended": {}, "source": "offline"}

    # 2) 场景关键词兜底：只认场景，参数留空 → UI 走「追问补齐」链路。
    #    英文关键词小写匹配（用户输入转小写），中文原样包含匹配。
    for scenario, kws in _KEYWORDS:
        if any(kw in text or kw in q_low for kw in kws):
            return {"scenario": scenario, "params": {},
                    "recommended": {}, "source": "offline"}

    return None
