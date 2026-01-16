import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, date
import plotly.express as px
from io import BytesIO
from streamlit_modal import Modal
import streamlit.components.v1 as components

# 导入自定义样式
from styles import apply_custom_styles, show_custom_badge, create_metric_card

# --- Helper Functions ---

def reset_pagination():
    """Callback to reset the page number to 1."""
    if 'page' in st.session_state:
        st.session_state.page = 1

def load_feedback_details(file_path):
    """
    加载反馈明细数据
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except FileNotFoundError:
        st.error(f"错误：找不到反馈明细文件。请确保 '{file_path}' 存在。")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"加载反馈明细数据时出错: {e}")
        return pd.DataFrame()

def get_rating_badge(rating_type):
    """
    根据反馈类型返回对应的徽章样式
    """
    if rating_type == "good":
        return "🟢 好评"
    elif rating_type == "bad":
        return "🔴 差评"
    elif rating_type == "improve":
        return "🟡 待改进"
    else:
        return "⚪ 未知"

def format_datetime(dt_str):
    """
    格式化日期时间显示
    """
    if not dt_str:
        return ""
    try:
        dt = pd.to_datetime(dt_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str

def truncate_text(text, max_length=100):
    """
    截断文本并添加省略号
    """
    if not text or len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def df_to_xlsx(df: pd.DataFrame) -> bytes:
    """将DataFrame转换为XLSX格式的字节流"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='FeedbackDetails')
    processed_data = output.getvalue()
    return processed_data

# 新增：复制到剪贴板（无需外部库）
def render_copy_button(copy_text: str, unique_key: str) -> None:
    """
    渲染一个复制按钮，点击后将 copy_text 复制到剪贴板。
    通过内嵌 HTML/JS 实现，避免第三方包兼容性问题。
    """
    if not copy_text:
        return
    safe_js_text = json.dumps(str(copy_text))
    components.html(
        f"""
        <div style='display:flex; justify-content:flex-end;'>
            <button id="copybtn-{unique_key}" style="padding:6px 10px; border:1px solid #ddd; border-radius:6px; background:#f8f9fa; cursor:pointer;">
                复制
            </button>
        </div>
        <script>
        const textToCopy = {safe_js_text};
        const btn = document.getElementById("copybtn-{unique_key}");
        if (btn) {{
          btn.addEventListener('click', async () => {{
            try {{
              await navigator.clipboard.writeText(textToCopy);
              const old = btn.innerText;
              btn.innerText = '已复制';
              setTimeout(() => btn.innerText = old, 1500);
            }} catch (e) {{
              const old = btn.innerText;
              btn.innerText = '复制失败';
              setTimeout(() => btn.innerText = old, 1500);
            }}
          }});
        }}
        </script>
        """,
        height=40,
    )

