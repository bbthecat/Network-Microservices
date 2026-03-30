@echo off
:: ============================================================
:: Lab 7 — Push to GitHub
:: รันไฟล์นี้ใน VSCode Terminal หรือ Command Prompt
:: ============================================================

echo.
echo  Pushing Lab 7 to GitHub...
echo  Repo: https://github.com/bbthecat/Network-Microservices.git
echo.

cd /d "d:\ปั2\network"

git init
git add .
git commit -m "feat: Lab 7 - Docker-based Network & Microservices Lab"
git branch -M main
git remote add origin https://github.com/bbthecat/Network-Microservices.git
git push -u origin main

echo.
echo  Done! Check: https://github.com/bbthecat/Network-Microservices
pause
