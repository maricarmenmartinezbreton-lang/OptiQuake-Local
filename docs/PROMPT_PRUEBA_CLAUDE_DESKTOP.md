# Prompt para ejecutar la prueba real con Claude Desktop (Windows)

Copia todo el bloque de abajo y pégalo en un chat nuevo de **Claude Desktop** en el PC
donde está conectada la Insta360 Link (con Desktop Commander o Windows MCP activo).

---

```text
Usa Desktop Commander (o Windows MCP) para ejecutar en este PC la prueba de campo de
mi proyecto OptiQuake Local con la cámara Insta360 Link. Pasos:

1. Comprueba que existen Python 3.10+, Git y FFmpeg (`python --version`, `git --version`,
   `ffmpeg -version`). Si falta FFmpeg, instálalo con `winget install Gyan.FFmpeg`
   y abre una terminal nueva para que quede en el PATH. Si falta Git: `winget install Git.Git`.

2. Prepara el repositorio en %USERPROFILE%\OptiQuake-Local:
   - Si no existe: git clone https://github.com/maricarmenmartinezbreton-lang/OptiQuake-Local.git
   - Luego: git fetch origin && git checkout claude/lucid-hopper-m8lqqm && git pull

3. Ejecuta y muéstrame la salida de:
   python src\optiquake.py --self-test
   python tests\test_detector.py
   python src\optiquake.py --health
   python src\optiquake.py --list-devices

4. Recuérdame que en Insta360 Link Controller desactive el seguimiento con IA y la
   reducción de ruido del micrófono. Espera a que te confirme.

5. Abre la prueba guiada en una ventana VISIBLE, porque tengo que seguir las
   instrucciones en pantalla y hacer golpes y movimientos:
   Start-Process powershell -ArgumentList '-NoExit','-Command','cd $env:USERPROFILE\OptiQuake-Local; python scripts\prueba_campo.py'
   Si falla porque no encuentra el micrófono, usa el nombre exacto que salió en
   --list-devices con: python scripts\prueba_campo.py --microfono "NOMBRE"

6. Cuando yo te diga que terminó, lee el archivo *_informe.json más reciente en
   %USERPROFILE%\OptiQuake-Local\prueba_campo\ y muéstrame la tabla de resultados.

7. Sube SOLO ese archivo *_informe.json a mi Google Drive, en una carpeta llamada
   "OptiQuake pruebas". No subas el vídeo .mp4 salvo que yo lo pida.

Si algún paso falla, muéstrame el error completo y no sigas hasta resolverlo.
```

---

Después, en la sesión de Claude Code donde se desarrolla el proyecto, escribe:
"ya está el informe en Drive". Claude lo leerá con el conector de Google Drive y
ajustará los umbrales con los datos reales.
