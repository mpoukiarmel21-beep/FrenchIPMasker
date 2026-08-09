@echo off
cd /d "%~dp0"
echo ============================================
echo   French Proxy Tool - Serveur proxy local
echo   Rotation automatique d'IP FR
echo ============================================
echo   Dans IXBrowser : profil -> proxy -> type HTTP
echo   -> 127.0.0.1 port 8080
echo.
python french_proxy_tool.py serve --port 8080 --count 15
pause
