@echo off
rem Botni ishga tushirish (Windows). Birinchi safar venv yaratadi va kutubxonalarni o'rnatadi.
cd /d "%~dp0..\.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
if not exist venv (
  py -3 -m venv venv || python -m venv venv
  venv\Scripts\python -m pip install -q -r requirements.txt
)
venv\Scripts\python bot.py
