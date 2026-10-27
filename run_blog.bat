@echo off
REM Windows Task Scheduler eken run karanna use karana file eka
cd /d "%~dp0"
".venv\Scripts\python.exe" auto_blog.py >> blog_log.txt 2>&1
