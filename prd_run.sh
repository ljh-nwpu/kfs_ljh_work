#!/bin/bash
# 激活conda环境
echo "开始激活conda环境"
source /root/miniconda3/etc/profile.d/conda.sh
conda activate base
echo "conda环境激活成功"
# 定义根目录
ROOT_DIR="/root/autodl-tmp/kfs_bi"
LOG_FILE="$ROOT_DIR/df_data/cron_job.log"

# 输出当前时间到日志
# echo "==== $(date '+%Y-%m-%d %H:%M:%S') ====" >> $LOG_FILE

# 进入工作目录并执行脚本
cd $ROOT_DIR
python get_show_data.py --db_path /root/autodl-tmp/open_webui/backend/data/webui.db >> $LOG_FILE 2>&1
echo "执行脚本成功,时间:$(date '+%Y-%m-%d %H:%M:%S'),save log to $LOG_FILE"

# 输出执行结果
if [ $? -eq 0 ]; then
    echo "执行成功" >> $LOG_FILE
else
    echo "执行失败" >> $LOG_FILE
fi