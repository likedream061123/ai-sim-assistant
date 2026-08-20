"""AppTest 冒烟（CI 外单独跑，pytest 不收集）：UI 层关键路径不炸。

用法:  python tests/smoke_app.py

覆盖:
1. 手动模式：计算 → 导出按钮(JSON/CSV) + 计算历史 expander + 载入参数按钮
2. 自然语言：解析(mock LLM) → 结果区导出按钮 + 历史 expander
3. 历史载入 on_click：切到手动模式 + last_parse 写入

注意: 本地 .streamlit/local_keys.json 记住的 provider 决定侧边栏默认服务商，
自然语言分支需给对应 provider 塞一个假 key 才能让「解析并计算」enabled。
"""
import json
import os
import sys
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
import app
_APP = os.path.join(_ROOT, "app.py")
_HIST = os.path.join(_ROOT, ".streamlit", "history.json")
_KEYS = os.path.join(_ROOT, ".streamlit", "local_keys.json")


def _default_provider() -> str:
    """本地记住的默认服务商（env LLM_PROVIDER 优先 → local_keys.json → deepseek 兜底）。

    与 app._llm_provider() 的优先级一致，确保给 parse_go 塞对 provider 的假 key。
    """
    prov = os.environ.get("LLM_PROVIDER")
    if not prov:
        try:
            if os.path.exists(_KEYS):
                prov = json.loads(open(_KEYS, encoding="utf-8").read()).get("provider")
        except Exception:
            pass
    return prov or "deepseek"


