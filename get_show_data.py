## 该函数功能
# 1. 获取chat表的所有数据
# 2. 获取feedback表的所有数据
# 3. 汇总数据：1）汇总所有数据的使用量和反馈量，不同模型的调用量和反馈量，汇总不同user使用量和反馈量，
#          2）然后按天进行汇总使用量和反馈量，按天进行汇总不同user使用量和反馈量
# 4. 保存数据为json格式
import pandas as pd
import json
import datetime
import logging
from pathlib import Path

# 从重构后的模块中导入函数
from chat_data import get_chat_data
from feedback_data_v2 import get_feedback_data

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s- %(funcName)s - %(lineno)d - %(levelname)s - %(message)s' # 统一为详细日志格式
)
logger = logging.getLogger(__name__)


def generate_summary_stats(chat_df: pd.DataFrame, feedback_df: pd.DataFrame) -> dict:
    """
    根据聊天和反馈数据生成汇总统计信息。

    Args:
        chat_df: 包含聊天数据的DataFrame。
        feedback_df: 包含反馈数据的DataFrame。

    Returns:
        dict: 包含所有汇总统计信息的多层字典。
    """
    summary = {}

    # 确保日期列是datetime类型，以便进行时间序列分析
    chat_df['created_at'] = pd.to_datetime(chat_df['created_at'], errors='coerce')
    feedback_df['created_at'] = pd.to_datetime(feedback_df['created_at'], errors='coerce')

    # 删除缺少关键信息的行
    chat_df.dropna(subset=['created_at', 'user_name', 'last_chat_model'], inplace=True)
    feedback_df.dropna(subset=['created_at', 'user_name', 'model'], inplace=True)

    # 替换模型名称
    chat_df['last_chat_model'] = chat_df['last_chat_model'].replace('星伴V1.1', '聆境 1.1').replace('聆镜 1.1',
                                                                                                    '聆境 1.1')
    feedback_df['model'] = feedback_df['model'].replace('星伴V1.1', '聆境 1.1').replace('聆镜 1.1', '聆境 1.1')

    not_use_model_list = ["星伴V1.1", "星伴v1.2", "arena-model"]
    chat_df = chat_df[~chat_df['last_chat_model'].isin(not_use_model_list)]
    feedback_df = feedback_df[~feedback_df['model'].isin(not_use_model_list)]

    # 计算文字量统计（新增功能）
    # 用户输入文字量（字符数）
    chat_df['user_text_length'] = chat_df['content'].astype(str).str.len()
    # AI输出文字量（字符数）
    chat_df['ai_text_length'] = chat_df['respond_content'].astype(str).str.len()

    # 1. 总体统计（添加文字量统计）
    summary['overall_stats'] = {
        'total_chats': int(chat_df['chat_id'].nunique()),
        'total_user_queries': len(chat_df),
        'total_feedbacks': len(feedback_df),
        'feedback_ratio': len(feedback_df) / len(chat_df) if len(chat_df) > 0 else 0,
        'total_user_text_length': int(chat_df['user_text_length'].sum()),
        'total_ai_text_length': int(chat_df['ai_text_length'].sum()),
    }

    # 2. 按模型统计（添加文字量统计）
    model_usage = chat_df['last_chat_model'].value_counts().to_dict()
    model_feedback = feedback_df['model'].value_counts().to_dict()
    model_user_text = chat_df.groupby('last_chat_model')['user_text_length'].sum().to_dict()
    model_ai_text = chat_df.groupby('last_chat_model')['ai_text_length'].sum().to_dict()

    model_stats = {
        model: {
            'usage_count': model_usage.get(model, 0),
            'feedback_count': model_feedback.get(model, 0),
            'user_text_length': int(model_user_text.get(model, 0)),
            'ai_text_length': int(model_ai_text.get(model, 0))
        } for model in set(model_usage) | set(model_feedback)
    }
    summary['model_stats'] = model_stats

    # 3. 按用户统计（添加文字量统计）
    user_usage = chat_df['user_name'].value_counts().to_dict()
    user_feedback = feedback_df['user_name'].value_counts().to_dict()
    user_user_text = chat_df.groupby('user_name')['user_text_length'].sum().to_dict()
    user_ai_text = chat_df.groupby('user_name')['ai_text_length'].sum().to_dict()

    user_stats = {
        user: {
            'usage_count': user_usage.get(user, 0),
            'feedback_count': user_feedback.get(user, 0),
            'user_text_length': int(user_user_text.get(user, 0)),
            'ai_text_length': int(user_ai_text.get(user, 0))
        } for user in set(user_usage) | set(user_feedback)
    }
    summary['user_stats'] = user_stats

    # 4. 按天统计（添加文字量统计）
    daily_usage = chat_df.set_index('created_at').resample('D').size().to_frame('count')
    daily_feedback = feedback_df.set_index('created_at').resample('D').size().to_frame('count')
    daily_user_text = chat_df.set_index('created_at').resample('D')['user_text_length'].sum().to_frame(
        'user_text_length')
    daily_ai_text = chat_df.set_index('created_at').resample('D')['ai_text_length'].sum().to_frame('ai_text_length')

    daily_stats = pd.merge(daily_usage, daily_feedback, left_index=True, right_index=True, how='outer').fillna(0)
    daily_stats = pd.merge(daily_stats, daily_user_text, left_index=True, right_index=True, how='outer').fillna(0)
    daily_stats = pd.merge(daily_stats, daily_ai_text, left_index=True, right_index=True, how='outer').fillna(0)

    daily_stats.rename(columns={'count_x': 'usage_count', 'count_y': 'feedback_count'}, inplace=True)

    # 4.1. 按天统计好评和差评
    if not feedback_df.empty and 'good_or_bad' in feedback_df.columns:
        daily_feedback_by_rating = feedback_df.groupby(
            [pd.Grouper(key='created_at', freq='D'), 'good_or_bad']).size().unstack(fill_value=0)
        # 确保'good'和'bad'列存在
        if 'good' not in daily_feedback_by_rating.columns:
            daily_feedback_by_rating['good'] = 0
        if 'bad' not in daily_feedback_by_rating.columns:
            daily_feedback_by_rating['bad'] = 0
        if 'improve' not in daily_feedback_by_rating.columns:
            daily_feedback_by_rating['improve'] = 0

        daily_stats = daily_stats.join(daily_feedback_by_rating[['good', 'bad', 'improve']], how='outer').fillna(0)
    else:
        daily_stats['good'] = 0
        daily_stats['bad'] = 0
        daily_stats['improve'] = 0

    # 4.2. 计算各种率
    daily_stats['feedback_ratio'] = (daily_stats['feedback_count'] / daily_stats['usage_count']).where(
        daily_stats['usage_count'] > 0, 0)
    daily_stats['excellent_rate'] = (daily_stats['good'] / daily_stats['usage_count']).where(
        daily_stats['usage_count'] > 0, 0)
    daily_stats['error_rate'] = (daily_stats['bad'] / daily_stats['usage_count']).where(daily_stats['usage_count'] > 0,
                                                                                        0)
    daily_stats['improve_rate'] = (daily_stats['improve'] / daily_stats['usage_count']).where(
        daily_stats['usage_count'] > 0, 0)

    # 将浮点计数值转换为整数
    daily_stats[['usage_count', 'feedback_count', 'good', 'bad', 'improve', 'user_text_length', 'ai_text_length']] = \
    daily_stats[
        ['usage_count', 'feedback_count', 'good', 'bad', 'improve', 'user_text_length', 'ai_text_length']].astype(int)

    # 将DatetimeIndex转换为字符串，以确保JSON序列化兼容性
    daily_stats.index = daily_stats.index.strftime('%Y-%m-%d')
    summary['daily_stats'] = daily_stats.to_dict('index')

    # 5. 按天和用户统计 (修改为列表形式，添加文字量统计)
    daily_user_usage = chat_df.groupby([pd.Grouper(key='created_at', freq='D'), 'user_name']).size().reset_index(
        name='usage_count')
    daily_user_feedback = feedback_df.groupby([pd.Grouper(key='created_at', freq='D'), 'user_name']).size().reset_index(
        name='feedback_count')
    daily_user_text = chat_df.groupby([pd.Grouper(key='created_at', freq='D'), 'user_name'])[
        'user_text_length'].sum().reset_index(name='user_text_length')
    daily_ai_text = chat_df.groupby([pd.Grouper(key='created_at', freq='D'), 'user_name'])[
        'ai_text_length'].sum().reset_index(name='ai_text_length')

    # 将日期转换为字符串
    daily_user_usage['created_at'] = daily_user_usage['created_at'].dt.strftime('%Y-%m-%d')
    daily_user_feedback['created_at'] = daily_user_feedback['created_at'].dt.strftime('%Y-%m-%d')
    daily_user_text['created_at'] = daily_user_text['created_at'].dt.strftime('%Y-%m-%d')
    daily_ai_text['created_at'] = daily_ai_text['created_at'].dt.strftime('%Y-%m-%d')

    # 合并使用和反馈数据
    daily_user_stats_df = pd.merge(
        daily_user_usage,
        daily_user_feedback,
        on=['created_at', 'user_name'],
        how='outer'
    ).fillna(0)

    # 合并文字量数据
    daily_user_stats_df = pd.merge(
        daily_user_stats_df,
        daily_user_text,
        on=['created_at', 'user_name'],
        how='outer'
    ).fillna(0)

    daily_user_stats_df = pd.merge(
        daily_user_stats_df,
        daily_ai_text,
        on=['created_at', 'user_name'],
        how='outer'
    ).fillna(0)

    # 转换数据类型
    daily_user_stats_df['usage_count'] = daily_user_stats_df['usage_count'].astype(int)
    daily_user_stats_df['feedback_count'] = daily_user_stats_df['feedback_count'].astype(int)
    daily_user_stats_df['user_text_length'] = daily_user_stats_df['user_text_length'].astype(int)
    daily_user_stats_df['ai_text_length'] = daily_user_stats_df['ai_text_length'].astype(int)

    # 转换为字典列表
    summary['daily_user_stats'] = daily_user_stats_df.to_dict('records')

    return summary

