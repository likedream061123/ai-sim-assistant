import matplotlib

matplotlib.use("Agg")  # 测试强制无 GUI 后端，避免 Windows 上 tkagg 间歇性 TclError
import os
import sys

os.environ.setdefault("SERPAPI_KEY", "test-dummy")  # test_serpapi 占位 key（requests 已 mock，非真调用）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
