import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy import stats
import os
import re


# ========== 缓存：数据加载和处理 ==========
@st.cache_data
def load_processed_data(main_csv_path, summary_csv_path, excel_path, sheet_name):
    """加载并处理原始数据，缓存结果"""

    # 读取主数据
    df = pd.read_csv(main_csv_path, encoding='utf-8')
    df.columns = df.columns.str.strip().str.replace('\ufeff', '')

    # 读取分组汇总数据
    n_median_map = {}
    p_median_map = {}
    n_avg_map = {}
    p_avg_map = {}

    if os.path.exists(summary_csv_path):
        df_summary = pd.read_csv(summary_csv_path, encoding='utf-8')
        df_summary.columns = df_summary.columns.str.strip().str.replace('\ufeff', '')
        df_summary = df_summary.rename(columns={
            '所属项目': 'Project Name',
            '电压条件': 'Voltage Condition',
            'N-switch中位数(V)': 'N-switch Median (V)',
            'P-switch中位数(V)': 'P-switch Median (V)',
            'N-switch均值(V)': 'N-switch Average (V)',
            'P-switch均值(V)': 'P-switch Average (V)',
        })
        for _, row in df_summary.iterrows():
            key = f"{row['Project Name']}|{row['Voltage Condition']}"
            n_median_map[key] = row.get('N-switch Median (V)', 'N/A')
            p_median_map[key] = row.get('P-switch Median (V)', 'N/A')
            n_avg_map[key] = row.get('N-switch Average (V)', 'N/A')
            p_avg_map[key] = row.get('P-switch Average (V)', 'N/A')

    # 重命名主数据的列
    df = df.rename(columns={
        '所属项目': 'Project Name',
        '电压条件': 'Voltage Condition',
        '正切换电压(V)': 'Positive Voltage (V)',
        '负切换电压(V)': 'Negative Voltage (V)',
        '文件名': 'File Name',
    })

    # 添加中位数和均值的列
    df['Match Key'] = df['Project Name'] + '|' + df['Voltage Condition']
    df['N-switch Median (V)'] = df['Match Key'].map(n_median_map)
    df['P-switch Median (V)'] = df['Match Key'].map(p_median_map)
    df['N-switch Average (V)'] = df['Match Key'].map(n_avg_map)
    df['P-switch Average (V)'] = df['Match Key'].map(p_avg_map)

    # 删除临时列
    df = df.drop(columns=['Match Key'])

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
                        excel_sample_name = str(row[name_col]) if pd.notna(row[name_col]) else ""
                        if excel_sample_name and excel_sample_name != 'nan':
                            # 去除下划线及后面的日期后缀（如 _20260401）
                            clean_name = re.sub(r'_\d{8}$', '', excel_sample_name)

                            time_val = row[time_col] if pd.notna(row[time_col]) else None
                            if time_val:
                                # 尝试解析日期
                                try:
                                    if hasattr(time_val, 'strftime'):
                                        date_str = time_val.strftime('%Y-%m-%d')
                                    else:
                                        # 尝试从字符串中提取日期
                                        time_str = str(time_val)
                                        match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', time_str)
                                        if match:
                                            year, month, day = match.groups()
                                            date_str = f"{year}-{int(month):02d}-{int(day):02d}"
                                        else:
                                            # 尝试用 pandas 解析
                                            dt = pd.to_datetime(time_str)
                                            date_str = dt.strftime('%Y-%m-%d')
                                    # 存储时同时用原始名称和清理后的名称作为 key
                                    sample_modified_map[excel_sample_name] = date_str
                                    sample_modified_map[clean_name] = date_str
                                except:
                                    pass
        except Exception as e:
            pass

    # 添加修改时间列
    df['Sample Modified Date'] = df['Project Name'].map(sample_modified_map).fillna('')

    return df


