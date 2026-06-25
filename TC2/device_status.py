import streamlit as st
import pandas as pd
import os


def show():
    # 读取 CSV
    current_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(current_dir, "..", "data", "TC2-器件状态统计汇总_v2.3_20260612-1.csv")
    csv_path = os.path.normpath(csv_path)

    # Excel 文件路径（用于读取修改时间）
    excel_path = os.path.join(current_dir, "..", "data", "TC-Raw data & Test Report.xlsx")
    excel_path = os.path.normpath(excel_path)
    sheet_name = "TC2-Raw data & Report"

    try:
        if not os.path.exists(csv_path):
            st.error(f"CSV file not found: {csv_path}")
            return

        # 读取 CSV
        df = pd.read_csv(csv_path, encoding='utf-8')
        df.columns = df.columns.str.strip().str.replace('\ufeff', '')

        # 重命名列
        rename_map = {
            '项目名': 'Sample',
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

        # ========== 从 Excel 读取修改时间 ==========
        sample_modified_map = {}
        if os.path.exists(excel_path):
            try:
                excel_file = pd.ExcelFile(excel_path)
                if sheet_name in excel_file.sheet_names:
                    excel_df = pd.read_excel(excel_path, sheet_name=sheet_name)

                    # 识别 Name 列和时间列
                    name_col = None
                    for col in ['Name', '名称', 'Sample', '样品名称', 'Sample Name']:
                        if col in excel_df.columns:
                            name_col = col
                            break
                    if name_col is None:
                        name_col = excel_df.columns[0]

                    # 识别 Raw修改时间 列
                    time_col = None
                    for col in ['Raw修改时间', 'Raw Modified Time', '原始修改时间', 'Raw Time']:
                        if col in excel_df.columns:
                            time_col = col
                            break

                    if time_col:
                        # 解析时间并提取日期
                        for _, row in excel_df.iterrows():
                            sample_name = str(row[name_col]) if pd.notna(row[name_col]) else ""
                            if sample_name and sample_name != 'nan':
                                time_val = row[time_col] if pd.notna(row[time_col]) else None
                                if time_val:
                                    # 尝试解析日期
                                    try:
                                        if hasattr(time_val, 'strftime'):
                                            date_str = time_val.strftime('%Y-%m-%d')
                                        else:
                                            # 尝试从字符串中提取日期
                                            import re
                                            time_str = str(time_val)
                                            match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', time_str)
                                            if match:
                                                year, month, day = match.groups()
                                                date_str = f"{year}-{int(month):02d}-{int(day):02d}"
                                            else:
                                                # 尝试用 pandas 解析
                                                dt = pd.to_datetime(time_str)
                                                date_str = dt.strftime('%Y-%m-%d')
                                        sample_modified_map[sample_name] = date_str
                                    except:
                                        pass
            except Exception as e:
                st.warning(f"Could not read modification times from Excel: {e}")

        # ========== 添加修改时间列到 df ==========
        df['Sample Modified Date'] = df['Sample'].map(sample_modified_map).fillna('')

        # ========== 获取所有日期用于筛选 ==========
        all_dates = sorted([d for d in df['Sample Modified Date'].unique() if d and d != ''])

        # ========== 根据标记列生成显示内容 ==========
        def get_total_devices_display(row):
            """返回 Total Devices 列显示的内容"""
            total_devices = row.get('Total Devices', 0)
            status_flag = str(row.get('Status Flag', '')).strip()

            # BEOL: 不显示数量，不显示感叹号，只显示文字
            if status_flag == "BEOL":
                return "Not current design — disregard"

            # 空文件夹 或 有TXT无数据: 显示 0 + 感叹号 + Data not uploaded
            if status_flag in ["空文件夹", "有TXT无数据"]:
                return f"0 ⚠️ Data not uploaded"

            # 压缩包: 显示 0 + 感叹号 + Zip file, re-upload required
            if status_flag == "压缩包":
                return f"0 ⚠️ Zip file, re-upload required"

            # 正常: 显示数量，如果总数不等于1024则加警告
            if status_flag == "正常":
                if total_devices == 1024:
                    return str(total_devices)
                else:
                    return f"{total_devices} ⚠️ Some data was not uploaded"

            # 其他未知情况
            if total_devices == 1024:
                return str(total_devices)
            else:
                return f"{total_devices} ⚠️ Total Devices ≠ 1024"

        # 为每一行生成 Total Devices 显示内容
        df['Total Devices Display'] = df.apply(get_total_devices_display, axis=1)

        # 格式化百分比显示
        for col in ['Working %', 'Short %', 'Open %', 'Unworking %', 'Other %']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{x:.1f}%")

        # ========== 筛选器 ==========
        col1, col2, col3 = st.columns(3)

        with col1:
            sample_options = sorted(df['Sample'].unique().tolist())
            selected_samples = st.multiselect(
                "🔍 Sample",
                options=sample_options,
                default=[],
                placeholder="Select samples...",
                key="tc2_device_sample_filter"
            )

        with col2:
            voltage_options = sorted([v for v in df['Voltage Condition'].dropna().unique().tolist() if str(v).strip()])
            selected_voltages = st.multiselect(
                "Voltage Condition",
                options=voltage_options,
                default=[],
                placeholder="Select voltages...",
                key="tc2_device_voltage_filter"
            )

        with col3:
            if all_dates:
                selected_date_range = st.date_input(
                    "📅 Sample Modified",
                    value=(),
                    key="tc2_device_date_filter",
                    help="Select start and end date for Sample modification time"
                )
            else:
                st.info("No dates available")
                selected_date_range = ()

        # ========== 应用筛选 ==========
        filtered_df = df.copy()

        if selected_samples:
            filtered_df = filtered_df[filtered_df['Sample'].isin(selected_samples)]

        if selected_voltages:
            filtered_df = filtered_df[filtered_df['Voltage Condition'].isin(selected_voltages)]

        if selected_date_range and len(selected_date_range) == 2:
            start_date, end_date = selected_date_range
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            filtered_df = filtered_df[
                (filtered_df['Sample Modified Date'] >= start_str) &
                (filtered_df['Sample Modified Date'] <= end_str)
                ]

        # ========== Sample 交替颜色 ==========
        unique_samples = filtered_df['Sample'].unique()
        colors = ['#F0F8FF', '#FAFAFA']
        sample_color_map = {sample: colors[i % len(colors)] for i, sample in enumerate(unique_samples)}

        def highlight_samples(row):
            sample_name = row['Sample']
            color = sample_color_map.get(sample_name, '#FFFFFF')
            return ['background-color: {}'.format(color)] * len(row)

        # ========== 准备最终显示的列（Sample Modified Date 放在最后一列） ==========
        final_columns = ['Sample', 'Voltage Condition',
                         'Working', 'Working %', 'Short', 'Short %',
                         'Open', 'Open %', 'Unworking', 'Unworking %',
                         'Total Devices Display', 'Sample Modified Date']

        final_df = filtered_df[final_columns].copy()
        final_df = final_df.rename(columns={'Total Devices Display': 'Total Devices'})

        # 把日期中的 - 替换为 / 显示
        final_df['Sample Modified Date'] = final_df['Sample Modified Date'].apply(
            lambda x: x.replace('-', '/') if x and isinstance(x, str) else x
        )

        # 应用样式
        styled_df = final_df.style.apply(highlight_samples, axis=1)

        # 数值列居中
        center_cols = ['Working', 'Working %', 'Short', 'Short %', 'Open', 'Open %', 'Unworking', 'Unworking %',
                       'Total Devices', 'Sample Modified Date']
        existing_center = [col for col in center_cols if col in final_df.columns]
        styled_df = styled_df.set_properties(**{'text-align': 'center'}, subset=existing_center)

        # 表头居中
        styled_df = styled_df.set_table_styles([{
            'selector': 'th',
            'props': [('text-align', 'center')]
        }])

        # ========== 显示筛选状态 ==========
        filter_active = []
        if selected_samples:
            filter_active.append(f"Sample: {len(selected_samples)} selected")
        if selected_voltages:
            filter_active.append(f"Voltage: {len(selected_voltages)} selected")
        if selected_date_range and len(selected_date_range) == 2:
            filter_active.append(f"Sample Modified: {selected_date_range[0]} ~ {selected_date_range[1]}")

        if filter_active:
            st.caption(f"🔍 Filtering by: {', '.join(filter_active)}")

        st.write(f"**Found {len(filtered_df)} record(s)**")

        # ========== 显示表格 ==========
        st.dataframe(styled_df, width='stretch', height=500)

    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.info("Please ensure the CSV file has required columns: 项目名, 项目标记, 总器件数")