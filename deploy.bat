@echo off
title FrenchIPMasker - Deploy Cloudflare Worker
echo ============================================
echo   FrenchIPMasker - Deploiement Worker CF
echo ============================================
echo.

:: Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Node.js n'est pas installe.
    echo Telecharge-le depuis : https://nodejs.org
    echo.
    echo Ouvre ce lien dans ton navigateur, installe Node.js, puis relance deploy.bat
    start https://nodejs.org/dist/v22.12.0/node-v22.12.0-x64.msi
    pause
    exit /b 1
)
echo [OK] Node.js detecte
echo.

:: Install wrangler
echo [1/4] Installation de Wrangler (Cloudflare CLI)...
call npm install -g wrangler 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Echec installation wrangler. Verifie ta connexion internet.
    pause
    exit /b 1
)
echo [OK] Wrangler installe
echo.

:: Login
echo [2/4] Connexion a Cloudflare...
echo.
echo Une page web va s'ouvrir. Connecte-toi avec ton compte Cloudflare.
echo (Cree un compte gratuit si tu n'en as pas : https://dash.cloudflare.com/sign-up)
echo.
wrangler login
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Echec de la connexion. Reessaie.
    pause
    exit /b 1
)
echo [OK] Connecte
echo.

:: Deploy
echo [3/4] Deploiement du Worker FrenchIPMasker...
wrangler deploy worker.js --name french-ip-masker --compatibility-date 2025-01-01
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERREUR] Echec du deploiement.
    echo Verifie que tu as bien un compte Cloudflare actif.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   DEPLOIEMENT REUSSI !
echo ============================================
echo.
echo [4/4] Recuperation de l'URL du worker...
echo.
echo Ton worker est accessible a l'adresse ci-dessous.
echo Copie cette URL et colle-la dans les parametres de l'extension :
echo.
wrangler whoami >nul 2>&1
echo   https://french-ip-masker.YOUR-SUBDOMAIN.workers.dev
echo.
echo NOTE : L'URL exacte s'affiche dans le terminal ci-dessus.
echo Cherche la ligne commencant par "https://french-ip-masker"
echo.
echo ============================================
echo   ETAPES SUIVANTES :
echo   1. Copie l'URL du worker
echo   2. Installe l'extension FrenchIPMasker dans Chrome
echo   3. Dans l'extension, colle l'URL du worker
echo   4. Active le masquage !
echo ============================================
echo.
pause
