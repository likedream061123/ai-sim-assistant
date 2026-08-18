import matplotlib

matplotlib.use("Agg")  # 测试强制无 GUI 后端，避免 Windows 上 tkagg 间歇性 TclError
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
