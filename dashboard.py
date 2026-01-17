import streamlit as st
import pandas as pd
import json
from pathlib import Path
import plotly.express as px
from datetime import datetime, date

# 导入反馈明细页面
from feedback_details_page import show_feedback_details_page
# 导入自定义样式
from styles import apply_custom_styles, create_metric_card
# 导入导航菜单组件
from streamlit_option_menu import option_menu

# --- 页面配置 ---
st.set_page_config(
    page_title="聆境BI数据看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- 数据加载与处理 ---
def load_data(file_path):
    """
    加载并预处理JSON统计数据。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        st.error(f"错误：找不到数据文件。请确保 '{file_path}' 存在。")
        return None


@st.cache_data
def convert_df_to_csv(df: pd.DataFrame) -> bytes:
    """
    将DataFrame转换为UTF-8编码的CSV字节流，并缓存结果。
    """
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')


def process_daily_stats(daily_stats_dict):
    """将每日统计字典转换为格式正确的DataFrame。"""
    if not daily_stats_dict:
        return pd.DataFrame(columns=['date', 'usage_count', 'feedback_count'])
    df = pd.DataFrame.from_dict(daily_stats_dict, orient='index')
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"
    return df.reset_index()  # 重置索引，使date成为普通列


def process_dict_to_df(data_dict, index_name="name"):
    """通用函数，将字典转换为DataFrame，并将索引重置为列。"""
    if not data_dict:
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(data_dict, orient='index')
    df.index.name = index_name
    return df.reset_index()


# --- 概览页面函数 ---
def show_overview_page():
    """显示概览页面内容"""
    # 应用自定义样式
    apply_custom_styles()

    # --- 登录验证 ---
    if not st.session_state.get("authenticated", False):
        st.title("🔒 登录到聆境BI数据看板")

        # 在实际应用中，应使用 st.secrets 或环境变量等更安全的方式管理凭据
        # 为简单起见，这里我们硬编码一个用户
        PRESET_USERS = {
            "admin": "Kfs0716"  # 您可以修改这里的用户名和密码
        }

        with st.form("login_form"):
            username = st.text_input("用户名")
            password = st.text_input("密码", type="password")
            submitted = st.form_submit_button("登录")

            if submitted:
                if username in PRESET_USERS and PRESET_USERS[username] == password:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("用户名或密码不正确。")
        return  # 如果未登录，则停止执行

    # --- 如果已登录，则显示主应用 ---

    # --- 登出按钮 ---
    def logout():
        st.session_state.authenticated = False
        st.rerun()

    # 修复(1): 删除了注入不稳定CSS的 st.markdown 代码块。
    # Streamlit 的 st.columns 是实现这种布局的正确且稳定的方法。

    # 将标题和退出登录按钮放在页面顶部同一行
    col_title, col_button = st.columns([0.9, 0.1])
    with col_title:
        st.markdown('<h1 class="custom-title">聆境BI数据看板 - 概览</h1>', unsafe_allow_html=True)
    with col_button:
        st.button("退出登录", on_click=logout, use_container_width=True)

    st.caption("展示用户聊天、反馈和模型使用情况的交互式仪表盘。")

    # 找到最新的统计文件
    data_dir = Path(__file__).parent / "df_data"
    list_of_files = list(data_dir.glob('*_summary_stats.json'))
    if not list_of_files:
        st.error("在当前目录下找不到任何 `_summary_stats.json` 文件。")
        st.stop()

    latest_file = max(list_of_files, key=lambda p: p.stat().st_mtime)

    data = load_data(latest_file)
    if not data:
        st.stop()

    # --- 数据预处理 ---
    overall_stats = data.get('overall_stats', {})
    daily_df = process_daily_stats(data.get('daily_stats', {}))
    model_df = process_dict_to_df(data.get('model_stats', {}), "model")

    daily_user_stats_list = data.get('daily_user_stats', [])
    if daily_user_stats_list:
        user_daily_df = pd.DataFrame(daily_user_stats_list)
        if not user_daily_df.empty:
            user_daily_df['created_at'] = pd.to_datetime(user_daily_df['created_at'])
    else:
        user_daily_df = pd.DataFrame(columns=['created_at', 'user_name', 'usage_count', 'feedback_count'])

    # --- 页面主体 ---

    # 1. 关键指标 (KPIs)
    st.header("整体概览")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="总提问数", value=f"{overall_stats.get('total_user_queries', 0):,}")
    with col2:
        st.metric(label="总反馈数", value=f"{overall_stats.get('total_feedbacks', 0):,}")
    with col3:
        st.metric(label="反馈率", value=f"{overall_stats.get('feedback_ratio', 0):.2%}")

    st.markdown("---")

    # ... existing code ...
    # 2. 每日趋势
    st.header("每日使用与反馈趋势")

    if not daily_df.empty:
        FIXED_MIN_DATE = date(2026, 1, 13)

        min_date = max(daily_df['date'].min().date(), FIXED_MIN_DATE)
        max_date = max(daily_df['date'].max().date(), FIXED_MIN_DATE)

        daily_df.sort_values(by='date', ascending=False, inplace=True)
        date_range = st.date_input(
            "选择日期范围",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="daily_date_range",
            help="选择一个时间段来分析趋势。"
        )

        # 初始化 filtered_daily_df
        filtered_daily_df = pd.DataFrame()
        start_date = min_date
        end_date = max_date

        # 处理日期范围选择
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_daily_df = daily_df[
                (daily_df['date'].dt.date >= start_date) & (daily_df['date'].dt.date <= end_date)]
        elif len(date_range) == 1:
            # 只选择一天的情况
            start_date = end_date = date_range[0]
            filtered_daily_df = daily_df[daily_df['date'].dt.date == start_date]

        if not filtered_daily_df.empty:
            col1, col2 = st.columns(2)

            with col1:
                # 重命名列用于显示
                display_columns = {
                    'usage_count': '提问数',
                    'feedback_count': '反馈数',
                    'good': '好评数',
                    'bad': '错误数',
                    'improve': '待改进数'
                }

                # 创建图表 - 如果只有一天数据，使用散点图显示点
                if len(filtered_daily_df) == 1:
                    # 单日数据，使用散点图显示点
                    fig_daily = px.scatter(
                        filtered_daily_df, x='date', y=['usage_count', 'feedback_count', 'good', 'bad', 'improve'],
                        labels={'value': '数量', 'date': '日期', 'variable': '指标'},
                        template="plotly_white"
                    )
                    fig_daily.update_traces(marker=dict(size=10))
                else:
                    # 多日数据，使用折线图
                    fig_daily = px.line(
                        filtered_daily_df, x='date', y=['usage_count', 'feedback_count', 'good', 'bad', 'improve'],
                        labels={'value': '数量', 'date': '日期', 'variable': '指标'},
                        template="plotly_white"
                    )

                fig_daily.update_layout(
                    legend_title_text='',
                    title_text="每日提问和反馈数量",
                    title_x=0.5,
                    xaxis_title="日期",
                    yaxis_title="数量"
                )
                # 更新图例标签
                for i, trace in enumerate(fig_daily.data):
                    if i < len(display_columns):
                        trace.name = list(display_columns.values())[i]
                st.plotly_chart(fig_daily, use_container_width=True)

            with col2:
                rate_cols = ['feedback_ratio', 'excellent_rate', 'error_rate', 'improve_rate']

                legend_rename_map = {
                    'feedback_ratio': '反馈率',
                    'excellent_rate': '好评率',
                    'error_rate': '错误率',
                    'improve_rate': '待改进率'
                }

                available_cols = [col for col in rate_cols if col in filtered_daily_df.columns]

                if available_cols:
                    if len(filtered_daily_df) == 1:
                        # 单日数据，使用散点图显示点
                        df_melted = filtered_daily_df.melt(
                            id_vars=['date'],
                            value_vars=available_cols,
                            var_name='指标',
                            value_name='比率'
                        )
                        df_melted['指标'] = df_melted['指标'].map(legend_rename_map)

                        fig_rates = px.scatter(
                            df_melted, x='date', y='比率', color='指标',
                            labels={'比率': '比率', 'date': '日期'},
                            template="plotly_white"
                        )
                        fig_rates.update_traces(marker=dict(size=10))
                    else:
                        # 多日数据，使用折线图
                        df_melted = filtered_daily_df.melt(
                            id_vars=['date'],
                            value_vars=available_cols,
                            var_name='指标',
                            value_name='比率'
                        )
                        df_melted['指标'] = df_melted['指标'].map(legend_rename_map)

                        fig_rates = px.line(
                            df_melted, x='date', y='比率', color='指标',
                            labels={'比率': '比率', 'date': '日期'},
                            template="plotly_white"
                        )

                    fig_rates.update_layout(
                        legend_title_text='',
                        title_text="每日反馈比率趋势",
                        title_x=0.5,
                        yaxis_tickformat='.2%'
                    )
                    st.plotly_chart(fig_rates, use_container_width=True)
                else:
                    st.info("无可用的反馈率数据。")

            # 新增：每日文字量趋势图表（使用与每日使用与反馈趋势相同的时间范围）
            # 删除标题行：st.subheader("每日文字量趋势")

            # 按日期和用户分组，计算每日文字量 - 使用正确的文字量数据
            daily_text_df = user_daily_df.groupby(['created_at', 'user_name']).agg({
                'user_text_length': 'sum',
                'ai_text_length': 'sum'
            }).reset_index()

            # 使用与每日使用与反馈趋势相同的时间范围
            filtered_daily_text_df = daily_text_df[
                (daily_text_df['created_at'].dt.date >= start_date) &
                (daily_text_df['created_at'].dt.date <= end_date)
                ]

            if not filtered_daily_text_df.empty:
                # 修复：为所有日期和用户组合填充缺失数据，确保字符量为0的天数也显示
                # 生成完整的日期范围
                all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
                all_users = filtered_daily_text_df['user_name'].unique()

                # 创建完整的日期-用户组合
                full_combinations = pd.MultiIndex.from_product(
                    [all_dates, all_users],
                    names=['created_at', 'user_name']
                ).to_frame(index=False)

                # 合并现有数据，填充缺失值为0
                daily_text_df_full = pd.merge(
                    full_combinations,
                    filtered_daily_text_df,
                    on=['created_at', 'user_name'],
                    how='left'
                ).fillna(0)

                # 创建颜色映射，确保同一用户颜色一致
                unique_users = daily_text_df_full['user_name'].unique()
                colors = px.colors.qualitative.Set1 + px.colors.qualitative.Set2 + px.colors.qualitative.Set3
                color_map = {user: colors[i % len(colors)] for i, user in enumerate(unique_users)}

                col1, col2 = st.columns(2)

                with col1:
                    # 每日用户输入文字量趋势 - 使用正确的文字量数据
                    if len(daily_text_df_full['created_at'].unique()) == 1:
                        # 单日数据，使用散点图
                        fig_daily_user_text = px.scatter(
                            daily_text_df_full,
                            x='created_at',
                            y='user_text_length',
                            color='user_name',
                            labels={'user_text_length': '用户输入文字量（字符）', 'created_at': '日期',
                                    'user_name': '用户'},
                            template="plotly_white",
                            color_discrete_map=color_map
                        )
                        fig_daily_user_text.update_traces(marker=dict(size=10))
                    else:
                        # 多日数据，使用折线图
                        fig_daily_user_text = px.line(
                            daily_text_df_full,
                            x='created_at',
                            y='user_text_length',
                            color='user_name',
                            labels={'user_text_length': '用户输入文字量（字符）', 'created_at': '日期',
                                    'user_name': '用户'},
                            template="plotly_white",
                            color_discrete_map=color_map
                        )
                    fig_daily_user_text.update_layout(
                        legend_title_text='',
                        title_text="每日用户输入文字量趋势",
                        title_x=0.5
                    )
                    st.plotly_chart(fig_daily_user_text, use_container_width=True)

                    with col2:
                        # 每日AI输出文字量趋势 - 使用正确的文字量数据
                        if len(daily_text_df_full['created_at'].unique()) == 1:
                            # 单日数据，使用散点图
                            fig_daily_ai_text = px.scatter(
                                daily_text_df_full,
                                x='created_at',
                                y='ai_text_length',
                                color='user_name',
                                labels={'ai_text_length': 'AI输出文字量（字符）', 'created_at': '日期',
                                        'user_name': '用户'},
                                template="plotly_white",
                                color_discrete_map=color_map
                            )
                            fig_daily_ai_text.update_traces(marker=dict(size=10))
                        else:
                            # 多日数据，使用折线图
                            fig_daily_ai_text = px.line(
                                daily_text_df_full,
                                x='created_at',
                                y='ai_text_length',
                                color='user_name',
                                labels={'ai_text_length': 'AI输出文字量（字符）', 'created_at': '日期',
                                        'user_name': '用户'},
                                template="plotly_white",
                                color_discrete_map=color_map
                            )
                        fig_daily_ai_text.update_layout(
                            legend_title_text='',
                            title_text="每日AI输出文字量趋势",
                            title_x=0.5
                        )
                        st.plotly_chart(fig_daily_ai_text, use_container_width=True)

                    # 查看每日趋势明细数据 - 完全移出两列布局，显示在最左边并完全展开
                with st.expander("查看每日趋势明细数据"):
                    display_df = filtered_daily_df.copy()
                    rate_cols = ['feedback_ratio', 'excellent_rate', 'error_rate', 'to_be_improved_rate']
                    format_dict = {
                        'usage_count': '{:,}',
                        'feedback_count': '{:,}',
                        'good': '{:,}',
                        'bad': '{:,}',
                        'improve': '{:,}',
                        'user_text_length': '{:,}',
                        'ai_text_length': '{:,}'
                    }
                    for col in rate_cols:
                        if col in display_df.columns:
                            format_dict[col] = '{:.2%}'
                    display_df = display_df.rename(columns={
                        'usage_count': '提问数',
                        'feedback_count': '反馈数',
                        'good': '好评数',
                        'bad': '错误数',
                        'feedback_ratio': '反馈率',
                        'improve': '待改进数',
                        'excellent_rate': '好评率',
                        'error_rate': '错误率',
                        'improve_rate': '待改进率',
                        'user_text_length': '用户输入文字量',
                        'ai_text_length': 'AI输出文字量'
                    })
                    # 设置表格高度，确保完全展开显示所有行
                    st.dataframe(display_df.style.format(format_dict), height=min(600, 100 + len(display_df) * 35))
                    csv_daily = convert_df_to_csv(filtered_daily_df)
                    st.download_button(
                        label="下载每日趋势数据 (CSV)",
                        data=csv_daily,
                        file_name=f'daily_trend_{start_date}_to_{end_date}.csv',
                        mime='text/csv',
                    )

            else:
                st.warning("在选定时间范围内没有可供分析的每日数据。")
        else:
                st.warning("没有可供分析的每日数据。")
    st.markdown("---")
    # ... existing code ...

    # 3. 模型使用情况分析
    st.header("模型使用情况分析")
    if not model_df.empty:
        # 添加日期范围选择器
        FIXED_MIN_DATE = date(2026, 1, 13)
        min_date_model = max(daily_df['date'].min().date(), FIXED_MIN_DATE) if not daily_df.empty else FIXED_MIN_DATE
        max_date_model = max(daily_df['date'].max().date(), FIXED_MIN_DATE) if not daily_df.empty else FIXED_MIN_DATE

        model_date_range = st.date_input(
            "选择日期范围",
            value=(min_date_model, max_date_model),
            min_value=min_date_model,
            max_value=max_date_model,
            key="model_date_range",
            help="选择一个时间段来分析模型使用情况。"
        )

        if len(model_date_range) == 2:
            start_date_model, end_date_model = model_date_range

            # 根据日期范围重新计算模型统计数据
            # 需要从原始数据文件中重新加载数据并过滤
            try:
                # 找到最新的聊天数据文件
                chat_files = list(data_dir.glob('*_chat_data.csv'))
                if chat_files:
                    latest_chat_file = max(chat_files, key=lambda p: p.stat().st_mtime)
                    chat_df = pd.read_csv(latest_chat_file)
                    chat_df['created_at'] = pd.to_datetime(chat_df['created_at'], errors='coerce')

                    # 过滤聊天数据
                    filtered_chat_df = chat_df[
                        (chat_df['created_at'].dt.date >= start_date_model) &
                        (chat_df['created_at'].dt.date <= end_date_model)
                        ]

                    # 过滤反馈数据
                    feedback_files = list(data_dir.glob('*_feedback_data.csv'))
                    if feedback_files:
                        latest_feedback_file = max(feedback_files, key=lambda p: p.stat().st_mtime)
                        feedback_df = pd.read_csv(latest_feedback_file)
                        feedback_df['created_at'] = pd.to_datetime(feedback_df['created_at'], errors='coerce')

                        filtered_feedback_df = feedback_df[
                            (feedback_df['created_at'].dt.date >= start_date_model) &
                            (feedback_df['created_at'].dt.date <= end_date_model)
                            ]

                        # 重新计算模型统计数据
                        model_usage = filtered_chat_df['last_chat_model'].value_counts().to_dict()
                        model_feedback = filtered_feedback_df['model'].value_counts().to_dict()

                        model_df_filtered = pd.DataFrame({
                            'model': list(set(model_usage.keys()) | set(model_feedback.keys())),
                            'usage_count': [model_usage.get(model, 0) for model in
                                            set(model_usage.keys()) | set(model_feedback.keys())],
                            'feedback_count': [model_feedback.get(model, 0) for model in
                                               set(model_usage.keys()) | set(model_feedback.keys())]
                        })

                        # 清理模型名称中的特殊字符
                        model_df_filtered['model'] = model_df_filtered['model'].astype(str).str.replace('$', '\\$',
                                                                                                        regex=False)
                        df_to_plot_model = model_df_filtered.sort_values('usage_count', ascending=False)
                    else:
                        df_to_plot_model = pd.DataFrame(columns=['model', 'usage_count', 'feedback_count'])
                else:
                    df_to_plot_model = pd.DataFrame(columns=['model', 'usage_count', 'feedback_count'])
            except Exception as e:
                st.error(f"加载数据时出错: {e}")
                df_to_plot_model = model_df.sort_values('usage_count', ascending=False)

            col1, col2 = st.columns([3, 2])

            # ... existing code ...
            with col1:
                if not df_to_plot_model.empty:
                    fig_model = px.bar(
                        df_to_plot_model,
                        x='model',
                        y=['usage_count', 'feedback_count'],
                        barmode='group',
                        labels={'value': '数量', 'model': '模型', 'variable': '指标'},
                        template="plotly_white",
                        text_auto=True
                    )
                    # 修改图例标签
                    for trace in fig_model.data:
                        if trace.name == 'usage_count':
                            trace.name = '提问次数'
                        elif trace.name == 'feedback_count':
                            trace.name = '反馈次数'
                    fig_model.update_layout(legend_title_text='', xaxis_title=None, title_text="各模型提问量 vs 反馈量",
                                            title_x=0.5)
                    fig_model.update_traces(textposition='outside')
                    st.plotly_chart(fig_model, use_container_width=True)
                else:
                    st.info("在选定时间范围内没有模型使用数据。")

            with col2:
                if not df_to_plot_model.empty:
                    st.markdown("##### 数据明细")
                    # 修改表格列名
                    display_model_df = df_to_plot_model.rename(columns={
                        'usage_count': '提问次数',
                        'feedback_count': '反馈次数'
                    })
                    st.dataframe(
                        display_model_df.style.format({'提问次数': '{:,}', '反馈次数': '{:,}'}),
                        use_container_width=True
                    )
                    csv_model = convert_df_to_csv(df_to_plot_model)
                    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="下载模型使用反馈数据(CSV)",
                        data=csv_model,
                        file_name=f'model_stats_data_{time_str}.csv',
                        mime='text/csv',
                    )
                else:
                    st.info("没有可下载的数据。")
        # ... existing code ...
    else:
        st.info("没有模型统计数据。")

    st.markdown("---")

    # 4. 用户使用情况分析
    st.header("用户使用情况分析")

    if not user_daily_df.empty:
        FIXED_MIN_DATE = date(2026, 1, 13)

        min_date_user = max(user_daily_df['created_at'].min().date(), FIXED_MIN_DATE)
        max_date_user = max(user_daily_df['created_at'].max().date(), FIXED_MIN_DATE)

        # 将日期范围选择器和用户选择器放在同一行
        col1, col2 = st.columns([1.2, 1])

        with col1:
            user_date_range = st.date_input(
                "选择日期范围", value=(min_date_user, max_date_user),
                min_value=min_date_user,
                max_value=max_date_user,
                key="user_date_range", help="选择一个时间段来分析用户数据。"
            )

        if len(user_date_range) == 2:
            start_date_user, end_date_user = user_date_range

            filtered_user_daily_df = user_daily_df[
                (user_daily_df['created_at'].dt.date >= start_date_user) &
                (user_daily_df['created_at'].dt.date <= end_date_user)
                ]

            # 确保使用正确的文字量数据（从用户每日统计数据中获取）
            user_df = filtered_user_daily_df.groupby('user_name').agg(
                usage_count=('usage_count', 'sum'),
                feedback_count=('feedback_count', 'sum'),
                user_text_length=('user_text_length', 'sum'),
                ai_text_length=('ai_text_length', 'sum')
            ).reset_index().rename(columns={'user_name': 'user'})

            if not user_df.empty:
                # 修复(2b): 清理用户名称中的特殊字符（例如'$'），以防止在前端渲染图表或多选框时引发JS错误。
                user_df['user'] = user_df['user'].astype(str).str.replace('$', '\\$', regex=False)

                user_list = sorted(user_df['user'].unique())

                with col2:
                    selected_users = st.multiselect(
                        "选择用户",
                        options=user_list, default=None,
                        placeholder="选择一个或多个用户进行分析"
                    )

                if selected_users:
                    df_to_plot = user_df[user_df['user'].isin(selected_users)].copy()
                    title_text = "所选用户提问量 vs 反馈量"
                    title_text_length = "所选用户输入文字量 vs AI输出文字量"
                else:
                    df_to_plot = user_df.sort_values('usage_count', ascending=False)
                    title_text = "用户提问量 vs 反馈量"
                    title_text_length = "用户输入文字量 vs AI输出文字量"

                df_to_plot.sort_values('usage_count', ascending=True, inplace=True)

                # 将两个图表放在同一行
                col_chart1, col_chart2 = st.columns(2)

                # ... existing code ...
                with col_chart1:
                    # 原有的用户提问量vs反馈量图表
                    fig_user = px.bar(
                        df_to_plot, y='user', x=['usage_count', 'feedback_count'],
                        orientation='h', barmode='group',
                        labels={'value': '数量', 'user': '用户', 'variable': '指标'},
                        template="plotly_white",
                        height=max(400, len(df_to_plot) * 40), text_auto=True
                    )
                    # 修改图例标签
                    for trace in fig_user.data:
                        if trace.name == 'usage_count':
                            trace.name = '提问次数'
                        elif trace.name == 'feedback_count':
                            trace.name = '反馈次数'
                    fig_user.update_layout(legend_title_text='', yaxis_title=None, title_text=title_text, title_x=0.5)
                    fig_user.update_traces(textposition='outside')
                    st.plotly_chart(fig_user, use_container_width=True)

                with col_chart2:
                    # 用户输入文字量vsAI输出文字量图表 - 使用正确的文字量数据
                    df_text_length = df_to_plot.copy()
                    df_text_length.sort_values('user_text_length', ascending=True, inplace=True)

                    fig_text_length = px.bar(
                        df_text_length, y='user', x=['ai_text_length', 'user_text_length'],  # 调整顺序：AI输出在上，用户输入在下
                        orientation='h', barmode='group',
                        labels={'value': '文字量（字符）', 'user': '用户', 'variable': '指标'},
                        template="plotly_white",
                        height=max(400, len(df_text_length) * 40), text_auto=True,
                        color_discrete_map={'user_text_length': '#1f77b4', 'ai_text_length': '#d62728'}  # 蓝色和红色
                    )
                    fig_text_length.update_layout(legend_title_text='', yaxis_title=None, title_text=title_text_length,
                                                  title_x=0.5)
                    # 修改图例标签
                    for trace in fig_text_length.data:
                        if trace.name == 'user_text_length':
                            trace.name = '用户输入文字量'
                        elif trace.name == 'ai_text_length':
                            trace.name = 'AI输出文字量'
                    fig_text_length.update_traces(textposition='outside')
                    st.plotly_chart(fig_text_length, use_container_width=True)

                with st.expander("查看用户统计明细数据"):
                    display_df = df_to_plot.sort_values('usage_count', ascending=False)
                    # 修改表格列名
                    display_df = display_df.rename(columns={
                        'usage_count': '提问次数',
                        'feedback_count': '反馈次数',
                        'user_text_length': '用户输入文字量',
                        'ai_text_length': 'AI输出文字量'
                    })
                    st.dataframe(display_df.style.format({
                        '提问次数': '{:,}',
                        '反馈次数': '{:,}',
                        '用户输入文字量': '{:,}',
                        'AI输出文字量': '{:,}'
                    }))

                    csv_user = convert_df_to_csv(df_to_plot)
                    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="下载用户使用数据(CSV)",
                        data=csv_user,
                        file_name=f'user_use_data_{time_str}.csv',
                        mime='text/csv',
                    )
            # ... existing code ...
            else:
                st.info("在选定时间范围内没有用户数据。")
    else:
        st.info("没有用户统计数据。")


# --- 主函数 ---
def main():
    # 检查登录状态
    is_authenticated = st.session_state.get("authenticated", False)

    # 如果未登录，只显示登录页面，不显示侧边栏
    if not is_authenticated:
        show_overview_page()
    else:
        # 登录后，显示完整的UI，包括侧边栏和所选页面
        with st.sidebar:
            st.title("聆境 BI")

            # 使用 streamlit-option-menu 创建导航
            selected_page = option_menu(
                menu_title="导航菜单",  # required
                options=["数据概览", "反馈明细"],  # required
                icons=["bar-chart-line", "chat-dots"],  # optional
                menu_icon="compass",  # optional
                default_index=0,  # optional
                styles={
                    "container": {"padding": "0!important", "background-color": "#f8f9fa"},
                    "icon": {"color": "#f6b93b", "font-size": "20px"},
                    "nav-link": {
                        "font-size": "16px",
                        "text-align": "left",
                        "margin": "0px",
                        "color": "#34495e",
                        "--hover-color": "#eef2f7"
                    },
                    "nav-link-selected": {"background-color": "#4a69bd", "color": "white"},
                }
            )

        # 根据选择的页面显示对应内容
        if selected_page == "数据概览":
            show_overview_page()
        elif selected_page == "反馈明细":
            show_feedback_details_page()


if __name__ == "__main__":
    main()
