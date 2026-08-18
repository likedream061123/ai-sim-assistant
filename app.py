"""AI 工程仿真助手 —— Streamlit 主入口（编排层）。

架构: 输入 → (可选) LLM 解析 → 引擎计算 → 图+数据+解读+参数溯源。
引擎只管算，本文件只管串。手动表单是解析失败的兜底。

前端设计（taste-skill × impeccable 共同约定）:
- 单 accent 一致性：全站靛蓝 #2F5BFF（工程可信感，非 AI 紫渐变）。
- matplotlib 图用统一主题：同色板、灰网格、一致字号，主线靛蓝 + 对比暖橙。
- 关键数据用 st.metric 呈现（真实数值 + 溯源支撑，非营销假指标）。
- 克制 emoji：只留页面标识 ⚙️，正文/按钮/expander 不用装饰 emoji。
"""
import math
import matplotlib
# 统一图表主题（所有引擎图共享，主色取色板第一条）
matplotlib.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],  # 雅黑自带中英文字形（3.9 无逐字形回退，放第一最稳）
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#D8D8D2",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#ECECE7",
    "grid.linewidth": 0.6,
    "axes.titlesize": 13,
    "axes.titleweight": 600,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.frameon": False,
    "axes.prop_cycle": matplotlib.cycler(color=["#2F5BFF", "#E07B3A", "#2A9D8F", "#7A6FE0"]),
})
import streamlit as st
import engine.pendulum, engine.heat, engine.beam, engine.vessel
from agent import llm

# 轻量布局注入：放宽内容宽度，让图表更舒展
st.markdown(
    """<style>
    .block-container {max-width: 72rem; padding-top: 2.5rem;}
    </style>""",
    unsafe_allow_html=True,
)

SCENARIOS = {
    "单摆 (动力学)": "pendulum",
    "钢件冷却 (热处理)": "heat",
    "钢梁挠度 (结构校核)": "beam",
    "压力容器壁厚 (设计)": "vessel",
}
SCENARIOS_REV = {v: k for k, v in SCENARIOS.items()}
ENGINES = {
    "pendulum": engine.pendulum,
    "heat": engine.heat,
    "beam": engine.beam,
    "vessel": engine.vessel,
}
ENGINE_DEFAULTS = {
    "pendulum": engine.pendulum.DEFAULT_PARAMS,
    "heat": engine.heat.DEFAULT_PARAMS,
    "beam": engine.beam.DEFAULT_PARAMS,
    "vessel": engine.vessel.DEFAULT_PARAMS,
}
# 每场景关键数据卡：(data 键, 中文名, 单位) —— 只展示对用户有意义的键
DISPLAY = {
    "pendulum": [
        ("T_num", "数值周期", "s"),
        ("T0_small", "小角度理论周期", "s"),
        ("T_ratio", "周期比 T/T₀", ""),
        ("E0", "初始能量", "J"),
        ("E_end", "终点能量", "J"),
    ],
    "heat": [
        ("t_center_target", "冷却到目标温度时间", "s"),
        ("steady_reached", "已达稳态", ""),
    ],
    "beam": [
        ("v_max_mm", "最大挠度", "mm"),
        ("x_max", "位置", "m"),
        ("M_max", "最大弯矩", "N·m"),
        ("v_allow", "许用挠度 L/360", "m"),
        ("within_limit", "是否在限内", ""),
    ],
    "vessel": [
        ("t_req_mm", "所需壁厚", "mm"),
        ("sigma_actual", "实际应力", "Pa"),
        ("safe", "是否安全", ""),
    ],
}

st.set_page_config(page_title="AI 工程仿真助手", page_icon="⚙️", layout="wide")
st.title("AI 工程仿真助手")
st.caption("工程问题一句话 → AI 解析 → 数值真算 → 图表 + 大白话解读。数值永不猜。")


def _fmt(v, unit):
    """把标量格式化成人类可读文本。"""
    if isinstance(v, bool):
        return "是" if v else "否"
    if v is None:
        return "—（未计算）"
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return "发散"
        if abs(v) < 1e-3 or abs(v) > 1e6:
            return f"{v:.3e} {unit}".strip()
        return f"{v:.4g} {unit}".strip()
    return f"{v} {unit}".strip()


def render_metrics(scenario: str, data: dict):
    """关键数据卡：每行 3 个 st.metric（真实数值 + 溯源支撑）。"""
    items = [(k, label, unit) for k, label, unit in DISPLAY[scenario] if k in data]
    for i in range(0, len(items), 3):
        row = items[i:i + 3]
        cols = st.columns(len(row))
        for col, (key, label, unit) in zip(cols, row):
            col.metric(label, _fmt(data[key], unit))


def _show_sources(scenario: str, given: dict):
    """参数溯源：哪些是你/AI 给的、哪些用了默认值（透明性卖点）。"""
    defaults = ENGINE_DEFAULTS[scenario]
    rows = []
    for k, v in {**defaults, **(given or {})}.items():
        val = "—" if v is None else f"{v:g}"
        rows.append({"参数": k, "取值": val, "来源": "你给的" if k in given else "已用默认"})
    with st.expander("参数与来源（溯源）", expanded=False):
        st.dataframe(rows, hide_index=True)