def default_json_serializer(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))

def save_all_data(chat_df,feedback_df):
    """
    保存所有数据
    """
    output_dir = Path(__file__).parent / "df_data"
    output_dir.mkdir(exist_ok=True)
    time_now=datetime.datetime.now().strftime("%Y-%m-%d")
    chat_df.to_csv(output_dir / f"{time_now}_chat_data.csv",index=False,encoding="utf-8-sig")
    feedback_df.to_csv(output_dir / f"{time_now}_feedback_data.csv",index=False,encoding="utf-8-sig")
    
    # 保存详细的反馈数据为JSON格式（用于dashboard查看）
    if not feedback_df.empty:
        # 准备用于前端展示的反馈明细数据
        feedback_detail_data = []
        for _, row in feedback_df.iterrows():
            feedback_detail_data.append({
                "feedback_id": str(row['feedback_id']) if pd.notna(row['feedback_id']) else None,
                "user_name": str(row['user_name']) if pd.notna(row['user_name']) else "",
                "created_at": row['created_at'].isoformat() if pd.notna(row['created_at']) else None,
                "good_or_bad": str(row['good_or_bad']) if pd.notna(row['good_or_bad']) else "",
                "model": str(row['model']) if pd.notna(row['model']) else "",
                "rating_score": float(row['rating_score']) if pd.notna(row['rating_score']) and row['rating_score'] != -99 else None,
                "rating_comment": str(row['rating_comment']) if pd.notna(row['rating_comment']) else "",
                "query": str(row['query']) if pd.notna(row['query']) else "",
                "answer": str(row['answer']) if pd.notna(row['answer']) else "",
                "message_id": str(row['message_id']) if pd.notna(row['message_id']) else ""
            })
        
        # 保存反馈明细数据
        feedback_detail_path = output_dir / f"{time_now}_feedback_details.json"
        try:
            with open(feedback_detail_path, 'w', encoding='utf-8') as f:
                json.dump(feedback_detail_data, f, ensure_ascii=False, indent=2, default=default_json_serializer)
            logger.info(f"反馈明细数据成功保存到: {feedback_detail_path}")
        except Exception as e:
            logger.error(f"保存反馈明细JSON文件时出错: {e}")
    
    logger.info(f"明细数据成功保存到: {output_dir}")

