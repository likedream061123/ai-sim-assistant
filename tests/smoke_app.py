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

        # 1d) 验证对照卡：pendulum relation 模式（物理断言 >1）+ beam default_bench 模式
        for label, expect in [
            ("单摆 (动力学)", "物理断言"),      # relation: 周期比 >1 ✓
            ("钢梁挠度 (结构校核)", "验证基准"),  # default_bench: 本结果 vs 基准
        ]:
            at_v = AppTest.from_file(_APP, default_timeout=60)
            at_v.session_state["lang"] = "zh"
            at_v.run()
            assert not at_v.exception, at_v.exception
            at_v.radio(key="input_mode").set_value("手动输入").run()
            at_v.selectbox(key="scenario_select").set_value(label).run()
            at_v.button(key="calc_go").click().run()
            assert not at_v.exception, f"{label} 验证卡异常: {at_v.exception}"
            m_lbls = [m.label for m in at_v.metric]
            assert any(expect in l for l in m_lbls), f"{label} 缺验证卡: {m_lbls}"
            body = "\n".join(x.value for x in at_v.markdown)
            assert "数值已验证" in body, f"{label} 缺验证标题: {body[:200]}"
            print(f"1d) {label} 验证卡 ✅ ({expect})")

        # 1e) 复现链接：?scenario=beam&L=4&P=10000 … 打开 → 自动切手动 + 预填参数
        at_sh = AppTest.from_file(_APP, default_timeout=60)
        at_sh.session_state["lang"] = "zh"
        at_sh.query_params["scenario"] = "beam"
        at_sh.query_params["L"] = "4"
        at_sh.query_params["P"] = "10000"
        at_sh.run()
        assert not at_sh.exception, f"复现链接异常: {at_sh.exception}"
        assert at_sh.session_state["input_mode"] == "手动输入", "应切到手动输入"
        assert at_sh.session_state["scenario_select"] == "钢梁挠度 (结构校核)", \
            f"场景应预选 beam: {at_sh.session_state.get('scenario_select')}"
        assert abs(at_sh.number_input(key="beam_L").value - 4.0) < 1e-9, "beam_L 应预填 4"
        assert abs(at_sh.number_input(key="beam_P").value - 10000.0) < 1e-3, "beam_P 应预填 10000"
        print("1e) 复现链接预填 ✅ ?scenario=beam&L=4&P=10000 → 手动+参数落位")

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

        # 7c) heat 在线查热扩散系数：共识值预填 heat_alpha + 来源一致标注
        #     （用非默认值 1.65e-5，确保断言真正验证「预填生效」而非默认值）
        with patch("agent.serpapi.lookup_heat_material",
                   return_value={"alpha": 1.65e-5,
                                 "alpha_sources": [{"title": "Steel Diffusivity", "link": "https://ex.com/h1"}]}):
            at7 = AppTest.from_file(_APP, default_timeout=60)
            at7.session_state["lang"] = "zh"
            at7.session_state["api_key_serp"] = "sk-serp-test"
            at7.run()
            assert not at7.exception, at7.exception
            at7.radio(key="input_mode").set_value("手动输入").run()
            at7.selectbox(key="scenario_select").set_value("钢件冷却 (热处理)").run()
            b7 = [b for b in at7.button if "查热扩散系数" in b.label]
            assert b7, f"缺 heat 查参按钮: {[b.label for b in at7.button]}"
            b7[0].click().run()
            assert not at7.exception, f"heat 查参异常: {at7.exception}"
            assert abs(at7.number_input(key="heat_alpha").value - 1.65e-5) < 1e-9, "α 应被预填为在线值"
            succ7 = [s.value for s in at7.success]
            assert any("来源一致" in m for m in succ7), f"应显示来源一致: {succ7}"
            print("7c) heat 查热扩散 ✅ α 预填 1.65e-5 + 来源标注")

        # 7d) pipe 在线查管壁粗糙度：共识值预填 pipe_eps（非默认 1e-4）
        with patch("agent.serpapi.lookup_pipe_roughness",
                   return_value={"epsilon": 1e-4,
                                 "epsilon_sources": [{"title": "Roughness", "link": "https://ex.com/p1"}]}):
            at8 = AppTest.from_file(_APP, default_timeout=60)
            at8.session_state["lang"] = "zh"
            at8.session_state["api_key_serp"] = "sk-serp-test"
            at8.run()
            assert not at8.exception, at8.exception
            at8.radio(key="input_mode").set_value("手动输入").run()
            at8.selectbox(key="scenario_select").set_value("管道压降 (流体)").run()
            b8 = [b for b in at8.button if "查管壁粗糙度" in b.label]
            assert b8, f"缺 pipe 查参按钮: {[b.label for b in at8.button]}"
            b8[0].click().run()
            assert not at8.exception, f"pipe 查参异常: {at8.exception}"
            assert abs(at8.number_input(key="pipe_eps").value - 1e-4) < 1e-9, "ε 应被预填为在线值"
            print("7d) pipe 查管壁粗糙度 ✅ ε 预填 1e-4")

        # 7e) rc 在线查常用元件：R/C 都预填
        with patch("agent.serpapi.lookup_rc_components",
                   return_value={"R": 10e3, "C": 100e-6,
                                 "R_sources": [{"title": "Timer", "link": "https://ex.com/r1"}],
                                 "C_sources": [{"title": "Timer", "link": "https://ex.com/r1"}]}):
            at9 = AppTest.from_file(_APP, default_timeout=60)
            at9.session_state["lang"] = "zh"
            at9.session_state["api_key_serp"] = "sk-serp-test"
            at9.run()
            assert not at9.exception, at9.exception
            at9.radio(key="input_mode").set_value("手动输入").run()
            at9.selectbox(key="scenario_select").set_value("RC 充电 (电学)").run()
            b9 = [b for b in at9.button if "查常用元件值" in b.label]
            assert b9, f"缺 rc 查参按钮: {[b.label for b in at9.button]}"
            b9[0].click().run()
            assert not at9.exception, f"rc 查参异常: {at9.exception}"
            assert abs(at9.number_input(key="rc_R").value - 10e3) < 1e-6, "R 应被预填"
            assert abs(at9.number_input(key="rc_C").value - 100e-6) < 1e-12, "C 应被预填"
            print("7e) rc 查常用元件 ✅ R/C 预填")

        # 7f) 新场景查参失败 → 回退内置典型值（info 提示），不崩
        with patch("agent.serpapi.lookup_heat_material",
                   side_effect=RuntimeError("API 不可达")):
            at10 = AppTest.from_file(_APP, default_timeout=60)
            at10.session_state["lang"] = "zh"
            at10.run()
            assert not at10.exception, at10.exception
            at10.radio(key="input_mode").set_value("手动输入").run()
            at10.selectbox(key="scenario_select").set_value("钢件冷却 (热处理)").run()
            b10 = [b for b in at10.button if "查热扩散系数" in b.label][0]
            b10.click().run()
            assert not at10.exception, f"heat 查参失败异常: {at10.exception}"
            infos10 = [i.value for i in at10.info]
            assert any("内置典型值" in m for m in infos10), f"应回退内置值: {infos10}"
            print("7f) 新场景查参失败 ✅ 回退内置典型值")

        # 7g) vessel 在线查材料许用应力：共识值预填 ves_sigma（非默认 150e6）
        with patch("agent.serpapi.lookup_vessel_material",
                   return_value={"sigma_allow": 150e6,
                                 "sigma_allow_sources": [{"title": "A36", "link": "https://ex.com/v1"}]}):
            at11 = AppTest.from_file(_APP, default_timeout=60)
            at11.session_state["lang"] = "zh"
            at11.session_state["api_key_serp"] = "sk-serp-test"
            at11.run()
            assert not at11.exception, at11.exception
            at11.radio(key="input_mode").set_value("手动输入").run()
            at11.selectbox(key="scenario_select").set_value("压力容器壁厚 (设计)").run()
            b11 = [b for b in at11.button if "查材料许用应力" in b.label]
            assert b11, f"缺 vessel 查参按钮: {[b.label for b in at11.button]}"
            b11[0].click().run()
            assert not at11.exception, f"vessel 查参异常: {at11.exception}"
            assert abs(at11.number_input(key="ves_sigma").value - 150e6) < 1e5, "σ_allow 应被预填为在线值"
            succ11 = [s.value for s in at11.success]
            assert any("来源一致" in m for m in succ11), f"应显示来源一致: {succ11}"
            print("7g) vessel 查许用应力 ✅ σ_allow 预填 150 MPa")

        # 7h) heat 材料感知查参：选 aluminum → α 预填铝的热扩散系数（非默认 8.4e-5）
        with patch("agent.serpapi.lookup_heat_material",
                   return_value={"alpha": 8.4e-5,
                                 "alpha_sources": [{"title": "Al Diff", "link": "https://ex.com/al1"}]}):
            at12 = AppTest.from_file(_APP, default_timeout=60)
            at12.session_state["lang"] = "zh"
            at12.session_state["api_key_serp"] = "sk-serp-test"
            at12.run()
            assert not at12.exception, at12.exception
            at12.radio(key="input_mode").set_value("手动输入").run()
            at12.selectbox(key="scenario_select").set_value("钢件冷却 (热处理)").run()
            at12.selectbox(key="heat_material").set_value("aluminum").run()
            b12 = [b for b in at12.button if "查热扩散系数" in b.label]
            assert b12, f"缺 heat 查参按钮: {[b.label for b in at12.button]}"
            b12[0].click().run()
            assert not at12.exception, f"heat 材料查参异常: {at12.exception}"
            assert abs(at12.number_input(key="heat_alpha").value - 8.4e-5) < 1e-9, "α 应按铝材料预填"
            print("7h) heat 材料感知查参 ✅ aluminum α 预填 8.4e-5")

        print("SMOKE ALL OK")
    finally:
        cleanup()


if __name__ == "__main__":
    _main()
