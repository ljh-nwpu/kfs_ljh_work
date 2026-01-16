import streamlit as st

def apply_custom_styles():
    """
    应用自定义CSS样式
    """
    st.markdown("""
    <style>
    /* ------------------- 全局与基础样式 ------------------- */
    :root {
        --primary-color: #4a69bd; /* 主要颜色 - 柔和的蓝紫色 */
        --secondary-color: #6a89cc; /* 次要颜色 */
        --accent-color: #f6b93b;  /* 强调色 - 金色 */
        --text-color: #34495e; /* 主要文本颜色 - 深蓝灰色 */
        --light-text-color: #7f8c8d; /* 次要文本颜色 */
        --bg-color: #f8f9fa; /* 主背景色 */
        --card-bg-color: #ffffff; /* 卡片背景色 */
        --border-color: #e5e7eb; /* 边框颜色 */
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: var(--text-color);
    }
    
    .main {
        padding: 2rem;
        background-color: var(--bg-color);
    }

    /* ------------------- 标题与文本 ------------------- */
    .custom-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-align: left;
        color: var(--text-color);
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--text-color);
        font-weight: 600;
    }
    
    st.caption {
        color: var(--light-text-color);
    }

    /* ------------------- 卡片与容器 ------------------- */
    .metric-card, .feedback-card, .filter-container, .nav-container {
        background-color: var(--card-bg-color);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
    }

    .metric-card:hover, .feedback-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px rgba(0, 0, 0, 0.06);
    }

    .metric-card {
        border-left: 5px solid var(--primary-color);
    }

    .filter-container {
        margin-bottom: 1.5rem;
    }

    /* ------------------- 内容高亮与徽章 ------------------- */
    .content-highlight {
        background: #e9ecef;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid var(--primary-color);
        margin: 0.5rem 0;
    }
    
    .comment-highlight {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid var(--accent-color);
        margin: 0.5rem 0;
    }

    .status-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 600;
        text-align: center;
    }

    .badge-success { background-color: #d1fae5; color: #065f46; }
    .badge-danger { background-color: #fee2e2; color: #991b1b; }
    .badge-warning { background-color: #fef3c7; color: #92400e; }
    .badge-secondary { background-color: #e5e7eb; color: #4b5563; }

    /* ------------------- UI组件 (按钮, 代码块等) ------------------- */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        background-color: var(--primary-color);
        color: white;
        border: none;
    }
    
    .stButton > button:hover {
        background-color: var(--secondary-color);
    }

    .stCode, code {
        background-color: #eef2f7 !important;
        border: 1px solid #dbe1e8 !important;
        border-radius: 6px !important;
        color: #39434f;
        padding: 0.2em 0.4em;
    }

    /* ------------------- Modal弹窗样式微调 ------------------- */
    div[data-testid="stModal"] {
        /* 将弹窗从页面顶部对齐，而不是垂直居中 */
        align-items: flex-start;
        /* 增加一些距离顶部的内边距 */
        padding-top: 5rem;
    }

    /* ------------------- 响应式设计 ------------------- */
    @media (max-width: 768px) {
        .custom-title { font-size: 1.8rem; }
        .main { padding: 1rem; }
        .metric-card, .feedback-card { padding: 1rem; }
    }
    </style>
    """, unsafe_allow_html=True)

def show_custom_badge(rating_type, text=None):
    """
    显示自定义徽章
    """
    if text is None:
        text = rating_type
    
    badge_class = {
        'good': 'badge-good',
        'bad': 'badge-bad', 
        'improve': 'badge-improve'
    }.get(rating_type, 'badge-good')
    
    return f'<span class="{badge_class}">🟢 {text}</span>' if rating_type == 'good' else \
           f'<span class="{badge_class}">🔴 {text}</span>' if rating_type == 'bad' else \
           f'<span class="{badge_class}">🟡 {text}</span>'

def create_metric_card(title, value, delta=None):
    """
    创建自定义统计指标卡片
    """
    delta_html = f'<div style="font-size: 0.8rem; opacity: 0.8;">{delta}</div>' if delta else ''
    
    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{title}</div>
        {delta_html}
    </div>
    """

def create_loading_spinner():
    """
    创建加载动画
    """
    return '<div class="loading-spinner"></div>'

def show_alert(message, alert_type='info'):
    """
    显示自定义警告消息
    """
    alert_class = f'alert-{alert_type}' if alert_type in ['success', 'error', 'warning'] else 'alert-info'
    return f'<div class="{alert_class}">{message}</div>' 