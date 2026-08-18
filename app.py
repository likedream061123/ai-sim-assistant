"""AI 工程仿真助手 —— Streamlit 主入口（编排层）。"""
import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]  # 雅黑自带中英文字形（3.9 无逐字形回退，放第一最稳）
matplotlib.rcParams["axes.unicode_minus"] = False
import streamlit as st
import engine.pendulum, engine.heat, engine.beam, engine.vessel

SCENARIOS = {
    "单摆 (动力学)": "pendulum",
    "钢件冷却 (热处理)": "heat",
    "钢梁挠度 (结构校核)": "beam",
    "压力容器壁厚 (设计)": "vessel",
}
ENGINES = {
    "pendulum": engine.pendulum,
    "heat": engine.heat,
    "beam": engine.beam,
    "vessel": engine.vessel,
}

st.set_page_config(page_title="AI 工程仿真助手", page_icon="⚙️")
st.title("⚙️ AI 工程仿真助手")
st.caption("工程问题一句话 → AI 解析 → 数值真算 → 图表 + 大白话解读。数值永不猜。")


def render_result(scenario: str, params: dict):
    try:
        res = ENGINES[scenario].solve(params)
    except Exception as e:
        st.error(f"计算失败：{e}")
        return
    for fig in res["figures"]:
        st.pyplot(fig)
    st.subheader("关键数据")
    for k, v in res["data"].items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            st.write(f"- **{k}**: {v}")


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
elif scenario == "vessel":
    c1, c2, c3 = st.columns(3)
    params["P"] = c1.number_input("内压 (Pa)", 1e4, 1e8, 1e6, format="%.3g")
    params["D"] = c2.number_input("内径 (m)", 0.1, 10.0, 1.0)
    params["sigma_allow"] = c3.number_input("许用应力 (Pa)", 1e7, 1e9, 100e6, format="%.3g")

if st.button("计算", type="primary"):
    render_result(scenario, params)
