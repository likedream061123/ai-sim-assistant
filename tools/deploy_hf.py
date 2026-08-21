"""部署 AI 工程仿真助手到 Hugging Face Spaces（无登录公开访问）。

为什么迁移：Streamlit Community Cloud 2026 起强制所有 app 登录（官方 demo 也 303），
评委无账号打不开作品；HF Spaces 免费、无需登录、原生支持 Streamlit。

用法:
    HF_TOKEN=hf_xxx python tools/deploy_hf.py
    HF_TOKEN=hf_xxx python tools/deploy_hf.py --dry-run   # 仅验证目录组装，不调 API

安全约束:
    - .streamlit/secrets.toml（DeepSeek/SerpApi keys）绝不上传 —— 只上传 config.toml 主题
    - API keys 通过 HF Space Secrets 设置（add_space_secret），不进入 repo 文件
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

from huggingface_hub import HfApi

SPACE_NAME = "ai-sim-assistant"

# 只上传这些路径（含递归目录）；白名单外的文件（tests/、本地数据、secrets）一律排除
# README.md 由脚本生成 Space 专用版（含 YAML frontmatter 指定 python_version）
UPLOAD = {
    "app.py", "i18n.py", "requirements.txt", "PRODUCT.md",
    "agent", "engine", "assets", "docs",
    ".streamlit/config.toml",
}

# 这两个本地文件里可能含 key 明文，绝不进 repo
_NEVER = {".streamlit/secrets.toml", ".streamlit/local_keys.json", ".streamlit/history.json"}

_SPACE_README = """---
title: AI Engineering Simulation Assistant
emoji: 🛠️
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.39.0
app_file: app.py
pinned: false
python_version: "3.11"
---

# AI Engineering Simulation Assistant

Describe an engineering problem in plain English — the AI parses parameters,
scipy computes the real numbers, charts + plain-English interpretation follow.
Six scenarios: pendulum, beam deflection, pressure vessel wall thickness,
quenching heat diffusion, RC charging, pipe flow.

- ⚙️ Computed by scipy — never guessed
- 🌐 Live params via SerpApi (multi-source)
- 🧪 Verified vs MATLAB / ASME
- 🌍 Language auto-detects from your browser (English / 中文)
"""


def main() -> int:
    dry = "--dry-run" in sys.argv
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token and not dry:
        print("缺少 HF_TOKEN 环境变量（生成方式见 https://huggingface.co/settings/tokens）")
        return 1
    if dry:
        print("[dry-run] 无 token，仅验证部署目录组装（不调 API）")

    api = HfApi(token=token or "dry-run-dummy")

    # 1) 创建或获取 Streamlit Space
    if dry:
        print("[1/4] (dry-run) 跳过 create_repo")
        user, repo_id = "dry-run-user", f"dry-run-user/{SPACE_NAME}"
    else:
        who = api.whoami()
        user = who["name"]
        repo_id = f"{user}/{SPACE_NAME}"
        api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="streamlit",
                        exist_ok=True)
        print(f"[1/4] Space 就绪: https://huggingface.co/spaces/{repo_id}")

    # 2) 组装干净的部署目录（白名单复制，排除 secrets）
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "README.md"), "w", encoding="utf-8") as f:
            f.write(_SPACE_README)
        for rel in UPLOAD:
            src = os.path.join(os.getcwd(), rel)
            dst = os.path.join(tmp, rel)
            if os.path.isfile(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            elif os.path.isdir(src):
                shutil.copytree(src, dst,
                                ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
        # 兜底：万一白名单外有敏感文件被 copytree 带进来（不应发生）
        for rel in _NEVER:
            p = os.path.join(tmp, rel)
            if os.path.exists(p):
                os.remove(p)
        print("[2/4] 部署目录组装完成（已排除 secrets）")

        if dry:
            # 列出组装结果供检查（不调 API）
            for root, _, files in os.walk(tmp):
                depth = os.path.relpath(root, tmp)
                for fn in sorted(files):
                    print(f"       {os.path.join(depth, fn) if depth != '.' else fn}")
            print("[dry-run] 验证结束，未上传。")
            return 0

        # 3) 上传全部文件
        api.upload_folder(repo_id=repo_id, repo_type="space", folder_path=tmp)
        print("[3/4] 代码已上传，Space 自动构建中…")

    # 4) 设置 Space Secrets（keys 不进 repo）
    secrets_toml = os.path.join(os.getcwd(), ".streamlit/secrets.toml")
    if os.path.exists(secrets_toml):
        import tomllib
        with open(secrets_toml, "rb") as f:
            data = tomllib.load(f)
        for k, v in data.items():
            api.add_space_secret(repo_id, k, str(v))
            print(f"       secret 已设: {k}")
    else:
        print("       （未找到 .streamlit/secrets.toml，跳过 secrets 设置）")

    print(f"[4/4] 完成。线上地址（无登录可访问）: https://{user}-{SPACE_NAME}.hf.space")
    print(f"      Space 管理页: https://huggingface.co/spaces/{repo_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