if __name__ == "__main__":
    # 定义数据库路径
    import argparse
    parser = argparse.ArgumentParser(description='获取和处理数据')
    parser.add_argument('--db_path', type=str, default='/root/autodl-tmp/dev/open_webui/backend/data/webui.db', help='数据库路径')
    args = parser.parse_args()
    db_path = args.db_path
    
    logger.info("开始获取和处理数据...")
    
    # 1. 获取聊天和反馈数据
    chat_df = get_chat_data(db_path)
    feedback_df = get_feedback_data(db_path)


    if chat_df.empty:
        logger.warning("聊天数据为空，无法生成统计信息。")
    else:
        # 2. 生成汇总统计
        logger.info("数据获取成功，开始生成汇总统计...")
        summary_data = generate_summary_stats(chat_df, feedback_df)
        
        # 可选：保存详细的DataFrame数据
        save_all_data(chat_df, feedback_df)

        # 3. 保存数据为JSON文件
        output_dir = Path(__file__).parent
        # 将统计文件也保存到 df_data 目录中
        output_data_dir = output_dir / "df_data"
        output_data_dir.mkdir(exist_ok=True)
        time_now = datetime.datetime.now().strftime("%Y-%m-%d")
        output_path = output_data_dir / f"{time_now}_summary_stats.json"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, ensure_ascii=False, indent=4, default=default_json_serializer)
            logger.info(f"统计数据成功保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存JSON文件时出错: {e}")