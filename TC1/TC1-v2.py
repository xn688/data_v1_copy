import streamlit as st
import pandas as pd
import os

# --------------------------
# 页面标题（缩小字号）
# --------------------------
st.markdown("""
    <style>
        /* 只缩小当前页面的标题字号 */
        .stMarkdown h1 {
            font-size: 20px !important;
        }
        .stMarkdown h2 {
            font-size: 18px !important;
        }
        /* 缩小搜索框字体 */
        .stTextInput input {
            font-size: 14px !important;
        }
        .stTextInput label {
            font-size: 14px !important;
        }
    </style>
""", unsafe_allow_html=True)

# 页面标题
st.markdown("<h1>TC1 - All Folders (Auto from Teams)</h1>", unsafe_allow_html=True)
st.markdown("<h2>Click folder to open in SharePoint / Teams</h2>", unsafe_allow_html=True)

# --------------------------
# 搜索框
# --------------------------
search = st.text_input("🔍 Search Samples", placeholder="Search sample name...", key="search_tc1")

# --------------------------
# 读取 Excel 文件（从同一个 Excel 的不同 Sheet 读取）
# --------------------------
# 获取当前脚本所在目录（TC1 文件夹）
current_dir = os.path.dirname(os.path.abspath(__file__))
# 构建 data 文件夹下 Excel 文件的路径
excel_path = os.path.join(current_dir, "..", "data", "TC-Raw data.xlsx")
# 规范化路径
excel_path = os.path.normpath(excel_path)

# 要读取的 Sheet 名称
SHEET_NAME = "TC1-Raw data"

# 中文到英文的翻译映射
translation_map = {
    "电压": "Voltage",
    "电流": "Current",
    "温度": "Temperature",
    "测试": "Test",
    "结果": "Result",
    "数据": "Data",
    "文件夹": "Folder",
    "文件": "File",
}


def translate_to_english(text):
    """将中文文本翻译成英文"""
    if pd.isna(text) or text == "":
        return ""

    text_str = str(text)
    for cn, en in translation_map.items():
        text_str = text_str.replace(cn, en)
    return text_str


try:
    # 检查文件是否存在
    if not os.path.exists(excel_path):
        st.error(f"Excel file not found: {excel_path}")
        st.info("Please ensure the file path is correct: data/TC-Raw data.xlsx")
    else:
        # 读取 Excel 的指定 Sheet
        df = pd.read_excel(excel_path, sheet_name=SHEET_NAME)

        # 检查是否有足够的列
        if len(df.columns) < 3:
            st.error(f"Insufficient columns. Current: {len(df.columns)} columns, need at least 3 columns")
            st.write("Current columns:", df.columns.tolist())
        else:
            # 获取列名（假设第一列、第二列、第三列）
            col1_name = df.columns[0]  # 第一列 - 用于显示和搜索
            col2_name = df.columns[1]  # 第二列 - 额外信息显示
            col3_name = df.columns[2]  # 第三列 - 跳转链接

            # 应用搜索过滤
            if search:
                filtered_df = df[df[col1_name].astype(str).str.contains(search, case=False, na=False)]
            else:
                filtered_df = df.copy()

            st.divider()

            # 显示数据统计
            st.write(f"**Found {len(filtered_df)} record(s)**")

            # 创建两列显示
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
                            st.markdown(f"🔗 <a href='{link_url}' target='_blank'>{link_text}</a>",
                                        unsafe_allow_html=True)
                        else:
                            st.write(link_text)

                    with col2:
                        chinese_text = str(row[col2_name]) if pd.notna(row[col2_name]) else ""
                        english_text = translate_to_english(chinese_text)
                        st.write(english_text)
            else:
                st.info("No matching samples found")

except Exception as e:
    st.error(f"Error reading Excel file: {str(e)}")
    st.info(
        "Please check:\n1. Excel file path is correct\n2. Sheet name is correct\n3. File contains at least 3 columns")