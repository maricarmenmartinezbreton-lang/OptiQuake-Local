---
title: OptiQuake Local — Español
description: Plataforma experimental de código abierto para observación óptica local de vibraciones usando cámaras web.
lang: es
---

# OptiQuake Local — Resumen en español

**Creador:** Lic. Juan Esteban Ramírez — República Dominicana.

OptiQuake Local es una plataforma experimental de código abierto que utiliza cámaras web compatibles como sensores ópticos auxiliares de vibración.

## Instalación
`python -m pip install optiquake-local`

## Alertas de sismo (experimental)
Con `--alerts`, OptiQuake combina la cámara con los reportes oficiales de USGS, EMSC y GFZ:

```powershell
# una vez: tu ubicación (se guarda y sirve también sin internet)
python src\optiquake.py --alerts --lat 18.4861 --lon -69.9312 --place "Santo Domingo" --drill
# uso normal: cámara + fuentes oficiales + teléfonos en el Wi-Fi de la casa
python src\optiquake.py --alerts --lan-port
```

- Solo avisa de un sismo oficial si, por su magnitud y distancia, puede sentirse **donde estás**. Un sismo en RD no alerta a alguien en Estados Unidos.
- **Sin internet** sigue funcionando con la cámara y lo indica en pantalla.
- El aviso dice **ALERTA DE SISMO**, *Agáchate, cúbrete, sujétate* mientras tiembla, y *cuando pare, sal despacio y busca un lugar seguro y abierto*. Si hay riesgo, añade el aviso de tsunami.
- Canales: ventana roja a pantalla completa, sirena por las bocinas, bocina Bluetooth o auriculares (sube el volumen al máximo en Windows), voz, página para teléfonos en el Wi-Fi de casa (`--lan-port`, no necesita internet) y notificación al celular con ntfy (`--ntfy-topic`, necesita internet).
- `--drill` hace un **simulacro** por todos los canales.
- **Red de sensores** (`--mesh-key CLAVE`): varios equipos con OptiQuake en la misma red se avisan entre sí. Si otro sensor ve la misma vibración, la alerta pasa a *confirmada por N sensores*; sin detección propia, solo alerta si al menos dos sensores coinciden, para que un camión junto a una casa no alarme a todos. Un simulacro iniciado en un equipo suena en todos. Usa la misma clave en todos los equipos.
- **Siempre activo:** mientras vigila, Windows no se suspende. Con `--install-autostart` las alertas arrancan solas al entrar a Windows y se reinician si se detienen. Con el PC bloqueado siguen funcionando la sirena, la voz y los teléfonos.

**Instalación fácil en Windows:** doble clic en `INSTALAR-WINDOWS.cmd`. Instala Python y FFmpeg si faltan y te guía paso a paso: ubicación (lista de ciudades de RD), cámara, teléfonos, red de sensores, simulacro e inicio automático. `DESINSTALAR-ARRANQUE.cmd` quita el inicio automático. La primera vez, permite el acceso en el Firewall de Windows para *redes privadas*.

Es un aviso experimental: mantén activadas las alertas oficiales y sigue las indicaciones de Defensa Civil, el COE y el 911.

## Integraciones
- Skill para sistemas de IA.
- Plugin API v1 para extensiones comunitarias.
- Flujo JSONL para automatización.
- Arquitectura preparada para correlación multisensor.

## Límites científicos
La versión actual demuestra observabilidad local de vibraciones. No es un sismómetro certificado, no predice terremotos, no estima magnitud y no constituye por sí sola un sistema garantizado de alerta temprana.

## Referencias públicas
- Código: https://github.com/maricarmenmartinezbreton-lang/OptiQuake-Local
- PyPI: https://pypi.org/project/optiquake-local/
- DOI del proyecto: https://doi.org/10.5281/zenodo.23004638