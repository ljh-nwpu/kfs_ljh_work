import streamlit as st
import pandas as pd
import json
from pathlib import Path
import plotly.express as px
from datetime import datetime,date

# --- 页面配置 ---
st.set_page_config(
    page_title="聆境BI数据看板",
    page_icon="📊",
    layout="wide"
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
    return df.reset_index() # 重置索引，使date成为普通列

def process_dict_to_df(data_dict, index_name="name"):
    """通用函数，将字典转换为DataFrame，并将索引重置为列。"""
    if not data_dict:
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(data_dict, orient='index')
    df.index.name = index_name
    return df.reset_index()

# --- 主函数 ---
def main():
    # --- 登录验证 ---
    if not st.session_state.get("authenticated", False):
        st.title("🔒 登录到聆境BI数据看板")
        
        # 在实际应用中，应使用 st.secrets 或环境变量等更安全的方式管理凭据
        # 为简单起见，这里我们硬编码一个用户
        PRESET_USERS = {
            "admin": "Kfs0716" # 您可以修改这里的用户名和密码
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
        return # 如果未登录，则停止执行

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
        st.title("📊 聆镜BI数据看板")
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
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_daily_df = daily_df[(daily_df['date'].dt.date >= start_date) & (daily_df['date'].dt.date <= end_date)]

            col1, col2 = st.columns(2)

            with col1:
                filtered_daily_df=filtered_daily_df.rename(columns={
                    'usage_count': '提问数',
                    'feedback_count': '反馈数',
                    'good': '好评数',
                    'bad': '错误数',
                    'improve': '待改进数'
                })
                fig_daily = px.line(
                    filtered_daily_df, x='date', y=['提问数', '反馈数', '好评数', '错误数', '待改进数'],
                    labels={'value': '数量', 'date': '日期', 'variable': '指标'},
                    template="plotly_white"
                )
                fig_daily.update_layout(legend_title_text='', title_text="每日提问和反馈数量", title_x=0.5)
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


            with st.expander("查看每日趋势明细数据"):
                display_df = filtered_daily_df.copy()
                rate_cols = ['feedback_ratio', 'excellent_rate', 'error_rate', 'to_be_improved_rate']
                format_dict = {
                    'usage_count': '{:,}', 
                    'feedback_count': '{:,}',
                    'good': '{:,}',
                    'bad': '{:,}',
                    'improve': '{:,}'
                }
                for col in rate_cols:
                    if col in display_df.columns:
                        format_dict[col] = '{:.2%}'
                display_df=display_df.rename(columns={
                    'usage_count': '提问数',
                    'feedback_count': '反馈数',
                    'good': '好评数',
                    'bad': '错误数',
                    'feedback_ratio': '反馈率',
                    'improve': '待改进数',
                    'excellent_rate': '好评率',
                    'error_rate': '错误率',
                    'improve_rate': '待改进率'
                })
                st.dataframe(display_df.style.format(format_dict))
                csv_daily = convert_df_to_csv(filtered_daily_df)
                st.download_button(
                    label="下载每日趋势数据 (CSV)",
                    data=csv_daily,
                    file_name=f'daily_trend_{start_date}_to_{end_date}.csv',
                    mime='text/csv',
                )
    else:
        st.warning("没有可供分析的每日数据。")

    st.markdown("---")

    # 3. 模型使用情况分析
    st.header("模型使用情况分析")
    if not model_df.empty:
        # 修复(2a): 清理模型名称中的特殊字符（例如'$'），以防止在前端渲染图表时引发JS错误。
        # .astype(str)确保了即使名称是数字也能正常处理。
        model_df['model'] = model_df['model'].astype(str).str.replace('$', '\\$', regex=False)
        
        df_to_plot_model = model_df.sort_values('usage_count', ascending=False)
        
        col1, col2 = st.columns([3, 2])
        
        with col1:
            fig_model = px.bar(
                df_to_plot_model,
                x='model',
                y=['usage_count', 'feedback_count'],
                barmode='group',
                labels={'value': '数量', 'model': '模型', 'variable': '指标'},
                template="plotly_white",
                text_auto=True
            )
            fig_model.update_layout(legend_title_text='', xaxis_title=None, title_text="各模型提问量 vs 反馈量", title_x=0.5)
            fig_model.update_traces(textposition='outside')
            st.plotly_chart(fig_model, use_container_width=True)
            
        with col2:
            st.markdown("##### 数据明细")
            st.dataframe(
                df_to_plot_model.style.format({'usage_count': '{:,}', 'feedback_count': '{:,}'}),
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
                "选择日期范围",             value=(min_date_user, max_date_user),
                min_value=min_date_user,
                max_value=max_date_user,
                key="user_date_range",              help="选择一个时间段来分析用户数据。"
            )
        
        if len(user_date_range) == 2:
            start_date_user, end_date_user = user_date_range
            
            filtered_user_daily_df = user_daily_df[
                (user_daily_df['created_at'].dt.date >= start_date_user) &
                (user_daily_df['created_at'].dt.date <= end_date_user)
            ]

            user_df = filtered_user_daily_df.groupby('user_name').agg(
                usage_count=('usage_count', 'sum'),
                feedback_count=('feedback_count', 'sum')
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
                else:
                    df_to_plot = user_df.sort_values('usage_count', ascending=False)
                    title_text = "用户提问量 vs 反馈量"

                df_to_plot.sort_values('usage_count', ascending=True, inplace=True)
                
                fig_user = px.bar(
                    df_to_plot, y='user', x=['usage_count', 'feedback_count'],
                    orientation='h', barmode='group',
                    labels={'value': '数量', 'user': '用户', 'variable': '指标'},
                    template="plotly_white",
                    height=max(400, len(df_to_plot) * 40), text_auto=True
                )
                fig_user.update_layout(legend_title_text='', yaxis_title=None, title_text=title_text, title_x=0.5)
                fig_user.update_traces(textposition='outside')
                st.plotly_chart(fig_user, use_container_width=True)
                
                with st.expander("查看用户统计明细数据"):
                    display_df = df_to_plot.sort_values('usage_count', ascending=False)
                    st.dataframe(display_df.style.format({'usage_count': '{:,}', 'feedback_count': '{:,}'}))
                    
                    csv_user = convert_df_to_csv(display_df)
                    time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="下载用户使用数据(CSV)",
                        data=csv_user,
                        file_name=f'user_use_data_{time_str}.csv',
                        mime='text/csv',
                    )
            else:
                st.info("在选定时间范围内没有用户数据。")
    else:
        st.info("没有用户统计数据。")

if __name__ == "__main__":
    main()