@echo off
setlocal
title Windows Live ID - Reparacion segura
echo Reparacion conservadora de Windows Live ID.
echo No borra contrasenas, tokens, registros de eventos ni juegos.
echo Solo vuelve a registrar CloudExperienceHost para el usuario actual.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Repair-WindowsLiveID.ps1" -Mode Repair
set "EXITCODE=%ERRORLEVEL%"
echo.
echo Resultado tecnico: %EXITCODE%
echo Informe en Escritorio\Windows-LiveID-Repair-Reports
pause
exit /b %EXITCODE%