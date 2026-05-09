# TC3/tc3_shmoo.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import re


def load_all_project_data(speed_data_dir):
    """加载所有项目的CSV数据"""
    all_data = {}

    if not os.path.exists(speed_data_dir):
        st.error(f"Speed data directory not found: {speed_data_dir}")
        return all_data

    csv_files = [f for f in os.listdir(speed_data_dir) if f.endswith('.csv') and f.startswith('分组统计_')]

    for csv_file in csv_files:
        project_name = csv_file.replace('分组统计_', '').replace('.csv', '')
        file_path = os.path.join(speed_data_dir, csv_file)

        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            df.columns = df.columns.str.strip()

            column_mapping = {
                '时间': '时间',
                'WN': 'WN',
                'WP': 'WP',
                'RL_中位数': 'RL_中位数',
                'RH_中位数': 'RH_中位数',
                'RL_项目总中位数': 'RL_总中位数',
                'RH_项目总中位数': 'RH_总中位数',
                'RL_MAD': 'RL_MAD',
                'RH_MAD': 'RH_MAD',
                '涉及PT_Row文件夹数': 'PT_Row文件夹数',
                '父路径': '父路径'
            }

            required_raw_cols = ['时间', 'WN', 'WP', 'RL_中位数', 'RH_中位数',
                                 'RL_项目总中位数', 'RH_项目总中位数', 'RL_MAD', 'RH_MAD',
                                 '父路径', '涉及PT_Row文件夹数']

            missing_cols = [col for col in required_raw_cols if col not in df.columns]
            if missing_cols:
                st.warning(f"Project {project_name} missing columns: {missing_cols}")
                continue

            df = df.rename(columns=column_mapping)

            numeric_cols = ['WN', 'WP', 'RL_中位数', 'RH_中位数', 'RL_总中位数', 'RH_总中位数', 'RL_MAD', 'RH_MAD',
                            'PT_Row文件夹数']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            all_data[project_name] = df

        except Exception as e:
            st.error(f"Error loading {csv_file}: {e}")

    return all_data


def extract_subfolder_path(full_path, project_name):
    """从完整路径中提取项目名称之后的完整子路径"""
    try:
        if pd.isna(full_path) or not full_path:
            return ""
        full_path = str(full_path)
        pattern = rf'.*[\\/]TC3[\\/]{re.escape(project_name)}[\\/]?(.*)$'
        match = re.search(pattern, full_path, re.IGNORECASE)
        if match:
            sub_path = match.group(1)
            sub_path = sub_path.rstrip('\\/')
            return sub_path if sub_path else ""
        return ""
    except:
        return ""


def convert_time_to_ns(time_str):
    """将时间字符串转换为纳秒数值用于排序"""
    if pd.isna(time_str):
        return 0
    time_str = str(time_str).strip().lower()

    import re
    match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zμ]*)', time_str)
    if not match:
        return 0

    value = float(match.group(1))
    unit = match.group(2)

    if unit in ['ns', 'nanosecond', 'nanoseconds']:
        return value
    elif unit in ['us', 'μs', 'microsecond', 'microseconds']:
        return value * 1000
    elif unit in ['ms', 'millisecond', 'milliseconds']:
        return value * 1000000
    elif unit in ['s', 'sec', 'second', 'seconds']:
        return value * 1000000000
    else:
        return value


