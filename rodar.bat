@echo off
chcp 65001 >nul
cls
echo.
echo  ============================================================
echo   AudioTranscriber — Iniciando...
echo  ============================================================
echo.

:: Verifica se o ambiente virtual existe
if not exist venv\Scripts\activate.bat (
    echo  [ERRO] Ambiente virtual nao encontrado.
    echo  Execute primeiro o arquivo "instalar.bat".
    echo.
    pause
    exit /b 1
)

:: Verifica se o .env existe
if not exist .env (
    echo  [AVISO] Arquivo .env nao encontrado.
    echo  Copie o .env.example para .env e adicione sua API Key.
    echo.
    pause
    exit /b 1
)

:: Ativa o ambiente virtual
call venv\Scripts\activate.bat

:: Inicia o Streamlit
echo  [OK] Iniciando AudioTranscriber...
echo  [OK] Acesse no navegador: http://localhost:8501
echo.
echo  Para encerrar: pressione CTRL+C nesta janela.
echo.
streamlit run app.py --server.port 8501 --server.headless false

pause
