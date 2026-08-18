"""端到端集成测试：中文 → LLM 解析(mock) → 引擎真算 → AI 解读(mock)。

UI 层（app.py）的 AppTest 冒烟在 CI 外单独跑，这里验证：
1. 统一引擎接口 solve(params) -> {"figures", "data"} 对四场景全通
2. app.DISPLAY 的每个 (key, label, unit) 都真实存在于引擎返回 data
   （缺键 = UI 静默漏显示 = bug，这条防未来改引擎时踩雷）
3. 完整管道: parse_query(mock) → solve → explain(mock)
"""
from unittest.mock import MagicMock, patch

import pytest

import app
from agent import llm


@pytest.fixture(autouse=True)
def _close_figs():
    """每次测试后关闭所有 figure，避免 heat 反复 solve 触发 max_open_warning。"""
    yield
    import matplotlib.pyplot as plt
    plt.close("all")


def _fake_llm(content: str):
    """让 llm._client 返回一个固定 JSON 响应的假客户端。"""
    fake_resp = MagicMock()
    fake_resp.choices[0].message.content = content
    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_resp
    return patch("agent.llm._client", return_value=fake_client)


@pytest.mark.parametrize("scenario", ["pendulum", "heat", "beam", "vessel"])
def test_unified_engine_interface(scenario):
    res = app.ENGINES[scenario].solve({})
    assert isinstance(res, dict) and "figures" in res and "data" in res
    assert isinstance(res["figures"], list) and res["figures"]
    assert isinstance(res["data"], dict)


@pytest.mark.parametrize("scenario", ["pendulum", "heat", "beam", "vessel"])
def test_display_keys_exist_in_engine_data(scenario):
    """UI 数据卡引用的键必须真实存在于引擎返回。"""
    data = app.ENGINES[scenario].solve({})["data"]
    for key, _label, _unit in app.DISPLAY[scenario]:
        assert key in data, f"DISPLAY[{scenario}] 引用了引擎 data 里不存在的键: {key}"


def test_full_pipeline_beam():
    """中文问题 → mock 解析 → 真算 beam → mock 解读，数值与 MATLAB 基准一致。"""
    with _fake_llm('{"scenario": "beam", "params": {"L": 4, "P": 10000, "a": 1.5}}'):
        parsed = llm.parse_query("一根4米简支钢梁，距左端1.5米处承受10kN集中力，最大挠度多少？")
    assert parsed["scenario"] == "beam"
    res = app.ENGINES["beam"].solve(parsed["params"])
    assert abs(res["data"]["v_max"] - 1.2265e-4) < 1e-6  # MATLAB beam_deflection.m 基准
    with _fake_llm("最大挠度0.12毫米，在许用范围之内，梁是安全的。"):
        text = llm.explain("beam", {"v_max": 1.2265e-4})
    assert "梁" in text


def test_no_key_explain_falls_back():
    """无 DEEPSEEK_API_KEY 时 explain 静默降级，不让 UI 崩。"""
    with patch("agent.llm._client", side_effect=ValueError("缺少 key")):
        text = llm.explain("beam", {"v_max": 1e-4})
    assert "暂不可用" in text