def prepare_shmoo_data(df, value_col, total_median_col, mad_col, threshold_multiplier):
    """准备Shmoo图数据"""
    if value_col == 'RL_中位数':
        x_col, y_col = '时间', 'WN'
        y_label_display = 'Vreset (V)'
    else:
        x_col, y_col = '时间', 'WP'
        y_label_display = 'Vset (V)'

    x_unique = df[x_col].dropna().unique()
    x_with_keys = [(x, convert_time_to_ns(x)) for x in x_unique]
    x_sorted = sorted(x_with_keys, key=lambda t: t[1])
    x_values = [t[0] for t in x_sorted]

    y_values = sorted(df[y_col].dropna().unique())

    total_median = df[total_median_col].iloc[0] if not df[total_median_col].isna().all() else 0
    mad_val = df[mad_col].iloc[0] if not df[mad_col].isna().all() else 1

    if pd.isna(total_median):
        total_median = 0
    if pd.isna(mad_val) or mad_val == 0:
        mad_val = 1

    lower_bound = total_median - threshold_multiplier * mad_val
    upper_bound = total_median + threshold_multiplier * mad_val

    cell_data = {}
    for _, row in df.iterrows():
        x_val = row[x_col]
        y_val = row[y_col]

        if pd.isna(x_val) or pd.isna(y_val):
            continue

        key = (x_val, y_val)

        med_val = row[value_col]
        if pd.isna(med_val):
            med_val = 0

        full_path = row['父路径'] if pd.notna(row['父路径']) else ""
        row_count = row['PT_Row文件夹数'] if pd.notna(row['PT_Row文件夹数']) else 32

        is_pass = lower_bound <= med_val <= upper_bound

        if key in cell_data:
            cell_data[key].append({
                'value': med_val,
                'is_pass': is_pass,
                'full_path': full_path,
                'row_count': row_count
            })
        else:
            cell_data[key] = [{
                'value': med_val,
                'is_pass': is_pass,
                'full_path': full_path,
                'row_count': row_count
            }]

    return x_values, y_values, cell_data, lower_bound, upper_bound, total_median, mad_val, y_label_display


