# TC3/tc3_device_status.py
import streamlit as st
import pandas as pd
import os

def show():
    # 读取 CSV
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "..", "data", "TC3-器件状态统计汇总_v3.0_20260428-3.csv")
    csv_path = os.path.normpath(csv_path)

    try:
        if not os.path.exists(csv_path):
            st.error(f"CSV file not found: {csv_path}")
            st.info("Please update the CSV filename in tc3_device_status.py for TC3")
            return

        # 读取 CSV
        df = pd.read_csv(csv_path, encoding='utf-8')
        df.columns = df.columns.str.strip().str.replace('\ufeff', '')

        # 重命名列（根据实际 CSV 的列名调整）
        rename_map = {
            '项目名': 'Project Name',
            '项目标记': 'Status Flag',
            '电压条件文件夹': 'Voltage Folder',
            '电压条件': 'Voltage Condition',
            'working数量': 'Working',
            'working百分比': 'Working %',
            'short数量': 'Short',
            'short百分比': 'Short %',
            'open数量': 'Open',
            'open百分比': 'Open %',
            'unworking数量': 'Unworking',
            'unworking百分比': 'Unworking %',
            '其他数量': 'Other',
            '其他百分比': 'Other %',
            '总器件数': 'Total Devices',
        }

        existing_rename = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=existing_rename)

        # 转换数量列为整数
        for col in ['Working', 'Short', 'Open', 'Unworking', 'Other', 'Total Devices']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        # 转换百分比列为数值
        for col in ['Working %', 'Short %', 'Open %', 'Unworking %', 'Other %']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('%', '').astype(float)

        # 根据标记列生成显示内容
        def get_total_devices_display(row):
            total_devices = row.get('Total Devices', 0)
            status_flag = str(row.get('Status Flag', '')).strip()

            if status_flag == "BEOL":
                return "Not current design — disregard"

            if status_flag in ["空文件夹", "有TXT无数据"]:
                return f"0 ⚠️ Data not uploaded"

            if status_flag == "压缩包":
                return f"0 ⚠️ Zip file, re-upload required"

            if status_flag == "正常":
                if total_devices == 1024:
                    return str(total_devices)
                else:
                    return f"{total_devices} ⚠️ Some data was not uploaded"

            if total_devices == 1024:
                return str(total_devices)
            else:
                return f"{total_devices} ⚠️ Total Devices ≠ 1024"

        df['Total Devices Display'] = df.apply(get_total_devices_display, axis=1)

        # 格式化百分比显示
        for col in ['Working %', 'Short %', 'Open %', 'Unworking %', 'Other %']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{x:.1f}%")

        # 提示
        st.markdown(
            """
            <div style='text-align: right; font-size: 11px; color: #666; margin-bottom: 10px;'>
            ⚠️ Warning: Data issues (except BEOL which is not current design)
            </div>
            """,
            unsafe_allow_html=True
        )

        # 筛选器
        col1, col2 = st.columns(2)

        with col1:
            project_options = sorted(df['Project Name'].unique().tolist())
            selected_projects = st.multiselect(
                "Project Name",
                options=project_options,
                default=[],
                placeholder="Select projects...",
                key="tc3_project_filter"
            )

        with col2:
            voltage_options = sorted([v for v in df['Voltage Condition'].dropna().unique().tolist() if str(v).strip()])
            selected_voltages = st.multiselect(
                "Voltage Condition",
                options=voltage_options,
                default=[],
                placeholder="Select voltages...",
                key="tc3_voltage_filter"
            )

        # 应用筛选
        filtered_df = df.copy()

        if selected_projects:
            filtered_df = filtered_df[filtered_df['Project Name'].isin(selected_projects)]

        if selected_voltages:
            filtered_df = filtered_df[filtered_df['Voltage Condition'].isin(selected_voltages)]

        # 项目交替颜色
        unique_projects = filtered_df['Project Name'].unique()
        colors = ['#F0F8FF', '#FAFAFA']
        project_color_map = {project: colors[i % len(colors)] for i, project in enumerate(unique_projects)}

        def highlight_projects(row):
            project_name = row['Project Name']
            color = project_color_map.get(project_name, '#FFFFFF')
            return ['background-color: {}'.format(color)] * len(row)

        # 准备最终显示的列
        final_columns = ['Project Name', 'Voltage Condition',
                         'Working', 'Working %', 'Short', 'Short %',
                         'Open', 'Open %', 'Unworking', 'Unworking %',
                         'Total Devices Display']

        final_df = filtered_df[final_columns].copy()
        final_df = final_df.rename(columns={'Total Devices Display': 'Total Devices'})

        # 应用样式
        styled_df = final_df.style.apply(highlight_projects, axis=1)

        # 数值列居中
        center_cols = ['Working', 'Working %', 'Short', 'Short %', 'Open', 'Open %', 'Unworking', 'Unworking %', 'Total Devices']
        existing_center = [col for col in center_cols if col in final_df.columns]
        styled_df = styled_df.set_properties(**{'text-align': 'center'}, subset=existing_center)

        # 表头居中
        styled_df = styled_df.set_table_styles([{
            'selector': 'th',
            'props': [('text-align', 'center')]
        }])

        # 显示表格
        st.dataframe(styled_df, width='stretch', height=500)

    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.info("Please ensure the CSV file has required columns: 项目名, 项目标记, 总器件数")