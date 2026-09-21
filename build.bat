@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo  Build: PKA_PXG_Hotkeys.exe
echo ============================================

rem Usa o ambiente virtual do projeto quando existir.
if exist ".venv\Scripts\python.exe" (
    set "PY=.venv\Scripts\python.exe"
) else (
    set "PY=python"
)

"%PY%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale o Python 3.12+ ou crie o .venv.
    exit /b 1
)

"%PY%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller ausente. Instalando dependencias...
    "%PY%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar as dependencias.
        exit /b 1
    )
)

rem assets/ so entra no pacote se tiver algum arquivo.
set "EXTRA="
dir /b /a-d "assets" >nul 2>&1 && set "EXTRA=--add-data assets;assets"

"%PY%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --noupx ^
    --windowed ^
    --name PKA_PXG_Hotkeys ^
    --collect-all customtkinter ^
    --hidden-import keyboard ^
    --hidden-import mouse ^
    --uac-admin ^
    %EXTRA% ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERRO] O build falhou. Veja as mensagens acima.
    exit /b 1
)

echo.
echo [OK] Executavel gerado em: dist\PKA_PXG_Hotkeys\PKA_PXG_Hotkeys.exe
echo      Distribua a PASTA dist\PKA_PXG_Hotkeys inteira, nao so o .exe.
echo      As pastas config\ e logs\ sao criadas ao lado do .exe na primeira execucao.
echo      O executavel pede elevacao (UAC) ao abrir: o PokeAlliance roda como
echo      administrador, e sem isso o Windows bloqueia as teclas enviadas.
exit /b 0
