import streamlit as st
import sys
import os

# 将 TC2 目录添加到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入功能模块
import all_folders
import device_status
import switch_voltage

# 创建子选项卡
tab1, tab2, tab3 = st.tabs(["📁 All Folders", "📊 Device Status Summary", "⚡ Switch Voltage Analysis"])

with tab1:
    all_folders.show()

with tab2:
    device_status.show()

with tab3:
    switch_voltage.show()