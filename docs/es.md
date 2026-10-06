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