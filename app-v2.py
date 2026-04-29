import streamlit as st
import importlib.util
import os

# 宽屏模式
st.set_page_config(layout="wide")

# 主页面样式
st.markdown("""
    <style>
        .block-container {
            padding-top: 0.2rem !important;
            padding-bottom: 0rem !important;
        }
        header {
            display: none !important;
        }
        /* 主选项卡样式 */
        .stTabs [data-baseweb="tab"] {
            font-size: 26px !important;
            font-weight: bold !important;
            padding: 15px 35px !important;
        }
    </style>
""", unsafe_allow_html=True)

# 定义加载并执行脚本的函数
def run_script(script_path):
    if not os.path.exists(script_path):
        st.error(f"脚本文件不存在：{script_path}")
        return
    spec = importlib.util.spec_from_file_location("temp_module", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

# 横向选项卡
tab1, tab2, tab3, tab4 = st.tabs(["TC1", "TC2", "TC3", "TC4"])

with tab1:
    run_script("TC1/TC1-v2.py")

with tab2:
    run_script("TC2/TC2-main.py")

with tab3:
    run_script("TC3/TC3-v1.py")

with tab4:
    run_script("TC4/TC4-v1.py")