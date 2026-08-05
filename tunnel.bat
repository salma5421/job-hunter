@echo off
echo ========================================================
echo 🌐 Creating Instant Public HTTPS URL...
echo ========================================================
ssh -o StrictHostKeyChecking=no -R 80:127.0.0.1:5000 serveo.net
pause
