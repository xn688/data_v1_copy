# TC4/TC4-v1.py
import streamlit as st
import sys
import os

# 将当前 TC4 目录添加到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入模块
import tc4_folders as all_folders

# 创建子选项卡（只有一个）
tab1 = st.tabs(["📁 All Folders"])

with tab1[0]:
    all_folders.show()