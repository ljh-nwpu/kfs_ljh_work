#!/usr/bin/env python3
"""
创建测试数据用于演示反馈明细功能
"""

import json
import pandas as pd
from datetime import datetime, timedelta
import random
from pathlib import Path

def create_test_feedback_data():
    """创建测试反馈数据"""
    
    # 测试用户列表
    users = ['张三', '李四', '王五', '赵六', '孙七', '周八', '吴九', '郑十']
    
    # 测试模型列表
    models = ['聆境 1.1', 'GPT-4', 'Claude-3', '星伴V2.0']
    
    # 反馈类型
    feedback_types = ['good', 'bad', 'improve']
    
    # 测试问题和回答
    test_qa_pairs = [
        {
            'query': '请帮我写一个Python函数来计算斐波那契数列',
            'answer': '好的，我来为您写一个计算斐波那契数列的Python函数：\n\n```python\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n```\n\n这个函数使用递归方法计算斐波那契数列的第n项。'
        },
        {
            'query': '如何提高工作效率？',
            'answer': '提高工作效率的几个建议：\n1. 制定明确的目标和计划\n2. 使用时间管理技巧，如番茄工作法\n3. 减少干扰，专注于重要任务\n4. 学会委派和说不\n5. 保持良好的工作习惯和环境'
        },
        {
            'query': '请解释一下机器学习的基本概念',
            'answer': '机器学习是人工智能的一个分支，它让计算机能够从数据中学习并做出预测或决策，而无需明确编程。主要包括：\n\n1. **监督学习**：使用标记数据训练模型\n2. **无监督学习**：从未标记数据中发现模式\n3. **强化学习**：通过与环境交互学习最优策略\n\n常见应用包括图像识别、自然语言处理、推荐系统等。'
        },
        {
            'query': '今天天气怎么样？',
            'answer': '抱歉，我无法获取实时天气信息。建议您：\n1. 查看天气预报应用\n2. 搜索"今日天气 + 您的城市名"\n3. 关注当地气象部门发布的信息\n\n如果您需要其他帮助，请随时告诉我！'
        }
    ]
    
    # 评论内容示例
    comments = {
        'good': [
            '回答很详细，很有帮助！',
            '解释得很清楚，谢谢！',
            '完美的答案，正是我需要的',
            '非常专业的回答',
            '思路清晰，逻辑性强'
        ],
        'bad': [
            '回答不够准确',
            '没有解决我的问题',
            '信息有误，需要修正',
            '回答太简单了',
            '不是我想要的答案'
        ],
        'improve': [
            '回答可以更详细一些',
            '希望能提供更多例子',
            '可以加上一些实际应用场景',
            '建议增加图表说明',
            '希望能有更多的解决方案'
        ]
    }
    
    # 生成测试数据
    feedback_data = []
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(100):  # 生成100条测试数据
        # 随机选择数据
        user = random.choice(users)
        model = random.choice(models)
        feedback_type = random.choice(feedback_types)
        qa_pair = random.choice(test_qa_pairs)
        comment = random.choice(comments[feedback_type]) if random.random() > 0.3 else ""  # 70%概率有评论
        
        # 生成时间（最近30天内）
        days_offset = random.randint(0, 29)
        hours_offset = random.randint(0, 23)
        minutes_offset = random.randint(0, 59)
        created_time = base_date + timedelta(days=days_offset, hours=hours_offset, minutes=minutes_offset)
        
        feedback_item = {
            'feedback_id': f'fb_{i+1:04d}',
            'message_id': f'msg_{random.randint(10000, 99999)}',
            'user_name': user,
            'created_at': created_time.isoformat(),
            'good_or_bad': feedback_type,
            'model': model,
            'rating_score': random.randint(1, 5) if random.random() > 0.5 else None,
            'rating_comment': comment,
            'query': qa_pair['query'],
            'answer': qa_pair['answer']
        }
        
        feedback_data.append(feedback_item)
    
    return feedback_data

def create_test_summary_data():
    """创建测试汇总数据"""
    base_date = datetime.now() - timedelta(days=30)
    
    # 生成每日统计数据
    daily_stats = {}
    for i in range(30):
        date_str = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        daily_stats[date_str] = {
            'usage_count': random.randint(10, 50),
            'feedback_count': random.randint(5, 25),
            'good': random.randint(2, 15),
            'bad': random.randint(0, 5),
            'improve': random.randint(1, 8),
            'feedback_ratio': random.uniform(0.3, 0.8),
            'excellent_rate': random.uniform(0.4, 0.9),
            'error_rate': random.uniform(0.05, 0.2),
            'improve_rate': random.uniform(0.1, 0.4)
        }
    
    summary_data = {
        'overall_stats': {
            'total_chats': 45,
            'total_user_queries': 1200,
            'total_feedbacks': 600,
            'feedback_ratio': 0.5
        },
        'daily_stats': daily_stats,
        'model_stats': {
            '聆境 1.1': {'usage_count': 400, 'feedback_count': 200},
            'GPT-4': {'usage_count': 350, 'feedback_count': 180},
            'Claude-3': {'usage_count': 300, 'feedback_count': 150},
            '星伴V2.0': {'usage_count': 150, 'feedback_count': 70}
        },
        'user_stats': {
            '张三': {'usage_count': 150, 'feedback_count': 75},
            '李四': {'usage_count': 120, 'feedback_count': 60},
            '王五': {'usage_count': 100, 'feedback_count': 50},
            '赵六': {'usage_count': 90, 'feedback_count': 45},
            '孙七': {'usage_count': 80, 'feedback_count': 40},
            '周八': {'usage_count': 70, 'feedback_count': 35},
            '吴九': {'usage_count': 60, 'feedback_count': 30},
            '郑十': {'usage_count': 50, 'feedback_count': 25}
        },
        'daily_user_stats': []  # 简化起见，这里留空
    }
    
    return summary_data

def main():
    """主函数"""
    print("🚀 正在创建测试数据...")
    
    # 创建df_data目录
    data_dir = Path(__file__).parent / "df_data"
    data_dir.mkdir(exist_ok=True)
    
    # 生成当前日期字符串
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 创建反馈明细数据
    feedback_data = create_test_feedback_data()
    feedback_file = data_dir / f"{date_str}_feedback_details.json"
    
    with open(feedback_file, 'w', encoding='utf-8') as f:
        json.dump(feedback_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 反馈明细数据已保存到: {feedback_file}")
    print(f"   生成了 {len(feedback_data)} 条反馈记录")
    
    # 创建汇总统计数据
    summary_data = create_test_summary_data()
    summary_file = data_dir / f"{date_str}_summary_stats.json"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 汇总统计数据已保存到: {summary_file}")
    
    print("\n🎉 测试数据创建完成！")
    print("现在可以运行以下命令启动dashboard：")
    print("streamlit run dashboard.py")

if __name__ == "__main__":
    main() 