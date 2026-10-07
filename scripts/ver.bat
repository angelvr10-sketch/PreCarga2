@echo off
REM ============================================================================
REM  Levantar precarga2 en modo PRODUCCION local.
REM
REM  Uso:  scripts\ver.bat
REM
REM  Compila el frontend y lo sirve desde FastAPI, igual que en Fly.
REM  A diferencia de dev.bat, AQUI si se registra el service worker, asi que la
REM  PWA se puede instalar y probar de verdad.
REM
REM  Entra a http://localhost:8000  ^(no 5173^)
REM
REM  Recompila antes de cada arranque, para no probar un bundle viejo.
REM ============================================================================

setlocal
cd /d "%~dp0.."

set VENV_PYTHON=%CD%\.venv\Scripts\python.exe
set NODE=%ProgramFiles%\nodejs\node.exe

echo.
echo 1/2  Compilando el frontend...
cd frontend
call "%NODE%" "%CD%\node_modules\typescript\bin\tsc" -b
if errorlevel 1 (
  echo [ERROR] TypeScript fallo. No se arranca.
  cd /d "%~dp0.."
  exit /b 1
)
call "%NODE%" "%CD%\node_modules\vite\bin\vite.js" build
if errorlevel 1 (
  echo [ERROR] El build fallo. No se arranca.
  cd /d "%~dp0.."
  exit /b 1
)
cd /d "%~dp0.."

echo.
echo 2/2  Arrancando el servidor ^(con el service worker activo^)...
echo.
echo   http://localhost:8000
echo   Usuario: admin / admin123
echo.
echo   Para la PWA: Chrome/Edge en el menu del navegador ^> "Instalar app".
echo.
echo   Ctrl+C para detener.
echo.

"%VENV_PYTHON%" -m uvicorn main:app --host 127.0.0.1 --port 8000

endlocal
