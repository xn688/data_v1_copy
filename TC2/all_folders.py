# TC2/all_folders.py
import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime


def show():
    # 紧凑样式 - 只减小页面顶部间距和标题大小，不影响表格
    st.markdown("""
        <style>
            /* 减小整个页面的顶部间距 */
            .main .block-container {
                padding-top: 1rem !important;
                padding-bottom: 0rem !important;
            }
            /* 减小标题字号和间距 */
            .compact-h2 {
                font-size: 18px !important;
                font-weight: 600 !important;
                margin: 0 0 4px 0 !important;
                padding: 0 !important;
            }
            .compact-h3 {
                font-size: 14px !important;
                font-weight: 400 !important;
                margin: 0 0 12px 0 !important;
                padding: 0 !important;
                color: #666 !important;
            }
            /* 减小 divider 间距 */
            hr {
                margin-top: 8px !important;
                margin-bottom: 8px !important;
            }
            /* 保持表格文字大小不变 */
            .compact-table {
                font-size: 14px !important;
            }
            .compact-table td {
                font-size: 14px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 紧凑标题
    st.markdown("<h2 class='compact-h2'>All Folders (Auto from Teams)</h2>", unsafe_allow_html=True)
    st.markdown("<h3 class='compact-h3'>Click folder to open in SharePoint / Teams</h3>", unsafe_allow_html=True)

    # 文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(current_dir, "..", "data", "TC-Raw data & Test Report.xlsx")
    excel_path = os.path.normpath(excel_path)

    sheet_name = "TC2-Raw data & Report"

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

    def split_values(value):
        if pd.isna(value) or value == "":
            return []
        value_str = str(value)
        if ',' in value_str:
            items = [item.strip() for item in value_str.split(',') if item.strip()]
        elif '，' in value_str:
            items = [item.strip() for item in value_str.split('，') if item.strip()]
        else:
            items = [value_str.strip()]
        return items

    def format_multiline_links(names, links):
        if not names:
            return ""
        html_lines = []
        for i, name in enumerate(names):
            if i < len(links) and links[i] and links[i].strip():
                html_lines.append(f"📄 <a href='{links[i]}' target='_blank'>{name}</a>")
            else:
                html_lines.append(f"📄 {name}")
        return "<br>".join(html_lines)

    def parse_time_to_date(time_value):
        """
        解析时间值，提取日期部分（格式：YYYY-MM-DD）
        支持包含时区信息的时间字符串
        """
        if pd.isna(time_value) or time_value == "":
            return None

        time_str = str(time_value).strip()

        if hasattr(time_value, 'strftime'):
            return time_value.strftime('%Y-%m-%d')

        import re
        date_patterns = [
            r'(\d{4})/(\d{1,2})/(\d{1,2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, time_str)
            if match:
                year, month, day = match.groups()
                return f"{year}-{int(month):02d}-{int(day):02d}"

        try:
            dt = pd.to_datetime(time_str)
            return dt.strftime('%Y-%m-%d')
        except:
            pass

        return time_str

    try:
        if not os.path.exists(excel_path):
            st.error(f"Excel file not found: {excel_path}")
            return

        excel_file = pd.ExcelFile(excel_path)
        available_sheets = excel_file.sheet_names

        if sheet_name not in available_sheets:
            st.error(f"Sheet '{sheet_name}' not found")
            st.info(f"Available sheets: {', '.join(available_sheets)}")
            return

        df = pd.read_excel(excel_path, sheet_name=sheet_name)

        # 识别列名
        name_candidates = ['Name', '名称', 'Sample', '样品名称', 'Sample Name']
        name_col = None
        for col in name_candidates:
            if col in df.columns:
                name_col = col
                break
        if name_col is None:
            name_col = df.columns[0]

        desc_candidates = ['Description', '项目类型', 'Type', '描述', 'Project Type']
        desc_col = None
        for col in desc_candidates:
            if col in df.columns:
                desc_col = col
                break
        if desc_col is None:
            desc_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

        folder_candidates = ['Folder Link', '文件夹链接', 'Link', '链接', 'Folder URL']
        folder_col = None
        for col in folder_candidates:
            if col in df.columns:
                folder_col = col
                break
        if folder_col is None:
            folder_col = df.columns[2] if len(df.columns) > 2 else None

        report_name_candidates = ['Report Name', '报告名称', 'Report', '报告']
        report_name_col = None
        for col in report_name_candidates:
            if col in df.columns:
                report_name_col = col
                break
        if report_name_col is None:
            report_name_col = df.columns[3] if len(df.columns) > 3 else None

        report_link_candidates = ['Report Link', '报告链接', 'Report URL', '报告URL', 'Link']
        report_link_col = None
        for col in report_link_candidates:
            if col in df.columns:
                report_link_col = col
                break
        if report_link_col is None:
            report_link_col = df.columns[4] if len(df.columns) > 4 else None

        # ========== 识别修改时间列 ==========
        raw_time_candidates = ['Raw修改时间', 'Raw Modified Time', '原始修改时间', 'Raw Time']
        raw_time_col = None
        for col in raw_time_candidates:
            if col in df.columns:
                raw_time_col = col
                break

        report_time_candidates = ['报告修改时间', 'Report Modified Time', '报告时间', 'Report Time']
        report_time_col = None
        for col in report_time_candidates:
            if col in df.columns:
                report_time_col = col
                break

        # 构建数据行
        data_rows = []
        all_sample_names = set()
        all_descriptions = set()
        all_report_names = set()
        all_raw_dates = set()
        all_report_dates = set()

        for idx, row in df.iterrows():
            name = str(row[name_col]) if pd.notna(row[name_col]) else ""
            if not name or name == 'nan':
                name = ""
            else:
                all_sample_names.add(name)

            description = str(row[desc_col]) if desc_col and pd.notna(row[desc_col]) else ""
            if description and description != 'nan':
                desc_en = translate_to_english(description)
                all_descriptions.add(desc_en)

            folder_link = str(row[folder_col]) if folder_col and pd.notna(row[folder_col]) else ""

            report_names = []
            report_links = []

            if report_name_col and pd.notna(row[report_name_col]):
                report_names = split_values(row[report_name_col])
                for rn in report_names:
                    all_report_names.add(rn)

            if report_link_col and pd.notna(row[report_link_col]):
                report_links = split_values(row[report_link_col])

            raw_date = ""
            if raw_time_col and pd.notna(row[raw_time_col]):
                parsed_date = parse_time_to_date(row[raw_time_col])
                if parsed_date:
                    raw_date = parsed_date
                    all_raw_dates.add(parsed_date)

            report_date = ""
            if report_time_col and pd.notna(row[report_time_col]):
                parsed_date = parse_time_to_date(row[report_time_col])
                if parsed_date:
                    report_date = parsed_date
                    all_report_dates.add(parsed_date)

            if name or report_names:
                data_rows.append({
                    'Name': name,
                    'Description': description,
                    'Folder Link': folder_link,
                    'Report Names': report_names,
                    'Report Links': report_links,
                    'Raw Modified Date': raw_date,
                    'Report Modified Date': report_date
                })

        sorted_raw_dates = sorted(list(all_raw_dates))
        sorted_report_dates = sorted(list(all_report_dates))

        # ========== 搜索区域 - 顺序与表格列一致 ==========
        col_search1, col_search2, col_search3, col_search4, col_search5 = st.columns(5)

        with col_search1:
            selected_samples = st.multiselect(
                "🔍 Sample",
                options=sorted(list(all_sample_names)),
                default=[],
                placeholder="Select...",
                key="tc2_sample_filter"
            )

        with col_search2:
            selected_descriptions = st.multiselect(
                "📝 Description",
                options=sorted(list(all_descriptions)),
                default=[],
                placeholder="Select...",
                key="tc2_desc_filter"
            )

        with col_search3:
            if sorted_raw_dates:
                raw_date_range = st.date_input(
                    "📅 Sample Modified",
                    value=(),
                    key="tc2_raw_date_range",
                    help="Select start and end date for Sample modification time"
                )
            else:
                st.info("No dates")
                raw_date_range = ()

        with col_search4:
            selected_reports = st.multiselect(
                "📄 Report",
                options=sorted(list(all_report_names)),
                default=[],
                placeholder="Select...",
                key="tc2_report_filter"
            )

        with col_search5:
            if sorted_report_dates:
                report_date_range = st.date_input(
                    "📅 Report Modified",
                    value=(),
                    key="tc2_report_date_range",
                    help="Select start and end date for Report modification time"
                )
            else:
                st.info("No dates")
                report_date_range = ()

        # ========== 应用筛选 ==========
        filtered_rows = data_rows

        if selected_samples:
            filtered_rows = [row for row in filtered_rows if row['Name'] in selected_samples]

        if selected_descriptions:
            filtered_rows = [row for row in filtered_rows
                             if translate_to_english(row['Description']) in selected_descriptions]

        if selected_reports:
            filtered_rows = [row for row in filtered_rows
                             if any(report in selected_reports for report in row['Report Names'])]

        if raw_date_range and len(raw_date_range) == 2:
            start_date, end_date = raw_date_range
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            filtered_rows = [row for row in filtered_rows
                             if row['Raw Modified Date'] and start_str <= row['Raw Modified Date'] <= end_str]

        if report_date_range and len(report_date_range) == 2:
            start_date, end_date = report_date_range
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            filtered_rows = [row for row in filtered_rows
                             if row['Report Modified Date'] and start_str <= row['Report Modified Date'] <= end_str]

        st.divider()

        filter_active = []
        if selected_samples:
            filter_active.append(f"Sample: {len(selected_samples)} selected")
        if selected_descriptions:
            filter_active.append(f"Description: {len(selected_descriptions)} selected")
        if raw_date_range and len(raw_date_range) == 2:
            filter_active.append(f"Sample Modified: {raw_date_range[0]} ~ {raw_date_range[1]}")
        if selected_reports:
            filter_active.append(f"Report: {len(selected_reports)} selected")
        if report_date_range and len(report_date_range) == 2:
            filter_active.append(f"Report Modified: {report_date_range[0]} ~ {report_date_range[1]}")

        if filter_active:
            st.caption(f"🔍 Filtering by: {', '.join(filter_active)}")

        st.write(f"**Found {len(filtered_rows)} record(s)**")

        if len(filtered_rows) > 0:
            table_style = """
            <style>
                .compact-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 4px;
                }
                .compact-table th {
                    text-align: left;
                    padding: 8px 8px;
                    background-color: #f0f2f6;
                    font-weight: 600;
                    border-bottom: 1px solid #ddd;
                    white-space: nowrap;
                }
                .compact-table td {
                    padding: 6px 8px;
                    border-bottom: 1px solid #eee;
                    vertical-align: top;
                    line-height: 1.4;
                }
                .compact-table tr:hover {
                    background-color: #f5f5f5;
                }
                .sample-link {
                    text-decoration: none;
                    color: #1f77b4;
                }
                .sample-link:hover {
                    text-decoration: underline;
                }
                .date-cell {
                    font-size: 12px;
                    color: #555;
                    white-space: nowrap;
                }
            </style>
            """
            st.markdown(table_style, unsafe_allow_html=True)

            table_html = '<table class="compact-table"><thead><tr>'
            table_html += '<th style="width: 22%">📁 Sample</th>'
            table_html += '<th style="width: 15%">📝 Description</th>'
            table_html += '<th style="width: 15%">📅 Sample Modified</th>'
            table_html += '<th style="width: 33%">📄 Report</th>'
            table_html += '<th style="width: 15%">📅 Report Modified</th>'
            table_html += '</tr></thead><tbody>'

            for row in filtered_rows:
                table_html += '<tr>'

                if row['Name']:
                    if row['Folder Link'] and row['Folder Link'].strip() and row['Folder Link'] != 'nan':
                        table_html += f'<td>🔗 <a class="sample-link" href="{row["Folder Link"]}" target="_blank">{row["Name"]}</a></td>'
                    else:
                        table_html += f'<td>{row["Name"]}</td>'
                else:
                    table_html += '<td>—</td>'

                if row['Description'] and row['Description'].strip() and row['Description'] != 'nan':
                    desc_text = translate_to_english(row['Description'])
                    table_html += f'<td>{desc_text if desc_text else "—"}</td>'
                else:
                    table_html += '<td>—</td>'

                raw_date_display = row.get('Raw Modified Date', '')
                if raw_date_display and raw_date_display.strip() and raw_date_display != 'nan':
                    display_date = raw_date_display.replace('-', '/')
                    table_html += f'<td class="date-cell">{display_date}</td>'
                else:
                    table_html += '<td class="date-cell">—</td>'

                if row['Report Names'] and len(row['Report Names']) > 0:
                    report_html = format_multiline_links(row['Report Names'], row['Report Links'])
                    table_html += f'<td>{report_html}</td>'
                else:
                    table_html += '<td>—</td>'

                report_date_display = row.get('Report Modified Date', '')
                if report_date_display and report_date_display.strip() and report_date_display != 'nan':
                    display_date = report_date_display.replace('-', '/')
                    table_html += f'<td class="date-cell">{display_date}</td>'
                else:
                    table_html += '<td class="date-cell">—</td>'

                table_html += '</tr>'

            table_html += '</tbody></table>'
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("No matching samples found")

    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())