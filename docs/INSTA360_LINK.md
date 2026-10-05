# Guía: OptiQuake Local con la Insta360 Link (píxeles + micrófono)

Esta guía explica cómo usar **solo la Insta360 Link** como sensor de vibración,
combinando dos canales que la cámara entrega por USB: la imagen y el micrófono.

> Prototipo experimental: los eventos son *vibraciones locales*, no terremotos
> confirmados. No sustituye las alertas oficiales.

## 1. Qué mide cada canal

| Canal | Qué mide | Para qué sirve |
|---|---|---|
| Píxeles: `score` | Cambio medio de la imagen entre fotogramas | Detectar que algo vibró |
| Píxeles: `coverage` | Fracción de la imagen (cuadrícula 4×4) que cambió | Distinguir una **sacudida de toda la cámara** (cobertura alta) de una **persona u objeto** moviéndose en una zona (cobertura baja) |
| Píxeles: `shift_px` | Desplazamiento global de la imagen, con precisión subpíxel | Medir cuánto se movió la cámara entera |
| Píxeles: `dominant_hz` | Frecuencia dominante de la oscilación | Caracterizar la vibración (los sismos suelen estar entre 1 y 10 Hz) |
| Micrófono: `audio_z` | Energía en la banda baja de 20–200 Hz frente a su línea base | Confirmar con un retumbo estructural (`corroborated: true`) |

En pruebas sintéticas reproducibles (`tests/test_detector.py`):
- La sacudida de la cámara dio una cobertura del 56–100 % y un desplazamiento de 1–2,6 px.
- El objeto local dio una cobertura del 25 % y un desplazamiento de 0,04 px.
- La frecuencia de 5 Hz se midió como 5,0 Hz.

## 2. Preparar la cámara (Insta360 Link Controller)

1. **Desactiva el seguimiento con IA y los gestos.** Si el gimbal se mueve solo,
   generará falsos eventos. Usa el modo normal, con la cámara fija.
2. **Desactiva la reducción de ruido del micrófono.** Elimina precisamente los
   sonidos graves y continuos que queremos medir. El SDK oficial la expone como
   `EnableAudioNoiseReduction`.
3. **Fija la cámara a la estructura.** Una pared o un estante atornillado es mejor
   que un escritorio que se mueve al teclear. Evita las ventosas y los trípodes blandos.
4. **Encuadra una escena con textura y quieta,** por ejemplo una estantería o un
   cuadro. Una pared blanca lisa no muestra desplazamiento.
5. **Usa iluminación estable.** Evita el parpadeo de los fluorescentes y las pantallas
   en el encuadre.

### ¿Y los sensores de estabilización (IMU del gimbal)?

El SDK oficial de la Link (`github.com/Insta360Develop/Link-SDK`) indica si la cámara
tiene IMU (`imu_exist`), pero **no ofrece ninguna función para leer el giroscopio o el
acelerómetro en tiempo real**. Solo permite consultar los ángulos pan/tilt/roll del
gimbal y controlar funciones de la cámara. Por eso OptiQuake no usa todavía la IMU.

Además, la estabilización contrarresta el movimiento de la imagen, así que con el
gimbal activo la señal óptica se reduce. Si en el futuro se demuestra que los ángulos
del gimbal reflejan la compensación real (y no solo la posición ordenada), podrían
añadirse como un tercer canal. Requiere experimentar con la cámara física.

## 3. Uso

Primero, averigua los nombres exactos de la cámara y del micrófono:

```powershell
optiquake-local --list-devices
```

Monitorizar con píxeles + micrófono (Windows):

```powershell
optiquake-local --camera "Insta360 Link" --audio "Micrófono (Insta360 Link)" --fps 60 --min-coverage 0.5
```

Escribe el nombre del micrófono exactamente como lo muestra `--list-devices`.

Validar con una grabación (vídeo + audio del mismo archivo):

```powershell
optiquake-local --input prueba.mp4 --audio --min-coverage 0.5
```

### Prueba de campo guiada (recomendado la primera vez)

Desde la carpeta del repositorio, en Windows:

```powershell
python scripts\prueba_campo.py
```

El script busca la cámara y el micrófono de la Insta360, graba 52 s y te indica
en pantalla qué hacer en cada momento:

| Tiempo | Acción | Resultado correcto |
|---|---|---|
| 0–12 s | Calma | Sin eventos |
| 12–20 s | 3 golpes firmes en el mueble | Eventos con cobertura alta |
| 26–34 s | Caminar o mover la mano delante, sin tocar el mueble | Descartado por `--min-coverage 0.5` |
| 40–48 s | Sacudir suavemente el soporte | Evento con cobertura alta y frecuencia medida |

Al terminar muestra una tabla de aciertos y guarda la grabación y un informe JSON
en `prueba_campo/`, solo en tu equipo. Para volver a analizar una grabación:
`python scripts\prueba_campo.py --analizar prueba_campo\prueba_XXXX.mp4`.

Con el protocolo sintético equivalente (vídeo y audio generados con FFmpeg),
el resultado fue de 7/7 fases correctas.

## 4. Ejemplo de salida (valores ilustrativos)

```json
{"t":4.05,"score":6.19,"baseline":1.68,"robust_z":11.85,"source":"optical","event":"vibration","coverage":0.562,"shift_px":1.025,"audio_z":41.3}
{"status":"vibration_end","t":5.0,"start":4.017,"duration":1.0,"frames":50,"peak_score":12.42,"peak_robust_z":28.27,"peak_coverage":1.0,"peak_shift_px":2.654,"dominant_hz":5.09,"audio_peak_z":44.8,"corroborated":true}
```

- `event=vibration` se emite al empezar; los plugins lo reciben como antes.
- `vibration_end` resume el evento completo. La vibración termina tras `--end-seconds`
  (0,25 s por defecto) sin movimiento, para que una oscilación no se parta en trozos.
- `corroborated: true` significa que el micrófono también registró un retumbo
  grave en la ventana del evento.

## 5. Ajustes útiles

| Opción | Por defecto | Efecto |
|---|---|---|
| `--min-coverage` | 0 | Exige que se mueva esa fracción de la imagen. Con 0,5 se descarta el movimiento local |
| `--grid` | 4 | Tamaño de la cuadrícula (1 desactiva los rasgos de píxel) |
| `--end-seconds` | 0,25 | Tiempo en calma necesario para cerrar una vibración |
| `--audio-low` / `--audio-high` | 20 / 200 Hz | Banda grave analizada |
| `--audio-z-threshold` | 4 | Nivel de audio que cuenta como corroboración |

## 6. Límites conocidos

- El micrófono de una webcam suele recortar las frecuencias por debajo de ~50–100 Hz,
  así que no capta las frecuencias sísmicas (1–10 Hz) directamente. Mide el
  *retumbo audible* que producen la estructura y los objetos al vibrar.
- En directo, el audio llega con algo de retraso. Por eso la corroboración más
  fiable es la de `vibration_end`, no la del evento inicial.
- Falta validar con sacudidas reales y con un acelerómetro de referencia.
