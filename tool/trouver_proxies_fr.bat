@echo off
cd /d "%~dp0"
echo ============================================
echo   French Proxy Tool - Trouver proxies FR
echo   Scraping live + test en VRAI (IP de sortie)
echo ============================================
python french_proxy_tool.py list --count 8
echo.
echo Resultat dans : proxies_fr.txt
pause
