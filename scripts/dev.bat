@echo off
REM ============================================================================
REM  Levantar precarga2 en local (backend + frontend) con espera activa.
REM
REM  Uso:  scripts\dev.bat
REM
REM  Entra a http://localhost:5173
REM
REM  QUE HACE DISTINTO: no abre el frontend a ciegas. Primero arranca el
REM  backend y ESPERA a que responda; solo cuando responde bien abre Vite.
REM
REM  Sin eso, si el backend se cae al arrancar (por ejemplo porque falta el
REM  .env), queda una ventana con un traceback que se desliza sin que se note,
REM  la del frontend parece estar bien, y el resultado es que la app carga
REM  pero el login dice "Failed to fetch" sin explicar por que. Es exactamente
REM  el fallo que hace que esto parezca un problema de la app y no del arranque.
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0.."

set VENV_PYTHON=%CD%\.venv\Scripts\python.exe
set NODE=%ProgramFiles%\nodejs\node.exe
set VITE=%CD%\frontend\node_modules\vite\bin\vite.js

if not exist "%VENV_PYTHON%" (
  echo [ERROR] No existe %VENV_PYTHON%
  echo Crea el entorno:  python -m venv .venv
  echo                   .venv\Scripts\pip install -r requirements.txt
  exit /b 1
)

if not exist "%VITE%" (
  echo [ERROR] Falta vite en frontend\node_modules
  echo Instala con:  cd frontend ^&^& npm install
  exit /b 1
)

echo.
echo   1/2  Arrancando el backend en :8000...
start "precarga2 backend (:8000)" cmd /k "%VENV_PYTHON%" -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

REM --- Espera activa: hasta 45 s a que el puerto 8000 acepte conexiones ---
REM
REM Se hace TODO el bucle dentro de un solo PowerShell, con TcpClient y un
REM timeout de 300 ms por intento. La primera version usaba Test-NetConnection
REM en un bucle de .bat, y eso es un desastre: Test-NetConnection tarda ~3 s
REM por llamada (hace resolucion DNS), asi que 45 intentos eran mas de dos
REM minutos y el script se comia su propio tiempo de espera antes de abrir el
REM frontend.
set LISTO=
for /f "usebackq delims=" %%r in (`powershell -NoProfile -Command ^
  "$c = New-Object System.Net.Sockets.TcpClient; ^
   $limite = (Get-Date).AddSeconds(45); ^
   while ((Get-Date) -lt $limite) { ^
     try { $t = $c.BeginConnect('127.0.0.1', 8000, $null, $null); ^
           if ($t.AsyncWaitHandle.WaitOne(300) -and $c.Connected) { 'listo'; exit 0 } } catch {}; ^
     $c.Close(); $c = New-Object System.Net.Sockets.TcpClient; ^
     Start-Sleep -Milliseconds 300 }; ^
   exit 1" 2^>nul`) do set LISTO=%%r

if "!LISTO!"=="" (
  echo.
  echo [ERROR] El backend no respondio en 45 segundos.
  echo.
  echo Mira la ventana "precarga2 backend" para ver el error de arranque.
  echo Las causas mas comunes:
  echo.
  echo   - Falta el .env. Debe existir en la raiz del proyecto:
  echo         SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY
  echo   - Dependencias faltantes:
  echo         .venv\Scripts\pip install -r requirements.txt
  echo.
  echo No se abre el frontend porque sin backend no sirve de nada.
  exit /b 1
)

echo   2/2  Backend OK. Arrancando Vite en :5173...
start "precarga2 frontend (:5173)" cmd /k "%NODE%" "%VITE%" --port 5173 --host 127.0.0.1

echo.
echo   ┌────────────────────────────────────────────────────────┐
echo   │  ENTRA A  http://localhost:5173     (no a 8000)      │
echo   │                                                        │
echo   │  usuario: admin / admin123                            │
echo   │  ^(- admin no tiene comandas todavia^)                │
echo   │                                                        │
echo   │  Para probar la PWA instalable:  scripts\ver.bat      │
echo   │  esa entra por http://localhost:8000                  │
echo   └────────────────────────────────────────────────────────┘
echo.

endlocal