# ========== 缓存：KDE 计算 ==========
@st.cache_data
def compute_kde_curve(values, n_points=100):
    """计算 KDE 曲线，缓存结果"""
    if len(values) < 2:
        return None, None
    kde = stats.gaussian_kde(values)
    x = np.linspace(min(values), max(values), n_points)
    y = kde(x)
    return x, y


def show():
    current_dir = os.path.dirname(os.path.abspath(__file__))

    main_csv_path = os.path.join(current_dir, "..", "data", "TC3-切换电压统计结果-v3.0-20260612-1.csv")
    main_csv_path = os.path.normpath(main_csv_path)

    summary_csv_path = os.path.join(current_dir, "..", "data", "TC3-切换电压_分组汇总_v3.0-20260612-1.csv")
    summary_csv_path = os.path.normpath(summary_csv_path)

    # Excel 文件路径（用于读取修改时间）
    excel_path = os.path.join(current_dir, "..", "data", "TC-Raw data & Test Report.xlsx")
    excel_path = os.path.normpath(excel_path)
    sheet_name = "TC3-Raw data & Report"

    try:
        if not os.path.exists(main_csv_path):
            st.error(f"Main CSV file not found: {main_csv_path}")
            st.info("Please update the CSV filenames in tc3_switch_voltage.py for TC3")
            return

        # 加载处理后的数据（使用缓存）
        df = load_processed_data(main_csv_path, summary_csv_path, excel_path, sheet_name)

        # 全局样式
        st.markdown("""
            <style>
                span[data-baseweb="tag"] {
                    background-color: #e6f0ff !important;
                    border-color: #b3d4ff !important;
                    color: #1f1f1f !important;
                }
                span[data-baseweb="tag"] span {
                    color: #1f1f1f !important;
                }
                span[data-baseweb="tag"] svg {
                    fill: #4a8bbf !important;
                }
                div[data-baseweb="select"] li {
                    color: #1f1f1f !important;
                }
                div[data-baseweb="select"] div {
                    color: #1f1f1f !important;
                }
                div[data-baseweb="select"] input {
                    color: #1f1f1f !important;
                }
                div[data-baseweb="select"] li:hover {
                    background-color: #f0f5ff !important;
                }
                div[data-baseweb="select"] li[aria-selected="true"] {
                    background-color: #e6f0ff !important;
                }
                div[role="radiogroup"] input:checked {
                    accent-color: #4a8bbf !important;
                }
            </style>
        """, unsafe_allow_html=True)

        # ========== 获取所有可能的选项 ==========
        all_projects = sorted(df['Project Name'].dropna().unique().tolist())
        all_voltages = sorted(df['Voltage Condition'].dropna().unique().tolist())
        all_dates = sorted([d for d in df['Sample Modified Date'].unique() if d and d != ''])

        # ========== 初始化 Session State 变量 ==========
        if 'tc3_selected_projects' not in st.session_state:
            st.session_state.tc3_selected_projects = []
        if 'tc3_selected_voltages' not in st.session_state:
            st.session_state.tc3_selected_voltages = []
        if 'tc3_selected_date_range' not in st.session_state:
            st.session_state.tc3_selected_date_range = ()

        # ========== 联动筛选器 ==========
        col_filter1, col_filter2, col_filter3 = st.columns(3)

        with col_filter1:
            # 根据已选的电压条件和日期范围，计算可用的项目选项
            current_voltages = st.session_state.tc3_selected_voltages
            current_date_range = st.session_state.tc3_selected_date_range

            available_df = df.copy()
            if current_voltages:
                available_df = available_df[available_df['Voltage Condition'].isin(current_voltages)]
            if current_date_range and len(current_date_range) == 2:
                start_str = current_date_range[0].strftime('%Y-%m-%d')
                end_str = current_date_range[1].strftime('%Y-%m-%d')
                available_df = available_df[
                    (available_df['Sample Modified Date'] >= start_str) &
                    (available_df['Sample Modified Date'] <= end_str)
                    ]

            available_projects = sorted(available_df['Project Name'].dropna().unique().tolist())

            selected_projects = st.multiselect(
                "Filter by Project Name",
                options=available_projects,
                default=st.session_state.tc3_selected_projects,
                placeholder="Select projects...",
                key="tc3_project_multiselect"
            )

            # 检测项目选择是否变化，如果变化则自动更新电压选择
            if set(selected_projects) != set(st.session_state.tc3_selected_projects):
                if selected_projects:
                    # 有项目被选中，自动全选这些项目对应的所有电压
                    voltages_to_select = set()
                    for project in selected_projects:
                        project_voltages = df[df['Project Name'] == project][
                            'Voltage Condition'].dropna().unique().tolist()
                        voltages_to_select.update(project_voltages)
                    st.session_state.tc3_selected_voltages = sorted(list(voltages_to_select))
                else:
                    st.session_state.tc3_selected_voltages = []

            st.session_state.tc3_selected_projects = selected_projects

        with col_filter2:
            # 根据已选的项目和日期范围，计算可用的电压选项
            current_projects = st.session_state.tc3_selected_projects
            current_date_range = st.session_state.tc3_selected_date_range

            available_df = df.copy()
            if current_projects:
                available_df = available_df[available_df['Project Name'].isin(current_projects)]
            if current_date_range and len(current_date_range) == 2:
                start_str = current_date_range[0].strftime('%Y-%m-%d')
                end_str = current_date_range[1].strftime('%Y-%m-%d')
                available_df = available_df[
                    (available_df['Sample Modified Date'] >= start_str) &
                    (available_df['Sample Modified Date'] <= end_str)
                    ]

            available_voltages = sorted(available_df['Voltage Condition'].dropna().unique().tolist())

            st.multiselect(
                "Filter by Voltage Condition",
                options=available_voltages,
                key="tc3_selected_voltages",
                placeholder="Select voltage conditions..."
            )

        with col_filter3:
            if all_dates:
                # 只使用 key，不设置 value 参数，避免与 session_state 冲突
                st.date_input(
                    "📅 Sample Modified",
                    key="tc3_selected_date_range",
                    help="Select start and end date for Sample modification time"
                )
            else:
                st.info("No dates available")

        # ========== 只有用户主动选择了至少一项，才显示内容 ==========
        # 修改：日期范围也算作筛选条件
        has_selection = (len(st.session_state.tc3_selected_projects) > 0 or
                         len(st.session_state.tc3_selected_voltages) > 0 or
                         (st.session_state.tc3_selected_date_range and len(
                             st.session_state.tc3_selected_date_range) == 2))

        if not has_selection:
            st.info("👈 Please select at least one Project Name, Voltage Condition, or Date Range to display the chart.")
            return

        # ========== 应用筛选 ==========
        filtered_df = df.copy()

        if st.session_state.tc3_selected_projects:
            filtered_df = filtered_df[filtered_df['Project Name'].isin(st.session_state.tc3_selected_projects)]
        if st.session_state.tc3_selected_voltages:
            filtered_df = filtered_df[filtered_df['Voltage Condition'].isin(st.session_state.tc3_selected_voltages)]
        if st.session_state.tc3_selected_date_range and len(st.session_state.tc3_selected_date_range) == 2:
            start_date, end_date = st.session_state.tc3_selected_date_range
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            filtered_df = filtered_df[
                (filtered_df['Sample Modified Date'] >= start_str) &
                (filtered_df['Sample Modified Date'] <= end_str)
                ]

        if len(filtered_df) == 0:
            st.warning("No data available. Please adjust your filters.")
            return

        # ========== 提取原始数据用于拟合 ==========
        positive_values = filtered_df['Positive Voltage (V)'].dropna().tolist()
        negative_values = filtered_df['Negative Voltage (V)'].dropna().tolist()

        avg_positive = np.mean(positive_values) if positive_values else None
        avg_negative = np.mean(negative_values) if negative_values else None

        # ========== 使用缓存的 KDE 计算（100个点）==========
        pos_x, pos_y = compute_kde_curve(positive_values, n_points=100)
        neg_x, neg_y = compute_kde_curve(negative_values, n_points=100)

        # ========== 创建图表 ==========
        fig = go.Figure()

        # 正电压：直方图 + KDE曲线
        if positive_values:
            fig.add_trace(go.Histogram(
                x=positive_values,
                name='Positive Switch',
                marker_color='#2E86AB',
                opacity=0.6,
                histnorm='probability density',
                nbinsx=20,
                legendgroup='Positive',
                showlegend=True
            ))

            if pos_x is not None:
                fig.add_trace(go.Scatter(
                    x=pos_x,
                    y=pos_y,
                    name='Positive Switch (KDE Fit)',
                    line=dict(color='#2E86AB', width=2.5),
                    legendgroup='Positive',
                    showlegend=True,
                    mode='lines'
                ))

            if avg_positive is not None:
                fig.add_vline(
                    x=avg_positive,
                    line_width=2,
                    line_dash="dash",
                    line_color="#2E86AB",
                    opacity=0.8,
                    annotation_text=f"Avg P: {avg_positive:.3f} V",
                    annotation_position="top",
                    annotation_font_size=11,
                    annotation_font_color="#2E86AB"
                )

        # 负电压：直方图 + KDE曲线
        if negative_values:
            fig.add_trace(go.Histogram(
                x=negative_values,
                name='Negative Switch',
                marker_color='#A23B72',
                opacity=0.6,
                histnorm='probability density',
                nbinsx=20,
                legendgroup='Negative',
                showlegend=True
            ))

            if neg_x is not None:
                fig.add_trace(go.Scatter(
                    x=neg_x,
                    y=neg_y,
                    name='Negative Switch (KDE Fit)',
                    line=dict(color='#A23B72', width=2.5),
                    legendgroup='Negative',
                    showlegend=True,
                    mode='lines'
                ))

            if avg_negative is not None:
                fig.add_vline(
                    x=avg_negative,
                    line_width=2,
                    line_dash="dash",
                    line_color="#A23B72",
                    opacity=0.8,
                    annotation_text=f"Avg N: {avg_negative:.3f} V",
                    annotation_position="top",
                    annotation_font_size=11,
                    annotation_font_color="#A23B72"
                )

        fig.add_vline(x=0, line_width=1.5, line_dash="dash", line_color="gray", opacity=0.5)

        # ========== 【修改1】X轴间隔改为0.5V ==========
        # 计算合理的x轴范围
        all_values = positive_values + negative_values
        if all_values:
            x_min = min(all_values)
            x_max = max(all_values)
            # 扩展一点范围
            padding = 0.5
            x_min = np.floor((x_min - padding) / 0.5) * 0.5
            x_max = np.ceil((x_max + padding) / 0.5) * 0.5
            tick_values = np.arange(x_min, x_max + 0.5, 0.5)
            tick_text = [f"{v:.1f}" for v in tick_values]
        else:
            tick_values = None
            tick_text = None

        fig.update_layout(
            title='Switch Voltage Distribution with KDE Fit',
            xaxis_title="Voltage (V)",
            yaxis_title="Density",
            height=550,
            hovermode='closest',
            legend_title="Switch Type",
            barmode='overlay',
            xaxis=dict(
                zeroline=True,
                zerolinewidth=1,
                zerolinecolor='lightgray',
                tickmode='array' if tick_values is not None else None,
                tickvals=tick_values,
                ticktext=tick_text,
                tickformat='.1f',
                dtick=0.5
            ),
            yaxis=dict(gridcolor='lightgray', zeroline=True, zerolinewidth=1)
        )

        # ========== 显示统计摘要 ==========
        st.markdown("---")
        st.markdown("""
            <style>
                div[data-testid="stMetric"] label {
                    font-size: 12px !important;
                }
                div[data-testid="stMetric"] div {
                    font-size: 18px !important;
                }
            </style>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🟣 Negative Avg", f"{avg_negative:.4f} V" if avg_negative else "N/A")
        with col2:
            st.metric("🔵 Positive Avg", f"{avg_positive:.4f} V" if avg_positive else "N/A")
        with col3:
            st.metric("📊 Negative Count", f"{len(negative_values)}")
        with col4:
            st.metric("📊 Positive Count", f"{len(positive_values)}")

        # ========== 准备电压点选项数据 ==========
        positive_stats = filtered_df.groupby('Positive Voltage (V)').agg({
            'Project Name': list,
            'File Name': list,
            'Voltage Condition': list,
            'Negative Voltage (V)': list,
            'N-switch Median (V)': list,
            'P-switch Median (V)': list,
            'N-switch Average (V)': list,
            'P-switch Average (V)': list,
        }).reset_index()
        positive_stats['Type'] = 'Positive Switch'
        positive_stats['Frequency'] = positive_stats['Project Name'].apply(len)
        positive_stats = positive_stats.rename(columns={'Positive Voltage (V)': 'Voltage (V)'})

        negative_stats = filtered_df.groupby('Negative Voltage (V)').agg({
            'Project Name': list,
            'File Name': list,
            'Voltage Condition': list,
            'Positive Voltage (V)': list,
            'N-switch Median (V)': list,
            'P-switch Median (V)': list,
            'N-switch Average (V)': list,
            'P-switch Average (V)': list,
        }).reset_index()
        negative_stats['Type'] = 'Negative Switch'
        negative_stats['Frequency'] = negative_stats['Project Name'].apply(len)
        negative_stats = negative_stats.rename(columns={'Negative Voltage (V)': 'Voltage (V)'})

        plot_df = pd.concat([positive_stats, negative_stats], ignore_index=True)

        # ========== 检测筛选是否变化，如果变化则清空右侧选中状态 ==========
        filter_key = f"{len(st.session_state.tc3_selected_projects)}_{len(st.session_state.tc3_selected_voltages)}_{len(st.session_state.tc3_selected_date_range) if st.session_state.tc3_selected_date_range else 0}"
        if 'tc3_last_filter_key' not in st.session_state:
            st.session_state.tc3_last_filter_key = filter_key
        elif st.session_state.tc3_last_filter_key != filter_key:
            st.session_state.tc3_last_filter_key = filter_key
            st.session_state.tc3_selected_points = []

        # ============================================================
        # 【修改2】图表占满整行，File Details 移到图表下方
        # ============================================================

        # ========== 显示图表（占满整行） ==========
        st.plotly_chart(fig, width='stretch')

        # ========== File Details 部分（移到图表下方） ==========
        st.markdown("---")
        st.markdown("<h4 style='font-size: 14px; margin-bottom: 10px;'>📋 File Details</h4>", unsafe_allow_html=True)

        sort_option = st.radio(
            "Sort by",
            options=["Voltage (Low to High)", "Voltage (High to Low)", "Frequency (Low to High)",
                     "Frequency (High to Low)"],
            horizontal=True,
            label_visibility="collapsed",
            key="tc3_sort_radio"
        )

        if sort_option == "Voltage (Low to High)":
            sorted_df = plot_df.sort_values('Voltage (V)', ascending=True)
        elif sort_option == "Voltage (High to Low)":
            sorted_df = plot_df.sort_values('Voltage (V)', ascending=False)
        elif sort_option == "Frequency (Low to High)":
            sorted_df = plot_df.sort_values('Frequency', ascending=True)
        else:
            sorted_df = plot_df.sort_values('Frequency', ascending=False)

        point_labels = [f"{row['Frequency']} - {row['Voltage (V)']:.3f} V ({row['Type']})"
                        for _, row in sorted_df.iterrows()]

        all_indices = list(range(len(point_labels)))

        if 'tc3_selected_points' not in st.session_state:
            st.session_state.tc3_selected_points = []

        selected_indices = st.multiselect(
            "Select voltage points to display",
            options=all_indices,
            format_func=lambda i: point_labels[i],
            default=st.session_state.tc3_selected_points,
            placeholder="Select one or more voltage points...",
            key="tc3_point_multiselect"
        )

        st.session_state.tc3_selected_points = selected_indices

        st.markdown("---")

        if selected_indices:
            selected_voltages_data = [sorted_df.iloc[idx] for idx in selected_indices]

            all_details_data = []
            for selected_row in selected_voltages_data:
                file_count = len(selected_row['Project Name'])

                all_details_data.append({
                    'Project': f'--- {selected_row["Type"]} @ {selected_row["Voltage (V)"]:.3f} V (Freq: {selected_row["Frequency"]}) ---',
                    'File': '',
                    'Condition': '',
                    'Negative Voltage': '',
                    'Positive Voltage': '',
                    'N Avg (Project)': '',
                    'P Avg (Project)': '',
                    'N Median (Project)': '',
                    'P Median (Project)': '',
                })

                for i in range(file_count):
                    project = selected_row['Project Name'][i]
                    file_name = selected_row['File Name'][i]
                    voltage_condition = selected_row['Voltage Condition'][i]

                    if selected_row['Type'] == 'Positive Switch':
                        other_voltage = selected_row['Negative Voltage (V)'][i]
                        pos_voltage = selected_row['Voltage (V)']
                        neg_voltage = other_voltage
                    else:
                        other_voltage = selected_row['Positive Voltage (V)'][i]
                        pos_voltage = other_voltage
                        neg_voltage = selected_row['Voltage (V)']

                    n_median = selected_row['N-switch Median (V)'][i] if isinstance(
                        selected_row['N-switch Median (V)'], list) else selected_row['N-switch Median (V)']
                    p_median = selected_row['P-switch Median (V)'][i] if isinstance(
                        selected_row['P-switch Median (V)'], list) else selected_row['P-switch Median (V)']
                    n_avg = selected_row['N-switch Average (V)'][i] if isinstance(
                        selected_row['N-switch Average (V)'], list) else selected_row['N-switch Average (V)']
                    p_avg = selected_row['P-switch Average (V)'][i] if isinstance(
                        selected_row['P-switch Average (V)'], list) else selected_row['P-switch Average (V)']

                    def fmt_voltage(val):
                        if pd.isna(val):
                            return 'N/A'
                        try:
                            return f"{float(val):.3f} V"
                        except:
                            return str(val)

                    def fmt_value(val):
                        if pd.isna(val) or val == 'N/A':
                            return 'N/A'
                        try:
                            return f"{float(val):.3f} V"
                        except:
                            return str(val)

                    all_details_data.append({
                        'Project': project,
                        'File': file_name,
                        'Condition': voltage_condition,
                        'Positive Voltage': fmt_voltage(pos_voltage),
                        'Negative Voltage': fmt_voltage(neg_voltage),
                        'N Avg (Project)': fmt_value(n_avg),
                        'P Avg (Project)': fmt_value(p_avg),
                        'N Median (Project)': fmt_value(n_median),
                        'P Median (Project)': fmt_value(p_median),
                    })

            details_df = pd.DataFrame(all_details_data)
            st.markdown(
                f"**{len(selected_indices)} voltage point(s) selected, {len(details_df) - len(selected_indices)} files shown**")
            st.dataframe(details_df, width='stretch', height=500)
        else:
            st.info(
                "No voltage points selected. Select voltage points from the dropdown above to display file details.")

    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.info("Please check data format in CSV files")