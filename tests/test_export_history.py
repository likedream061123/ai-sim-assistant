"""结果导出（JSON/CSV）+ 计算历史持久化：纯函数单测。

UI 层（download_button / 历史 expander 是否渲染）由 AppTest 冒烟覆盖（CI 外手动跑）。
这里锁住数据本身：导出必须能解析回结构化数据、heat 曲线不能丢、历史去重/顺序/上限正确。
"""
import csv
import io
import json

import pytest

import app


@pytest.fixture(autouse=True)
def _hist_tmp(tmp_path, monkeypatch):
    """历史文件指到临时路径，避免污染真实 .streamlit/history.json。"""
    monkeypatch.setattr(app, "_HISTORY_FILE", tmp_path / "history.json")
    monkeypatch.setattr(app, "_HISTORY_MAX", 15)


def _solve(scenario):
    """跑一次引擎（跳过画图），拿 data。"""
    return app.ENGINES[scenario].solve({}, plot=False)


@pytest.mark.parametrize("scenario", ["pendulum", "heat", "beam", "vessel"])
def test_export_json_valid_all_scenarios(scenario):
    data = _solve(scenario)["data"]
    payload = json.loads(app._export_json(scenario, {}, data))
    assert payload["scenario"] in app.SCENARIOS          # 中文标签，评委能看懂
    assert "params" in payload and isinstance(payload["params"], dict)
    assert "results" in payload and isinstance(payload["results"], dict)


def test_export_json_heat_includes_curve():
    data = _solve("heat")["data"]
    payload = json.loads(app._export_json("heat", {}, data))
    assert "T_center" in payload["curves"]
    assert "t_arr" in payload["curves"]
    assert len(payload["curves"]["T_center"]) == len(payload["curves"]["t_arr"]) > 0


@pytest.mark.parametrize("scenario", ["pendulum", "heat", "beam", "vessel"])
def test_export_csv_parseable_all_scenarios(scenario):
    data = _solve(scenario)["data"]
    raw = app._export_csv(scenario, {}, data)
    rows = list(csv.reader(io.StringIO(raw)))
    assert rows[0] == ["项目", "值"]
    assert any(r and r[0].startswith("结果") for r in rows)   # 至少一行结果


def test_export_csv_heat_has_curve_table():
    data = _solve("heat")["data"]
    raw = app._export_csv("heat", {}, data)
    rows = [r for r in csv.reader(io.StringIO(raw)) if r]
    assert ["t (s)", "中心温度 (°C)"] in rows                 # 曲线长表段
    assert sum(1 for r in rows if len(r) == 2 and r[0].replace(".", "", 1).isdigit()) >= 2


def test_history_dedup_same_params():
    data = _solve("beam")["data"]
    params = {"L": 4.0, "P": 10000.0, "a": 1.5}
    app._save_history("beam", params, data)
    app._save_history("beam", params, data)
    assert len(app._load_history()) == 1


def test_history_different_params_kept_and_newest_first():
    for i in range(3):
        data = _solve("heat")["data"]
        app._save_history("heat", {"L": 0.1, "T0": 800.0 + i, "T_wall": 20.0, "T_target": 100.0}, data)
    hist = app._load_history()
    assert len(hist) == 3
    assert hist[0]["params"]["T0"] == 802.0   # 最新在前
    assert hist[-1]["params"]["T0"] == 800.0


def test_history_capped_at_max():
    for i in range(app._HISTORY_MAX + 3):
        data = _solve("vessel")["data"]
        app._save_history("vessel", {"P": 1e6, "D": 1.0, "sigma_allow": 100e6, "t_given": 0.005 + i * 1e-9}, data)
    hist = app._load_history()
    assert len(hist) == app._HISTORY_MAX
    # 最早（T0 最小）那条被挤掉：保留的是最新 _HISTORY_MAX 条
    assert hist[0]["params"]["t_given"] > hist[-1]["params"]["t_given"]


def test_history_persists_to_disk_and_no_api_keys():
    data = _solve("beam")["data"]
    app._save_history("beam", {"L": 4.0, "P": 10000.0, "a": 1.5}, data)
    raw = app._HISTORY_FILE.read_text(encoding="utf-8")
    assert "DEEPSEEK" not in raw and "api_key" not in raw      # 绝不落 API key
