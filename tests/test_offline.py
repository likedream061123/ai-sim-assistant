"""离线解析缓存测试 —— 无 key/无网络时的本地规则兜底。

锁两点：
1. 6 个示例问题精确命中，params 用 ASKABLE_PARAMS 白名单键（保证追问判断与 LLM 一致）
2. 关键词兜底只认场景、不填参数；未命中返回 None；短问题不被长示例误抢
"""
from agent import offline_cache


def test_examples_match_scenario_and_params():
    cases = {
        "pendulum": ("摆长1米的单摆，从120度松手，看它的周期和能量", {"th0_deg": 120.0, "l": 1.0}),
        "beam": ("一根4米简支钢梁，距左端1.5米处受10kN集中力，最大挠度多少？",
                 {"L": 4.0, "P": 10000.0, "a": 1.5}),
        "vessel": ("内压1MPa、内径1米的压力容器，许用应力100MPa，需要多厚壁？",
                   {"P": 1e6, "D": 1.0, "sigma_allow": 100e6}),
        "heat": ("半宽0.1米的钢件初始800度，放到20度空气中，中心要多久降到100度？",
                 {"L": 0.1, "T0": 800.0, "T_wall": 20.0, "T_target": 100.0}),
        "rc_circuit": ("100微法电容经1千欧电阻充到12伏，充到90%要多久？",
                       {"R": 1000.0, "C": 100e-6, "V_s": 12.0, "charge_percent": 90.0}),
        "pipe_flow": ("100米长、内径50mm的钢管，20方每小时的水压降多少？",
                      {"Q": 20.0 / 3600.0, "D": 0.05, "L": 100.0}),
    }
    for scenario, (q, params) in cases.items():
        hit = offline_cache.match_offline(q)
        assert hit is not None, f"{scenario} 应命中离线解析"
        assert hit["scenario"] == scenario
        assert hit["params"] == params
        assert hit["source"] == "offline"
        assert hit["recommended"] == {}


def test_example_in_longer_input_still_hits():
    q = "帮我算一下：摆长1米的单摆，从120度松手，看它的周期和能量，顺便考虑阻尼影响"
    hit = offline_cache.match_offline(q)
    assert hit is not None and hit["scenario"] == "pendulum"
    assert hit["params"]["l"] == 1.0


def test_short_question_not_stolen_by_example():
    """短问题「单摆周期」不应被长示例抢到完整解析，走关键词兜底只认场景。"""
    hit = offline_cache.match_offline("一个单摆，看它的周期")
    assert hit is not None and hit["scenario"] == "pendulum"
    assert hit["params"] == {}          # 只认场景，不填参数 → UI 走追问链路


def test_keyword_fallback_scenario_only():
    cases = [
        ("这个水管的压降有多大", "pipe_flow"),
        ("RC电路的时间常数是多少", "rc_circuit"),
        ("钢件淬火要多久冷却", "heat"),
        ("压力容器的壁厚怎么校核", "vessel"),
        ("钢梁跨中挠度是否超限", "beam"),
    ]
    for q, scenario in cases:
        hit = offline_cache.match_offline(q)
        assert hit is not None and hit["scenario"] == scenario, f"{q} → {scenario}"
        assert hit["params"] == {}


def test_no_match_returns_none():
    for q in ("", "   ", "你好", "今天天气不错", "随便聊聊"):
        assert offline_cache.match_offline(q) is None, f"{q!r} 不应命中"