def show_feedback_details_page():
    """
    显示反馈明细页面 - 表格版本
    """
    # 初始化 session state
    if 'page' not in st.session_state:
        st.session_state.page = 1
        
    # 定义回调函数，用于在用户通过输入框改变页码时，更新实际的页码状态
    def update_page_from_jumper():
        st.session_state.page = st.session_state.page_jumper
        
    # 应用自定义样式
    apply_custom_styles()
    
    # 页面标题
    st.markdown('<h1 class="custom-title">💬 用户反馈明细</h1>', unsafe_allow_html=True)
    st.caption("查看所有用户反馈的详细信息，支持筛选和查看完整内容")
    
    # 查找最新的反馈明细文件
    data_dir = Path(__file__).parent / "df_data"
    list_of_files = list(data_dir.glob('*_feedback_details.json'))
    
    if not list_of_files:
        st.markdown("""
        <div class="alert-warning">
            <strong>⚠️ 提示:</strong> 找不到反馈明细数据文件。请先运行数据生成脚本。
        </div>
        """, unsafe_allow_html=True)
        return
    
    latest_file = max(list_of_files, key=lambda p: p.stat().st_mtime)
    
    # 加载数据
    with st.spinner('正在加载反馈数据...'):
        feedback_df = load_feedback_details(latest_file)
    
    if feedback_df.empty:
        st.markdown("""
        <div class="alert-warning">
            <strong>ℹ️ 信息:</strong> 没有反馈数据可显示。
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 数据预处理
    feedback_df['created_at'] = pd.to_datetime(feedback_df['created_at'], errors='coerce')
    feedback_df = feedback_df.dropna(subset=['created_at'])
    feedback_df = feedback_df.sort_values('created_at', ascending=False)
    
    # 侧边栏过滤器
    with st.sidebar:
        st.header("🔍 筛选条件")

        # 日期范围筛选
        if not feedback_df.empty:
            FIXED_MIN_DATE = date(2026, 1, 13)

            min_date = max(feedback_df['created_at'].min().date(), FIXED_MIN_DATE)
            max_date = max(feedback_df['created_at'].max().date(), FIXED_MIN_DATE)

            date_range = st.date_input(
                "选择时间范围",
                value=(min_date, max_date),
                min_value=FIXED_MIN_DATE,
                max_value=max_date,
                help="筛选指定时间范围内的反馈",
                on_change=reset_pagination
            )

        # 用户筛选
        users = ['全部'] + sorted(feedback_df['user_name'].unique().tolist())
        selected_user = st.selectbox("选择用户", users, help="筛选特定用户的反馈", on_change=reset_pagination)
        
        # 反馈类型筛选
        feedback_types = ['全部'] + sorted(feedback_df['good_or_bad'].unique().tolist())
        selected_type = st.selectbox("反馈类型", feedback_types, help="筛选特定类型的反馈", on_change=reset_pagination)
        
        # 模型筛选
        models = ['全部'] + sorted([m for m in feedback_df['model'].unique().tolist() if m])
        selected_model = st.selectbox("选择模型", models, help="筛选特定模型的反馈", on_change=reset_pagination)
        
        # 新增：按问题内容搜索
        query_search = st.text_input("搜索问题内容", placeholder="输入关键词筛选...", on_change=reset_pagination)
        
        # 排序选项
        sort_options = {
            "时间 (最新在前)": ("created_at", False),
            "时间 (最早在前)": ("created_at", True),
            "用户名": ("user_name", True),
            "反馈类型": ("good_or_bad", True)
        }
        selected_sort = st.selectbox("排序方式", list(sort_options.keys()), on_change=reset_pagination)
    
    # 应用筛选条件
    filtered_df = feedback_df.copy()
    original_count = len(filtered_df)
    
    # 日期筛选
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['created_at'].dt.date >= start_date) &
            (filtered_df['created_at'].dt.date <= end_date)
        ]
    
    # 用户筛选
    if selected_user != '全部':
        filtered_df = filtered_df[filtered_df['user_name'] == selected_user]
    
    # 反馈类型筛选
    if selected_type != '全部':
        filtered_df = filtered_df[filtered_df['good_or_bad'] == selected_type]
    
    # 模型筛选
    if selected_model != '全部':
        filtered_df = filtered_df[filtered_df['model'] == selected_model]
    
    # 应用问题内容筛选
    if query_search:
        filtered_df = filtered_df[filtered_df['query'].str.contains(query_search, na=False, case=False)]
    
    # 应用排序
    sort_column, ascending = sort_options[selected_sort]
    filtered_df = filtered_df.sort_values(sort_column, ascending=ascending)
    
    # 显示筛选反馈
    filtered_count = len(filtered_df)
    if filtered_count != original_count:
        st.markdown(f"""
        <div class="filter-feedback">
            ✅ 筛选完成！从 {original_count} 条记录中筛选出 {filtered_count} 条符合条件的反馈
        </div>
        """, unsafe_allow_html=True)
    
    # 显示统计信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(create_metric_card("总反馈数", f"{len(filtered_df):,}"), unsafe_allow_html=True)
    with col2:
        good_count = len(filtered_df[filtered_df['good_or_bad'] == 'good'])
        st.markdown(create_metric_card("好评数", f"{good_count:,}"), unsafe_allow_html=True)
    with col3:
        bad_count = len(filtered_df[filtered_df['good_or_bad'] == 'bad'])
        st.markdown(create_metric_card("差评数", f"{bad_count:,}"), unsafe_allow_html=True)
    with col4:
        improve_count = len(filtered_df[filtered_df['good_or_bad'] == 'improve'])
        st.markdown(create_metric_card("待改进数", f"{improve_count:,}"), unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 反馈分布图表
    if not filtered_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            # 反馈类型分布
            type_counts = filtered_df['good_or_bad'].value_counts()
            if not type_counts.empty:
                fig_pie = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title="反馈类型分布",
                    color_discrete_map={
                        'good': '#28a745',    # 绿色
                        'bad': '#dc3545',     # 红色
                        'improve': '#87CEFA'  # 浅蓝色
                    }
                )
                fig_pie.update_layout(
                    height=300,
                    font=dict(size=12),
                    title_font_size=16,
                    title_x=0.5
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="plot-container">', unsafe_allow_html=True)
            # 每日反馈趋势
            daily_feedback = filtered_df.groupby(filtered_df['created_at'].dt.date).size().reset_index(name='count')
            if not daily_feedback.empty:
                fig_line = px.line(
                    daily_feedback,
                    x='created_at',
                    y='count',
                    title="每日反馈趋势",
                    labels={'created_at': '日期', 'count': '反馈数量'}
                )
                fig_line.update_layout(
                    height=300,
                    font=dict(size=12),
                    title_font_size=16,
                    title_x=0.5
                )
                fig_line.update_traces(line_color='#1f77b4', line_width=3)
                st.plotly_chart(fig_line, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 主要内容：反馈表格
    if filtered_df.empty:
        st.markdown("""
        <div class="alert-warning">
            <strong>ℹ️ 信息:</strong> 没有符合筛选条件的反馈数据。
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 分页控制
    st.markdown("### 📋 反馈明细")
    
    # 计算分页数据
    total_items = len(filtered_df)
    
    # 优化的分页控制
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        items_per_page = st.selectbox(
            "每页显示",
            options=[10, 20, 50, 100],
            index=1,
            help="选择每页显示的反馈数量",
            on_change=reset_pagination
        )
    
    # 重新计算总页数
    total_pages = (total_items - 1) // items_per_page + 1 if total_items > 0 else 1
    
    # 确保当前页码在有效范围内
    if st.session_state.page > total_pages:
        st.session_state.page = total_pages
        
    # 在渲染跳转输入框之前，确保其值与当前的页码状态一致。
    # 这可以防止点击“下一页”等按钮后，输入框不更新的问题。
    if st.session_state.get("page_jumper") != st.session_state.page:
        st.session_state.page_jumper = st.session_state.page
        
    with col2:
        # 显示数据统计信息
        st.info(f"📊 共 {total_items} 条反馈，分 {total_pages} 页显示")
    
    with col3:
        # 使用新的 key 和回调来避免状态冲突
        st.number_input(
            "跳转到页",
            min_value=1,
            max_value=total_pages,
            key="page_jumper",
            on_change=update_page_from_jumper,
            help="输入页码直接跳转"
        )
    
    # 计算当前页数据
    start_idx = (st.session_state.page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    current_page_df = filtered_df.iloc[start_idx:end_idx]
    
    # 显示反馈表格（使用Streamlit原生组件）
    display_feedback_table(current_page_df)
    
    # 页面导航
    if total_pages > 1:
        st.markdown("---")
        st.markdown("### 📄 页面导航")
        
        # 创建导航按钮布局
        nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 2, 1, 1])
        
        with nav_col1:
            if st.button("⏮️ 首页", help="跳转到第一页", use_container_width=True, disabled=st.session_state.page <= 1):
                st.session_state.page = 1
                st.rerun()
        
        with nav_col2:
            if st.button("⬅️ 上一页", help="跳转到上一页", use_container_width=True, disabled=st.session_state.page <= 1):
                st.session_state.page -= 1
                st.rerun()
        
        with nav_col3:
            # 显示当前页面信息
            st.markdown(f"""
            <div style="text-align: center; padding: 0.5rem; background: #f8f9fa; border-radius: 5px; border: 1px solid #dee2e6;">
                <strong>第 {st.session_state.page} 页 / 共 {total_pages} 页</strong>
                <br>
                <small style="color: #6c757d;">显示第 {start_idx + 1}-{min(end_idx, total_items)} 条，共 {total_items} 条记录</small>
            </div>
            """, unsafe_allow_html=True)
        
        with nav_col4:
            if st.button("下一页 ➡️", help="跳转到下一页", use_container_width=True, disabled=st.session_state.page >= total_pages):
                st.session_state.page += 1
                st.rerun()
        
        with nav_col5:
            if st.button("末页 ⏭️", help="跳转到最后一页", use_container_width=True, disabled=st.session_state.page >= total_pages):
                st.session_state.page = total_pages
                st.rerun()
    
    # 数据导出功能
    st.markdown("---")
    with st.expander("📥 数据导出"):
        st.markdown("### 导出筛选后的数据")
        
        # 准备导出数据
        export_df = filtered_df.copy()
        export_df['created_at'] = export_df['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 重命名列名为中文
        export_df = export_df.rename(columns={
            'feedback_id': '反馈ID',
            'message_id': '消息ID',
            'user_name': '用户名',
            'created_at': '创建时间',
            'good_or_bad': '反馈类型',
            'model': '模型',
            'rating_score': '评分',
            'rating_comment': '评论内容',
            'query': '用户问题',
            'answer': 'AI回答'
        })
        # 选择要导出的列
        export_columns = st.multiselect(
            "选择要导出的列",
            options=export_df.columns.tolist(),
            default=['用户名', '创建时间', '反馈类型', '模型', '评论内容','用户问题','AI回答'],
            help="自定义选择要导出的数据列"
        )
        
        if export_columns:
            xlsx_data = df_to_xlsx(export_df[export_columns])
            st.download_button(
                label="⬇️ 下载自定义文件 (XLSX)",
                data=xlsx_data,
                file_name=f"feedback_custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="下载自定义选择的反馈数据"
            )

def display_feedback_table(df):
    """
    使用更简洁的表格布局显示反馈数据，并提供详情展开功能
    """
    if df.empty:
        st.info("没有数据可显示")
        return

    # 定义表头
    header_cols = st.columns([1.5, 1, 1, 4, 1])
    headers = ["时间", "用户", "反馈类型", "用户问题", "反馈明细"]
    for col, header in zip(header_cols, headers):
        col.markdown(f"**{header}**")

    st.markdown("---")

    # 渲染每一行数据
    for idx, row in df.iterrows():
        cols = st.columns([1.5, 1, 1, 4, 1])
        
        # 基本信息
        cols[0].markdown(f"`{format_datetime(row['created_at'])}`")
        cols[1].markdown(row['user_name'])
        
        # 反馈类型徽章
        rating_type = row['good_or_bad']
        if rating_type == 'good':
            badge_text = '🟢 好评'
        elif rating_type == 'bad':
            badge_text = '🔴 差评'
        elif rating_type == 'improve':
            badge_text = '🟡 待改进'
        else:
            badge_text = '⚪ 未知'
        cols[2].markdown(badge_text)

        # 用户问题预览
        query_text = row.get('query') or ""
        query_preview = truncate_text(query_text, 80)
        cols[3].markdown(f'<div title="{query_text}">{query_preview or "无问题内容"}</div>', unsafe_allow_html=True)

        # 操作按钮
        detail_key = f"detail_btn_{row['feedback_id']}"
        
        modal = Modal(
            "反馈详细信息",
            key=f"modal_{row['feedback_id']}",
            padding=20,
            max_width=1000
        )
        
        if cols[4].button("查看详情", key=detail_key, use_container_width=True):
            with modal.container():
                show_feedback_detail_inline(row)
        
        st.markdown("---")


def show_feedback_detail_inline(row):
    """
    在对话框中以左右布局显示反馈详情
    """
    left_col, right_col = st.columns([2, 5])
    
    with left_col:
        with st.container(height=500):
            st.markdown("**📝 用户问题**")
            if row.get('query'):
                st.markdown(f"<div class='content-highlight'>{row['query']}</div>", unsafe_allow_html=True)
            else:
                st.info("无问题内容")
                
            st.markdown("**💭 用户评论**")
            if row.get('rating_comment'):
                st.markdown(f"<div class='comment-highlight'>{row['rating_comment']}</div>", unsafe_allow_html=True)
            else:
                st.info("无评论内容")

            st.markdown("---")
            st.markdown(f"**🤖 模型:** `{row.get('model') or 'N/A'}`")
            st.markdown(f"**Feedback ID:**")
            st.code(row['feedback_id'], language=None)
            st.markdown(f"**Message ID:**")
            st.code(row.get('message_id') or 'N/A', language=None)

    with right_col:
        with st.container(height=500):
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                st.markdown("**💬 AI回答**")
            
            answer_text = row.get('answer') or ""

            with col2:
                if answer_text:
                    render_copy_button(answer_text, f"ans_{row['feedback_id']}")

            if answer_text:
                st.markdown(answer_text, unsafe_allow_html=True)
            else:
                st.info("无回答内容")

if __name__ == "__main__":
    show_feedback_details_page() 