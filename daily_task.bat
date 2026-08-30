@echo off
rem ---- 每日定时更新入口（供 Windows 任务计划调用，也可手动双击） ----
rem 注册计划任务：schtasks /Create /F /SC DAILY /ST 08:00 /TN "EEJobHub-DailyUpdate" /TR "%~f0"
cd /d "%~dp0"
if not exist data\digest mkdir data\digest
"venv\Scripts\python.exe" -X utf8 -m src.daily_update >> "data\digest\task.log" 2>&1
