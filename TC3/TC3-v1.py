# TC3/TC3-v1.py
import streamlit as st
import sys
import os

# 将当前 TC3 目录添加到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 现在可以导入 TC3 的模块了
import tc3_folders as all_folders
import tc3_device_status as device_status
import tc3_switch_voltage as switch_voltage

# 创建子选项卡
tab1, tab2, tab3 = st.tabs(["📁 All Folders", "📊 Device Status Summary", "⚡ Switch Voltage Analysis"])

with tab1:
    all_folders.show()

with tab2:
    device_status.show()

with tab3:
    switch_voltage.show()