@echo off
call E:\anaconda3\Scripts\activate.bat kfs_bi-master

cd /d C:\Users\15215\Desktop\kfs_bi-master

python get_show_data.py --db_path C:\Users\15215\Desktop\kfs_bi-master\webui.db

pause
