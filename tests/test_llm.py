import pytest
from unittest.mock import patch, MagicMock
from agent import llm


def test_parse_query_pendulum():
    fake = MagicMock()
    fake.choices[0].message.content = '{"scenario":"pendulum","params":{"th0_deg":120}}'
    with patch("agent.llm._client") as m:
        m.return_value.chat.completions.create.return_value = fake
        r = llm.parse_query("一个初始角度120度的单摆")
    assert r["scenario"] == "pendulum"
    assert r["params"]["th0_deg"] == 120


def test_parse_query_unknown_scenario_raises():
    fake = MagicMock()
    fake.choices[0].message.content = '{"scenario":"rocket","params":{}}'
    with patch("agent.llm._client") as m:
        m.return_value.chat.completions.create.return_value = fake
        with pytest.raises(ValueError):
            llm.parse_query("火箭发射")


def test_explain_returns_text():
    fake = MagicMock()
    fake.choices[0].message.content = "结果合理。"
    with patch("agent.llm._client") as m:
        m.return_value.chat.completions.create.return_value = fake
        out = llm.explain("beam", {"v_max": 1e-4})
    assert isinstance(out, str) and len(out) > 0