def _main() -> None:
    backup = open(_HIST, "rb").read() if os.path.exists(_HIST) else None

    def cleanup() -> None:
        if backup is not None:
            open(_HIST, "wb").write(backup)
        elif os.path.exists(_HIST):
            os.remove(_HIST)

    try:
        # 1) 手动模式 heat
        at = AppTest.from_file(_APP, default_timeout=60)
        at.session_state["lang"] = "zh"
        at.run()
        assert not at.exception, at.exception
        at.radio(key="input_mode").set_value("手动输入").run()
        at.selectbox(key="scenario_select").set_value("钢件冷却 (热处理)").run()
        at.button(key="calc_go").click().run()
        assert not at.exception, f"手动异常: {at.exception}"
        dls = [d.label for d in at.get("download_button")]
        assert len(dls) >= 2, f"导出按钮: {dls}"
        assert any("计算历史" in e.label for e in at.expander), "缺历史 expander"
        assert any("载入参数" in b.label for b in at.button), "缺载入按钮"
        print("1) 手动模式 ✅ 导出:", dls)

        # 1b) 手动模式 rc_circuit + pipe_flow（新场景表单接线 + 默认值落位）
        for label, key, defval in [
            ("RC 充电 (电学)", "rc_R", 1000.0),
            ("管道压降 (流体)", "pipe_Q", 20.0 / 3600.0),
        ]:
            at_r = AppTest.from_file(_APP, default_timeout=60)
            at_r.session_state["lang"] = "zh"
            at_r.run()
            assert not at_r.exception, at_r.exception
            at_r.radio(key="input_mode").set_value("手动输入").run()
            at_r.selectbox(key="scenario_select").set_value(label).run()
            assert not at_r.exception, f"{label} 表单异常: {at_r.exception}"
            assert abs(at_r.number_input(key=key).value - defval) < 1e-9, \
                f"{label} 默认值异常: {at_r.number_input(key=key).value}"
            print(f"1b) {label} 表单 ✅ 默认 {key}={defval:.4g}")

        # 1c) RC 手动计算出结果卡
        at_r2 = AppTest.from_file(_APP, default_timeout=60)
        at_r2.session_state["lang"] = "zh"
        at_r2.run()
        at_r2.radio(key="input_mode").set_value("手动输入").run()
        at_r2.selectbox(key="scenario_select").set_value("RC 充电 (电学)").run()
        at_r2.button(key="calc_go").click().run()
        assert not at_r2.exception, f"RC 计算异常: {at_r2.exception}"
        assert any("充到目标时间" in m.label for m in at_r2.metric), "RC 结果卡缺数据"
        print("1c) RC 手动计算 ✅")

        # 2) 自然语言（mock agent.llm；provider 用本地记住的默认 → 塞同商 key）
        _prov = _default_provider()
        with patch("agent.llm.parse_query",
                   return_value={"scenario": "beam", "params": {"L": 4, "P": 10000, "a": 1.5}}), \
             patch("agent.llm.explain", return_value="AI 解读（mock）"):
            at2 = AppTest.from_file(_APP, default_timeout=60)
            at2.session_state["lang"] = "zh"
            at2.session_state[f"api_key_{_prov}"] = "sk-test-mock"
            at2.run()
            assert not at2.exception, at2.exception
            at2.text_area(key="q_text").set_value(
                "一根4米简支钢梁，距左端1.5米10kN，最大挠度多少？").run()
            at2.button(key="parse_go").click().run()
            assert not at2.exception, f"自然语言异常: {at2.exception}"
            dls2 = [d.label for d in at2.get("download_button")]
            assert len(dls2) >= 2, f"自然语言导出: {dls2}"
            assert any("计算历史" in e.label for e in at2.expander), "自然语言缺历史"
            print("2) 自然语言 ✅ 导出:", dls2)

        # 3) 历史载入 on_click
        hb = [b for b in at.button if b.label == "载入参数"]
        assert hb, "应存在载入参数按钮"
        hb[0].click().run()
        assert not at.exception, f"载入后异常: {at.exception}"
        assert "last_parse" in at.session_state, "last_parse 未写入"
        assert at.session_state["input_mode"] == "手动输入", "应切到手动模式"
        print("3) 载入历史 ✅ last_parse.scenario =",
              at.session_state["last_parse"]["scenario"])

        # 4) en 模式（提交/演示默认语言）：手动计算 metric label 应为英文
        at_en = AppTest.from_file(_APP, default_timeout=60)
        at_en.session_state["lang"] = "en"
        at_en.run()
        assert not at_en.exception, at_en.exception
        at_en.radio(key="input_mode").set_value("手动输入").run()
        at_en.selectbox(key="scenario_select").set_value("钢梁挠度 (结构校核)").run()
        at_en.button(key="calc_go").click().run()
        assert not at_en.exception, f"en 计算异常: {at_en.exception}"
        en_labels = [m.label for m in at_en.metric]
        assert "Max deflection" in en_labels, f"en metric 标签: {en_labels}"
        assert any("History" in e.label for e in at_en.expander), "en 缺历史 expander"
        print("4) en 模式手动计算 ✅ Max deflection / History")

        # 5) 离线兜底：在线解析抛异常（无 key / 网络不可达）→ 内置离线规则命中示例问题。
        #    注：patch agent.llm.parse_query 抛错（agent.llm 是共享模块，AppTest 下有效），
        #    模拟真实 API 失败分支，同时避免测试把真 key 发去真实调用。
        with patch("agent.llm.parse_query", side_effect=RuntimeError("网络不可达")):
            at3 = AppTest.from_file(_APP, default_timeout=60)
            at3.session_state["lang"] = "zh"
            at3.run()
            assert not at3.exception, at3.exception
            assert not at3.button(key="parse_go").disabled, "解析按钮应可点（离线兜底）"
            at3.text_area(key="q_text").set_value(
                "摆长1米的单摆，从120度松手，看它的周期和能量").run()
            at3.button(key="parse_go").click().run()
            assert not at3.exception, f"离线解析异常: {at3.exception}"
            assert any("离线" in i.value for i in at3.info), "应显示离线解析标注"
            assert any("数值周期" in m.label for m in at3.metric), "离线解析应产出结果卡"
            print("5) 离线解析 ✅ 在线失败回退内置规则仍走通")

        # 6) 极端输入兜底：a==L（荷载落在支点）能穿过 render_result 的 a>L 特判，
        #    由 engine/checks.py 兜住 → 优雅报错不崩
        at4 = AppTest.from_file(_APP, default_timeout=60)
        at4.session_state["lang"] = "zh"
        at4.run()
        assert not at4.exception, at4.exception
        at4.radio(key="input_mode").set_value("手动输入").run()
        at4.selectbox(key="scenario_select").set_value("钢梁挠度 (结构校核)").run()
        at4.number_input(key="beam_L").set_value(0.1).run()
        at4.number_input(key="beam_a").set_value(0.1).run()
        at4.button(key="calc_go").click().run()
        assert not at4.exception, f"非法参数异常: {at4.exception}"
        errs = [e.value for e in at4.error]
        assert any("荷载位置" in m for m in errs), f"应显示载荷越界提示: {errs}"
        print("6) 极端输入兜底 ✅ 非法参数优雅报错不崩")

        # 7) SerpApi 深度：在线查参 → 多源交叉 → 预填 + 来源标注
        #    注：key 走 session_state["api_key_serp"] / st.secrets / env（产品真实路径），
        #    不 patch 模块函数——AppTest 把 app.py 跑在独立命名空间，patch app._serp_key 打不到。
        # 7a) 搜索失败/无共识 → 回退内置典型值（info 提示），不崩。
        #    mock lookup 抛异常走回调的 try/except 安全网，也避免测试把真 key 发去真实 SerpApi。
        with patch("agent.serpapi.lookup_beam_material",
                   side_effect=RuntimeError("API 不可达")):
            at5 = AppTest.from_file(_APP, default_timeout=60)
            at5.session_state["lang"] = "zh"
            at5.run()
            assert not at5.exception, at5.exception
            at5.radio(key="input_mode").set_value("手动输入").run()
            at5.selectbox(key="scenario_select").set_value("钢梁挠度 (结构校核)").run()
            b5 = [b for b in at5.button if "查钢梁典型参数" in b.label]
            assert b5, f"缺查参按钮: {[b.label for b in at5.button]}"
            b5[0].click().run()
            assert not at5.exception, f"查参异常: {at5.exception}"
            infos = [i.value for i in at5.info]
            assert any("内置典型值" in m for m in infos), f"应回退内置值: {infos}"
            print("7a) 查参失败查参 ✅ 回退内置典型值")

        # 7b) 有 key + 搜索结果 → 共识值预填 + 来源一致标注
        with patch("agent.serpapi.lookup_beam_material",
                   return_value={"E": 195e9, "I": None,
                                 "E_sources": [{"title": "Steel Modulus", "link": "https://ex.com/1"}],
                                 "I_sources": []}):
            at6 = AppTest.from_file(_APP, default_timeout=60)
            at6.session_state["lang"] = "zh"
            at6.session_state["api_key_serp"] = "sk-serp-test"
            at6.run()
            assert not at6.exception, at6.exception
            at6.radio(key="input_mode").set_value("手动输入").run()
            at6.selectbox(key="scenario_select").set_value("钢梁挠度 (结构校核)").run()
            b6 = [b for b in at6.button if "查钢梁典型参数" in b.label][0]
            b6.click().run()
            assert not at6.exception, f"查参异常: {at6.exception}"
            assert abs(at6.number_input(key="beam_E").value - 195e9) < 1e3, "E 应被预填为 195 GPa"
            assert abs(at6.number_input(key="beam_I").value - 5e-4) < 1e-12, "I 无共识应回退内置"
            succ = [s.value for s in at6.success]
            assert any("195" in m and "GPa" in m for m in succ), f"应显示 E 来源一致: {succ}"
            print("7b) 有 key 查参 ✅ E 预填 195 GPa + 来源一致标注")
        print("SMOKE ALL OK")
    finally:
        cleanup()


if __name__ == "__main__":
    _main()
