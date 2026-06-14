@echo off
cls
echo.
echo  ============================================================
echo   AudioTranscriber - Instalacao (Windows)
echo  ============================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERRO] Python nao encontrado.
    echo  Instale em https://www.python.org/downloads/
    echo  Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] %PYVER% encontrado.
echo.

echo  [1/3] Criando ambiente virtual...
if exist venv (
    echo       Ja existe, pulando.
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo  [ERRO] Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
    echo  [OK] Ambiente virtual criado.
)
echo.

echo  [2/3] Ativando ambiente virtual...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo  [ERRO] Nao foi possivel ativar o ambiente virtual.
    pause
    exit /b 1
)
echo  [OK] Ambiente virtual ativado.
echo.

echo  [3/3] Instalando dependencias...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo  [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)
echo  [OK] Dependencias instaladas.
echo.

echo  ============================================================
echo   Instalacao concluida com sucesso!
echo.
echo   Para rodar: clique duas vezes em rodar.bat
echo  ============================================================
echo.
pause