def render_result(scenario: str, params: dict, note: str = ""):
    if note:
        st.info(note)
    try:
        res = ENGINES[scenario].solve(params)
    except Exception as e:
        st.error(f"计算失败：{e}")
        return
    # 数值异常兜底（spec §5）：NaN/发散 → 提示参数不合理
    if any(isinstance(v, float) and (math.isnan(v) or math.isinf(v)) for v in res["data"].values()):
        st.error("参数不合理，结果发散（NaN/Inf）——请调整参数后重算。")
        return
    for fig in res["figures"]:
        st.pyplot(fig)
    st.subheader("关键数据")
    render_metrics(scenario, res["data"])
    _show_sources(scenario, params)
    try:
        simple = {k: v for k, v in res["data"].items()
                  if isinstance(v, (int, float, str, bool)) or v is None}
        with st.spinner("生成解读…"):
            text = llm.explain(scenario, simple)
        st.subheader("AI 解读")
        st.info(text)
    except Exception:
        pass


def _fill_example(text: str):
    """示例 chip 回调：在 widget 实例化前（脚本重跑前）把示例填入问题输入框。"""
    st.session_state["q_text"] = text


mode = st.radio("输入方式", ["自然语言（AI 解析）", "手动输入"], horizontal=True)

if mode == "自然语言（AI 解析）":
    st.text_area(
        "描述你的工程问题", key="q_text", height=90,
        placeholder="例：一根4米长的简支钢梁，距左端1.5米处承受10kN集中力，最大挠度多少？",
    )
    st.caption("想快速试？点一个示例直接填入：")
    ex1, ex2, ex3 = st.columns(3)
    ex1.button("钢梁挠度", on_click=_fill_example, args=("一根4米简支钢梁，距左端1.5米处受10kN集中力，最大挠度多少？",))
    ex2.button("容器壁厚", on_click=_fill_example, args=("内压1MPa、内径1米的压力容器，许用应力100MPa，需要多厚壁？",))
    ex3.button("钢件冷却", on_click=_fill_example, args=("半宽0.1米的钢件初始800度，放到20度空气中，中心要多久降到100度？",))
    if st.button("解析并计算", type="primary"):
        try:
            parsed = llm.parse_query(st.session_state.get("q_text", ""))
            name = SCENARIOS_REV.get(parsed["scenario"], parsed["scenario"])
            st.success(f"识别场景：{name}")
            if parsed.get("params"):
                st.write("AI 识别到的参数：", {k: v for k, v in parsed["params"].items()})
            render_result(parsed["scenario"], parsed.get("params", {}))
        except ValueError as e:
            st.warning(f"{e} —— 请改用手动输入。")

else:
    scenario_label = st.selectbox("场景", list(SCENARIOS))
    scenario = SCENARIOS[scenario_label]
    params = {}
    if scenario == "pendulum":
        c1, c2, c3 = st.columns(3)
        params["th0_deg"] = c1.number_input("初始角度 θ₀ (°)", 0.0, 180.0, 120.0)
        params["w0"] = c2.number_input("初始角速度 ω₀ (rad/s)", 0.0, 20.0, 0.0)
        params["t_end"] = c3.number_input("时长 (s)", 1.0, 60.0, 20.0)
    elif scenario == "heat":
        c1, c2, c3 = st.columns(3)
        params["L"] = c1.number_input("钢件半宽 (m)", 0.01, 1.0, 0.1, format="%.3f")
        params["T0"] = c2.number_input("初始温度 (°C)", 100.0, 1500.0, 800.0)
        params["T_wall"] = c3.number_input("介质温度 (°C)", 0.0, 500.0, 20.0)
        params["T_target"] = st.number_input("目标温度 (°C)", 0.0, 1500.0, 100.0)
    elif scenario == "beam":
        c1, c2, c3 = st.columns(3)
        params["L"] = c1.number_input("梁长 (m)", 0.1, 20.0, 4.0)
        params["P"] = c2.number_input("集中荷载 (N)", 100.0, 1e6, 10000.0, format="%.0f")
        params["a"] = c3.number_input("荷载距左端 (m)", 0.1, 19.9, 1.5)
        c4, c5 = st.columns(2)
        params["E"] = c4.number_input("弹性模量 E (Pa)", 1e9, 1e12, 200e9, format="%.3g")
        params["I"] = c5.number_input("惯性矩 I (m4)", 1e-8, 1.0, 5e-4, format="%.3g")
        if st.button("SerpApi 查钢梁典型参数"):
            try:
                from agent import serpapi
                info = serpapi.search("standard steel I-beam elastic modulus moment of inertia")
                st.write("搜索结果参考：", info[:2])
                params.setdefault("E", 200e9)
                params.setdefault("I", 5e-4)
                st.success("已填入典型钢梁参数 E=200 GPa、I=5e-4 m⁴，点下方「计算」生效（可再改）。")
            except Exception as e:
                st.error(f"SerpApi 查询失败：{e}")
    elif scenario == "vessel":
        c1, c2, c3 = st.columns(3)
        params["P"] = c1.number_input("内压 (Pa)", 1e4, 1e8, 1e6, format="%.3g")
        params["D"] = c2.number_input("内径 (m)", 0.1, 10.0, 1.0)
        params["sigma_allow"] = c3.number_input("许用应力 (Pa)", 1e7, 1e9, 100e6, format="%.3g")
    if st.button("计算", type="primary"):
        render_result(scenario, params)
