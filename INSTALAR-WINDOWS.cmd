@echo off
chcp 65001 >nul
title OptiQuake Local - Instalacion de alertas de sismo
cd /d "%~dp0"
echo.
echo  ===  OptiQuake Local: instalacion de alertas de sismo  ===
echo.

rem --- Python 3.10 or newer. "python" may be the Microsoft Store shortcut, so test it.
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 goto have_python
echo  Python no esta instalado. Instalandolo con winget...
winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto python_failed
echo.
echo  Python quedo instalado. CIERRA esta ventana y vuelve a abrir INSTALAR-WINDOWS.cmd
pause
exit /b 0
:python_failed
echo  No se pudo instalar Python automaticamente.
echo  Descargalo de https://www.python.org/downloads/ y marca "Add python.exe to PATH".
pause
exit /b 1

:have_python
rem --- FFmpeg is needed only for the camera sensor.
where ffmpeg >nul 2>nul
if not errorlevel 1 goto have_ffmpeg
echo  FFmpeg no esta instalado; hace falta para usar la camara. Instalandolo con winget...
winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
if errorlevel 1 echo  No se pudo instalar FFmpeg: las alertas funcionaran solo con reportes oficiales.
if not errorlevel 1 echo  FFmpeg instalado. Si la camara no aparece, cierra y vuelve a abrir este instalador.

:have_ffmpeg
python src\optiquake.py --self-test
if errorlevel 1 goto selftest_failed
python src\optiquake.py --setup
echo.
echo  Para desactivar el inicio automatico: DESINSTALAR-ARRANQUE.cmd
pause
exit /b 0

:selftest_failed
echo  La prueba interna fallo. Revisa que la carpeta del programa este completa.
pause
exit /b 1
