# Windows Live ID Safe Repair

Módulo autónomo de diagnóstico y reparación conservadora para errores Windows Live ID 2028/6113, 0x80048888 y autenticación de aplicaciones Microsoft.

**Alcance honesto:** proporciona una auditoría y un intento de reparación de un clic sin borrar datos. No puede garantizar resolver todas las causas ni borrar los errores históricos, que se conservan como evidencia.

## Ejecutar en Windows con un clic
1. Descarga el ZIP del repositorio y extrae la carpeta skills/windows-liveid-safe-repair.
2. Inspecciona los archivos de la carpeta.
3. Haz doble clic en Ejecutar-reparacion-segura.cmd.
4. Lee el resultado local en Escritorio/Windows-LiveID-Repair-Reports.

Este lanzador solo vuelve a registrar Microsoft.Windows.CloudExperienceHost para el usuario actual; no desinstala Gaming Services, no elimina llaves del Registro ni credenciales, no modifica contraseñas y no reinicia Windows. Si los errores continúan, lo informa claramente.

## Instalación como Agent Skill
Con Node.js y un agente compatible:

    npx skills add maricarmenmartinezbreton-lang/OptiQuake-Local --skill windows-liveid-safe-repair

Instalar una skill **no ejecuta** reparación automática. En un proyecto protegido, revisa primero el código y la configuración.

## Auditar sin cambios
En Windows PowerShell 5.1:

    powershell.exe -NoProfile -File scripts\Repair-WindowsLiveID.ps1 -Mode Audit

## Límites de seguridad
- No limpia los eventos 2028/6113 anteriores: los informes tienen una ventana temporal limitada.
- Error de origen Microsoft Live ID no significa que los juegos instalados en Steam sean prescindibles.
- No deshabilita ni re-registra la aplicación GamingServices: se observaron fallos que pueden afectar la inscripción del servicio GamingServicesNet.
- Si falta GamingServicesNet, use únicamente la herramienta oficial Microsoft Gaming Services Repair Tool y compruebe su firma digital.
- No hay exportación de cuentas, correos, tokens ni datos privados.
- El estado final solo se declara resuelto con ausencia sostenida de errores NUEVOS y autenticación real verificada.

## Fuentes
Microsoft WAM/Live ID: https://learn.microsoft.com/troubleshoot/microsoft-365/authentication/automatic-authentication-fails
Xbox Gaming Services Repair Tool: https://support.xbox.com/help/games-apps/troubleshooting/gaming-services-repair-tool
Formato de skills: https://agentskills.io/specification

Licencia: AGPL-3.0, repositorio OptiQuake Local.