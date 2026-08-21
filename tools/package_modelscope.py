"""打包魔搭创空间部署 zip（排除 secrets / 本地数据 / 冗余）。

产出: dist/ai-sim-assistant-modelscope.zip
用法: python tools/package_modelscope.py
"""
from __future__ import annotations

import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 上传白名单（含递归目录）。secrets / 本地数据 / 测试 / git 一律排除。
INCLUDE = [
    "app.py", "i18n.py", "requirements.txt", "ms_deploy.json", "README.md", "PRODUCT.md",
    "agent", "engine", "assets",
    ".streamlit/config.toml",
]
# 复制的目录里额外排除的路径片段（防御性）
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", "node_modules"}
EXCLUDE_TAILS = {"secrets.toml", "local_keys.json", "history.json"}


def main() -> int:
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "ai-sim-assistant-modelscope.zip")
    if os.path.exists(out):
        os.remove(out)

    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in INCLUDE:
            src = os.path.join(ROOT, rel)
            if os.path.isfile(src):
                zf.write(src, rel)
                n += 1
            elif os.path.isdir(src):
                for root, dirs, files in os.walk(src):
                    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                    for fn in files:
                        p = os.path.join(root, fn)
                        if fn in EXCLUDE_TAILS:
                            continue
                        arc = os.path.relpath(p, ROOT).replace("\\", "/")
                        zf.write(p, arc)
                        n += 1
    print(f"打包完成: {out} （{n} 个文件）")
    # 列关键文件确认无 secrets
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        leaks = [x for x in names if "secret" in x.lower() or "history.json" in x.lower() or "local_keys" in x.lower()]
        print("关键文件检查:", "全部安全" if not leaks else f"⚠️ 发现泄漏: {leaks}")
        print("文件数:", len(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
