"""自动语言检测测试 —— 新会话按浏览器 Accept-Language 选初始语言。

评委（英文浏览器）打开即英文，Li（中文浏览器）打开即中文，无需手动切换。
"""
import app


def test_accept_zh_returns_zh():
    assert app._browser_lang_from("zh-CN,zh;q=0.9") == "zh"
    assert app._browser_lang_from("zh-TW,zh;q=0.9,en;q=0.8") == "zh"
    assert app._browser_lang_from("zh-Hans-CN,zh;q=0.9,en;q=0.5") == "zh"


def test_accept_en_or_other_returns_en():
    assert app._browser_lang_from("en-US,en;q=0.9") == "en"
    assert app._browser_lang_from("ja-JP,ja;q=0.9,en;q=0.7") == "en"  # 非中文兜底英文
    assert app._browser_lang_from("de-DE,de;q=0.9,en;q=0.6") == "en"


def test_missing_header_defaults_en():
    assert app._browser_lang_from(None) == "en"
    assert app._browser_lang_from("") == "en"


def test_browser_lang_graceful_without_context():
    """无运行上下文（测试环境）时兜底 en，不抛异常。"""
    assert app._browser_lang() == "en"
