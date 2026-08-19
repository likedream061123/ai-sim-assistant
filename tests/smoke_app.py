"""AppTest 冒烟（CI 外单独跑，pytest 不收集）：UI 层关键路径不炸。

用法:  python tests/smoke_app.py

覆盖:
1. 手动模式：计算 → 导出按钮(JSON/CSV) + 计算历史 expander + 载入参数按钮
2. 自然语言：解析(mock LLM) → 结果区导出按钮 + 历史 expander
3. 历史载入 on_click：切到手动模式 + last_parse 写入

注意: 本地 .streamlit/local_keys.json 记住的 provider 决定侧边栏默认服务商，
自然语言分支需给对应 provider 塞一个假 key 才能让「解析并计算」enabled。
"""
import os
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

_HIST = ".streamlit/history.json"


def _main() -> None:
    backup = open(_HIST, "rb").read() if os.path.exists(_HIST) else None

    def cleanup() -> None:
        if backup is not None:
            open(_HIST, "wb").write(backup)
        elif os.path.exists(_HIST):
            os.remove(_HIST)

    try:
        # 1) 手动模式 heat
        at = AppTest.from_file("app.py", default_timeout=60)
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

        # 2) 自然语言（mock agent.llm；provider 用本地记住的默认 → 塞同商 key）
        with patch("agent.llm.parse_query",
                   return_value={"scenario": "beam", "params": {"L": 4, "P": 10000, "a": 1.5}}), \
             patch("agent.llm.explain", return_value="AI 解读（mock）"):
            at2 = AppTest.from_file("app.py", default_timeout=60)
            at2.session_state["api_key_zhipu"] = "sk-test-mock"
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
        print("SMOKE ALL OK")
    finally:
        cleanup()


if __name__ == "__main__":
    _main()