def create_shmoo_figure(df, value_col, total_median_col, mad_col, threshold_multiplier, title, project_name,
                        shmoo_type):
    """创建单个Shmoo图 - 支持多行数据水平分割显示（横向划分/上下堆叠）"""

    x_values, y_values, cell_data, lower_bound, upper_bound, total_median, mad_val, y_label_display = prepare_shmoo_data(
        df, value_col, total_median_col, mad_col, threshold_multiplier
    )

    if not x_values or not y_values:
        return None, None

    n_x = len(x_values)
    n_y = len(y_values)

    # 构建颜色矩阵和文本矩阵
    z_matrix = []
    text_matrix = []
    hover_matrix = []

    for y in y_values:
        z_row = []
        text_row = []
        hover_row = []
        for x in x_values:
            key = (x, y)
            if key in cell_data:
                items = cell_data[key]

                # 构建悬停文本（包含所有子项）
                hover_lines = []
                for idx, item in enumerate(items, 1):
                    sub_path = extract_subfolder_path(item['full_path'], project_name)
                    status = "Pass" if item['is_pass'] else "Fail"
                    hover_lines.append(
                        f"[{idx}] {sub_path} | Value: {item['value']:.0f} | {status} | Row Count: {item['row_count']}")
                hover_text = "<br>".join(hover_lines)

                if len(items) == 1:
                    # 单行数据
                    item = items[0]
                    z_matrix_val = 1 if item['is_pass'] else 2
                    text_val = f"{item['value']:.0f}"
                else:
                    # 多行数据：全部pass才算绿色，否则红色
                    all_pass = all(item['is_pass'] for item in items)
                    z_matrix_val = 1 if all_pass else 2
                    # 显示多行数值，前面加上序号
                    text_val = "<br>".join([f"{idx}: {item['value']:.0f}" for idx, item in enumerate(items, 1)])

                z_row.append(z_matrix_val)
                text_row.append(text_val)
                hover_row.append(hover_text)
            else:
                z_row.append(np.nan)
                text_row.append("")
                hover_row.append("")
        z_matrix.append(z_row)
        text_matrix.append(text_row)
        hover_matrix.append(hover_row)

    # 创建图形
    fig = go.Figure()

    # 添加热图层（所有格子都有悬停信息）
    fig.add_trace(go.Heatmap(
        z=z_matrix,
        x=list(range(n_x)),
        y=list(range(n_y)),
        text=text_matrix,
        texttemplate='%{text}',
        textfont={"size": 11, "family": "monospace"},
        hovertext=hover_matrix,
        hoverinfo='text',
        colorscale=[
            [0, '#2e7d32'],  # 绿色 - pass
            [1, '#c62828']  # 红色 - fail
        ],
        showscale=False,
        zmin=1,
        zmax=2,
        connectgaps=False,
        hovertemplate='%{hovertext}<extra></extra>'
    ))

    # 对于多行数据的格子，添加水平分割的子矩形（覆盖在热图层上）
    for y_idx, y in enumerate(y_values):
        for x_idx, x in enumerate(x_values):
            key = (x, y)
            if key not in cell_data:
                continue
            items = cell_data[key]
            n_items = len(items)

            if n_items > 1:
                # 多行数据 - 添加水平划分的子矩形
                sub_height = 1.0 / n_items
                for i, item in enumerate(items):
                    color_hex = '#2e7d32' if item['is_pass'] else '#c62828'
                    y_offset = i * sub_height

                    x0 = x_idx - 0.5
                    x1 = x_idx + 0.5
                    y0 = y_idx - 0.5 + y_offset
                    y1 = y0 + sub_height

                    # 添加彩色矩形（跳过悬停，让热图层统一处理）
                    fig.add_trace(go.Scatter(
                        x=[x0, x1, x1, x0, x0],
                        y=[y0, y0, y1, y1, y0],
                        mode='lines',
                        fill='toself',
                        line=dict(width=0.5, color='white'),
                        fillcolor=color_hex,
                        opacity=1.0,
                        name='',
                        showlegend=False,
                        hoverinfo='skip'
                    ))

                    # 添加文本标注，前面加上序号
                    fig.add_annotation(
                        x=x_idx,
                        y=(y0 + y1) / 2,
                        text=f"{i + 1}: {item['value']:.0f}",
                        showarrow=False,
                        font=dict(size=10, color='white'),
                        xanchor='center',
                        yanchor='middle'
                    )

    # 添加网格线（宽度1.5）
    shapes = []
    # 垂直网格线
    for i in range(n_x + 1):
        shapes.append(dict(
            type="line", xref="x", yref="y",
            x0=i - 0.5, y0=-0.5, x1=i - 0.5, y1=n_y - 0.5,
            line=dict(color="black", width=1.5)
        ))
    # 水平网格线
    for j in range(n_y + 1):
        shapes.append(dict(
            type="line", xref="x", yref="y",
            x0=-0.5, y0=j - 0.5, x1=n_x - 0.5, y1=j - 0.5,
            line=dict(color="black", width=1.5)
        ))

    # 设置坐标轴
    fig.update_xaxes(
        title="Time",
        title_font=dict(size=14),
        tickfont=dict(size=12),
        tickangle=45,
        side='bottom',
        tickmode='array',
        tickvals=list(range(n_x)),
        ticktext=[str(x) for x in x_values],
        range=[-0.5, n_x - 0.5]
    )

    fig.update_yaxes(
        title=y_label_display,
        title_font=dict(size=14),
        tickfont=dict(size=12),
        tickmode='array',
        tickvals=list(range(n_y)),
        ticktext=[str(y) for y in y_values],
        range=[-0.5, n_y - 0.5],
        scaleanchor="x",
        scaleratio=1
    )

    fig.update_layout(
        title=f"<b>{title}</b>",
        height=500,
        width=None,
        xaxis=dict(
            gridcolor='lightgray',
            linecolor='black',
            linewidth=1,
            side='bottom'
        ),
        yaxis=dict(
            gridcolor='lightgray',
            linecolor='black',
            linewidth=1
        ),
        margin=dict(l=80, r=50, t=60, b=120),
        shapes=shapes,
        plot_bgcolor='white'
    )

    # 收集详细信息用于表格
    details_list = []
    for y_idx, y in enumerate(y_values):
        for x_idx, x in enumerate(x_values):
            key = (x, y)
            if key in cell_data:
                for item in cell_data[key]:
                    sub_path = extract_subfolder_path(item['full_path'], project_name)
                    detail_row = {
                        'Time': x,
                        'Subfolder': sub_path,
                        'Row Count': item['row_count'],
                    }
                    if shmoo_type == 'Vreset':
                        detail_row['Vreset'] = y
                        detail_row['RL_Value'] = f"{item['value']:.0f}"
                        detail_row['RL_Status'] = 'Pass' if item['is_pass'] else 'Fail'
                    else:
                        detail_row['Vset'] = y
                        detail_row['RH_Value'] = f"{item['value']:.0f}"
                        detail_row['RH_Status'] = 'Pass' if item['is_pass'] else 'Fail'
                    details_list.append(detail_row)

    details_df = pd.DataFrame(details_list) if details_list else pd.DataFrame()
    return fig, details_df


