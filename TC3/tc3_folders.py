# TC3/tc3_folders.py
import streamlit as st
import pandas as pd
import os

def show():
    # 页面标题样式
    st.markdown("""
        <style>
            .stMarkdown h1 {
                font-size: 20px !important;
            }
            .stMarkdown h2 {
                font-size: 18px !important;
            }
            .stTextInput input {
                font-size: 14px !important;
            }
            .stTextInput label {
                font-size: 14px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1>TC3 - All Folders (Auto from Teams)</h1>", unsafe_allow_html=True)
    st.markdown("<h2>Click folder to open in SharePoint / Teams</h2>", unsafe_allow_html=True)

    # 使用唯一的 key
    search = st.text_input("🔍 Search Samples", placeholder="Search sample name...", key="search_tc3_folders")

    # 读取 Excel
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(current_dir, "..", "data", "TC-Raw data.xlsx")
    excel_path = os.path.normpath(excel_path)

    translation_map = {
        "电压": "Voltage", "电流": "Current", "温度": "Temperature",
        "测试": "Test", "结果": "Result", "数据": "Data",
        "文件夹": "Folder", "文件": "File", "成功": "Success", "失败": "Failed",
    }

    def translate_to_english(text):
        if pd.isna(text) or text == "":
            return ""
        text_str = str(text)
        for cn, en in translation_map.items():
            text_str = text_str.replace(cn, en)
        return text_str

    try:
        if not os.path.exists(excel_path):
            st.error(f"Excel file not found: {excel_path}")
            return

        df = pd.read_excel(excel_path, sheet_name="TC3-Raw data")

        if len(df.columns) < 3:
            st.error(f"Insufficient columns")
            return

        col1_name, col2_name, col3_name = df.columns[0], df.columns[1], df.columns[2]

        if search:
            filtered_df = df[df[col1_name].astype(str).str.contains(search, case=False, na=False)]
        else:
            filtered_df = df.copy()

        st.divider()
        st.write(f"**Found {len(filtered_df)} record(s)**")

        if len(filtered_df) > 0:
            col1, col2 = st.columns([3, 2])
            with col1:
                st.markdown("**Sample**")
            with col2:
                st.markdown("**Description**")
            st.divider()

            for idx, row in filtered_df.iterrows():
                with col1:
                    link_url = row[col3_name]
                    link_text = str(row[col1_name])
                    if pd.notna(link_url) and str(link_url).strip():
                        st.markdown(f"🔗 <a href='{link_url}' target='_blank'>{link_text}</a>", unsafe_allow_html=True)
                    else:
                        st.write(link_text)
                with col2:
                    chinese_text = str(row[col2_name]) if pd.notna(row[col2_name]) else ""
                    st.write(translate_to_english(chinese_text))
        else:
            st.info("No matching samples found")

    except Exception as e:
        st.error(f"Error: {str(e)}")