"""AI 工程仿真助手 —— Streamlit 主入口（编排层）。"""
import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]  # 雅黑自带中英文字形（3.9 无逐字形回退，放第一最稳）
matplotlib.rcParams["axes.unicode_minus"] = False
import streamlit as st
import engine.pendulum

st.set_page_config(page_title="AI 工程仿真助手", page_icon="⚙️")
st.title("⚙️ AI 工程仿真助手")
st.caption("工程问题一句话 → AI 解析 → 数值真算 → 图表 + 大白话解读。数值永不猜。")

scenario = "pendulum"  # 暂固定单摆，Task 7 换下拉
c1, c2, c3 = st.columns(3)
th0 = c1.number_input("初始角度 θ0 (°)", 0.0, 180.0, 120.0)
w0 = c2.number_input("初始角速度 ω0 (rad/s)", 0.0, 20.0, 0.0)
t_end = c3.number_input("时长 (s)", 1.0, 60.0, 20.0)

if st.button("计算", type="primary"):
    res = engine.pendulum.solve({"th0_deg": th0, "w0": w0, "t_end": t_end})
    for fig in res["figures"]:
        st.pyplot(fig)
    st.subheader("关键数据")
    d = res["data"]
    st.write(f"- **周期 T（数值）**: {d['T_num']:.3f} s")
    st.write(f"- **小角度理论周期**: {d['T0_small']:.3f} s")
    st.write(f"- **周期比 T/T0**: {d['T_ratio']:.3f}（>1 说明大角度使周期变长）")
    st.write(f"- **初始能量 E0**: {d['E0']:.2f} J → 终点 {d['E_end']:.2f} J")