def show():
    """主显示函数"""

    current_dir = os.path.dirname(os.path.abspath(__file__))
    speed_data_dir = os.path.join(current_dir, "..", "data", "speed data")
    speed_data_dir = os.path.normpath(speed_data_dir)

    st.markdown("<h3 style='font-size: 20px; margin-bottom: 5px;'>📈 Shmoo Plot - Vset & Vreset</h3>",
                unsafe_allow_html=True)

    all_data = load_all_project_data(speed_data_dir)

    if not all_data:
        st.warning("No project data found. Please ensure CSV files are in 'data/speed data' folder")
        st.info(
            "Required columns: 时间, WN, WP, RL_中位数, RH_中位数, RL_项目总中位数, RH_项目总中位数, RL_MAD, RH_MAD, 父路径, 涉及PT_Row文件夹数")
        return

    st.markdown("---")

    selected_projects = st.multiselect(
        "Select Project(s)",
        options=sorted(all_data.keys()),
        default=[],
        placeholder="Choose projects to display...",
        key="shmoo_project_select"
    )

    if not selected_projects:
        st.info("👈 Please select one or more projects to display Shmoo plots.")
        return

    col_multiplier, col_formula = st.columns([1, 2])

    with col_multiplier:
        threshold_multiplier = st.number_input(
            "MAD Multiplier (±)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            key="multiplier_input",
            help="MAD = Median Absolute Deviation"
        )

    with col_formula:
        st.markdown(f"""
        <div style="margin-top: 25px;">
            <div style="font-family: monospace; font-size: 15px; font-weight: 500; background-color: #e8eaed; padding: 6px 14px; border-radius: 20px; display: inline-block; color: #1a1a1a;">
                📐 Pass/Fail Criteria: Vreset/Vset Overall Median ± <span style="font-size: 18px; font-weight: bold; color: #1a73e8; background-color: #ffffff; padding: 2px 8px; border-radius: 12px; margin: 0 2px;">{threshold_multiplier}</span> × MAD
            </div>
            <div style="font-family: monospace; font-size: 12px; color: #666; margin-top: 8px; margin-left: 8px;">
                ℹ️ Median per condition calculated after excluding top/bottom 2% outliers
            </div>
            <div style="font-family: monospace; font-size: 14px; font-weight: 500; margin-top: 10px; margin-left: 8px; color: #1a1a1a;">
                <span style='color: #2e7d32;'>●</span> Pass: per-condition median within range
            </div>
            <div style="font-family: monospace; font-size: 14px; font-weight: 500; margin-top: 5px; margin-left: 8px; color: #1a1a1a;">
                <span style='color: #c62828;'>●</span> Fail: per-condition median out of range
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    for idx, project in enumerate(selected_projects):
        df = all_data[project].copy()

        st.markdown(f"### 📁 {project}")

        rl_total = df['RL_总中位数'].iloc[0] if not df['RL_总中位数'].isna().all() else 0
        rl_mad = df['RL_MAD'].iloc[0] if not df['RL_MAD'].isna().all() else 1
        rh_total = df['RH_总中位数'].iloc[0] if not df['RH_总中位数'].isna().all() else 0
        rh_mad = df['RH_MAD'].iloc[0] if not df['RH_MAD'].isna().all() else 1

        def fmt_val(v):
            if isinstance(v, (int, float)):
                return f"{v:.3f}" if abs(v) < 1 else f"{v:.1f}"
            return str(v)

        rl_lower = rl_total - threshold_multiplier * rl_mad
        rl_upper = rl_total + threshold_multiplier * rl_mad
        rh_lower = rh_total - threshold_multiplier * rh_mad
        rh_upper = rh_total + threshold_multiplier * rh_mad

        left_col, right_col = st.columns(2)

        combined_all_details = {}

        with left_col:
            st.markdown(
                f"""
                <div style='background-color: #f8f9fa; padding: 10px 14px; border-left: 4px solid #2E86AB; border-radius: 6px; margin-bottom: 12px;'>
                    <div style='font-size: 14px; font-weight: 600; color: #2E86AB; margin-bottom: 6px;'>📉 Vreset</div>
                    <div style='font-size: 13px; color: #333; font-family: monospace;'>
                        Vreset Overall Median = {fmt_val(rl_total)} &nbsp;|&nbsp; MAD = {fmt_val(rl_mad)}<br>
                        <span style='color: #2e7d32;'>●</span> Pass ∈ [{fmt_val(rl_lower)}, {fmt_val(rl_upper)}] &nbsp;|&nbsp; 
                        <span style='color: #c62828;'>●</span> Fail {'<' + fmt_val(rl_lower)} or {'>' + fmt_val(rl_upper)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown("**📉 Vreset Shmoo Plot**")

            try:
                result = create_shmoo_figure(
                    df, 'RL_中位数', 'RL_总中位数', 'RL_MAD',
                    threshold_multiplier, "", project, 'Vreset'
                )
                if result:
                    fig_left, details_df_left = result
                    st.plotly_chart(fig_left, width='stretch', key=f"shmoo_left_{project}_{idx}")
                    if not details_df_left.empty:
                        for _, row in details_df_left.iterrows():
                            key = (row['Time'], row['Subfolder'])
                            if key not in combined_all_details:
                                combined_all_details[key] = {
                                    'Time': row['Time'],
                                    'Subfolder': row['Subfolder'],
                                    'Row Count': row['Row Count'],
                                    'Vreset': row.get('Vreset', ''),
                                    'Vset': '',
                                    'RL_Value': row.get('RL_Value', ''),
                                    'RL_Status': row.get('RL_Status', ''),
                                    'RH_Value': '',
                                    'RH_Status': ''
                                }
                            else:
                                combined_all_details[key]['Vreset'] = row.get('Vreset', '')
                                combined_all_details[key]['RL_Value'] = row.get('RL_Value', '')
                                combined_all_details[key]['RL_Status'] = row.get('RL_Status', '')
                else:
                    st.warning("Insufficient data for Vreset plot")
            except Exception as e:
                st.error(f"Error: {e}")

        with right_col:
            st.markdown(
                f"""
                <div style='background-color: #f8f9fa; padding: 10px 14px; border-left: 4px solid #A23B72; border-radius: 6px; margin-bottom: 12px;'>
                    <div style='font-size: 14px; font-weight: 600; color: #A23B72; margin-bottom: 6px;'>📈 Vset</div>
                    <div style='font-size: 13px; color: #333; font-family: monospace;'>
                        Vset Overall Median = {fmt_val(rh_total)} &nbsp;|&nbsp; MAD = {fmt_val(rh_mad)}<br>
                        <span style='color: #2e7d32;'>●</span> Pass ∈ [{fmt_val(rh_lower)}, {fmt_val(rh_upper)}] &nbsp;|&nbsp; 
                        <span style='color: #c62828;'>●</span> Fail {'<' + fmt_val(rh_lower)} or {'>' + fmt_val(rh_upper)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown("**📈 Vset Shmoo Plot**")

            try:
                result = create_shmoo_figure(
                    df, 'RH_中位数', 'RH_总中位数', 'RH_MAD',
                    threshold_multiplier, "", project, 'Vset'
                )
                if result:
                    fig_right, details_df_right = result
                    st.plotly_chart(fig_right, width='stretch', key=f"shmoo_right_{project}_{idx}")
                    if not details_df_right.empty:
                        for _, row in details_df_right.iterrows():
                            key = (row['Time'], row['Subfolder'])
                            if key not in combined_all_details:
                                combined_all_details[key] = {
                                    'Time': row['Time'],
                                    'Subfolder': row['Subfolder'],
                                    'Row Count': row['Row Count'],
                                    'Vreset': '',
                                    'Vset': row.get('Vset', ''),
                                    'RL_Value': '',
                                    'RL_Status': '',
                                    'RH_Value': row.get('RH_Value', ''),
                                    'RH_Status': row.get('RH_Status', '')
                                }
                            else:
                                combined_all_details[key]['Vset'] = row.get('Vset', '')
                                combined_all_details[key]['RH_Value'] = row.get('RH_Value', '')
                                combined_all_details[key]['RH_Status'] = row.get('RH_Status', '')
                else:
                    st.warning("Insufficient data for Vset plot")
            except Exception as e:
                st.error(f"Error: {e}")

        if combined_all_details:
            combined_df = pd.DataFrame(list(combined_all_details.values()))

            column_order = ['Time', 'Vreset', 'Vset', 'Subfolder', 'RL_Value', 'RL_Status', 'RH_Value', 'RH_Status',
                            'Row Count']
            existing_cols = [col for col in column_order if col in combined_df.columns]
            combined_df = combined_df[existing_cols]

            combined_df = combined_df.sort_values(['Time', 'Subfolder'])
            combined_df.insert(0, 'No.', range(1, len(combined_df) + 1))

            with st.expander("📋 View detailed data", expanded=False):
                st.caption("📊 Values = Median per test condition (excl. top/bottom 2% outliers per condition)")
                st.dataframe(combined_df, width='stretch', height=400, hide_index=True)

        st.markdown("---")