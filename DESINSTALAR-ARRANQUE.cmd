@echo off
chcp 65001 >nul
cd /d "%~dp0"
python src\optiquake.py --uninstall-autostart
echo  Las alertas ya no se iniciaran con Windows. Cierra la ventana minimizada
echo  "OptiQuake Local - alertas de sismo" o reinicia para detenerlas ahora.
pause
