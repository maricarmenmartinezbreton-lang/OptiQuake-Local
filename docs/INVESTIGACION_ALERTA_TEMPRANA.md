# Investigación: cómo acercar OptiQuake Local a una alerta temprana útil

Fecha: 2026-10-05 · Estado: propuesta de investigación, sin validar

> OptiQuake Local sigue siendo un prototipo experimental. Este documento describe
> qué haría falta para que contribuya a una alerta temprana real. No sustituye
> las alertas oficiales ni los sistemas sísmicos certificados.

## 1. La física que manda

Un terremoto emite dos tipos principales de ondas:

| Onda | Velocidad aproximada | Daño |
|---|---|---|
| P (primaria) | ~6 km/s | Débil, llega primero |
| S y superficiales | ~3,5 km/s | Fuerte, causa la mayor parte del daño |

La diferencia de llegada entre P y S es de **aproximadamente 1 segundo por cada 8 km**
de distancia al epicentro. De ahí salen las dos únicas formas de obtener aviso:

1. **Alerta en el sitio (un solo sensor):** detectar la onda P y avisar antes de que
   llegue la S. A 40 km hay ~5 s de diferencia; restando 1–3 s de detección quedan
   **2–4 segundos**. Cerca del epicentro (zona ciega) no hay tiempo útil.
   La literatura (métodos τc y Pd sobre los primeros 3 s de onda P) reporta 1–2 s de
   tiempo de alerta y 3–8 s de margen antes del movimiento fuerte.
2. **Alerta en red (muchos sensores separados):** los sensores cercanos al epicentro
   detectan primero y avisan por internet (casi instantáneo) a los lejanos, que aún
   no han recibido las ondas. **Aquí está la mayor parte del tiempo útil**: en el
   sismo M7.8 de Turquía (2023) los teléfonos de Earthquake Network dieron hasta
   58 s de aviso.

**Conclusión:** un único nodo OptiQuake nunca dará decenas de segundos de aviso.
El valor real está en (a) detectar bien la onda P en el sitio y (b) formar una red.

## 2. Límites honestos de la webcam

- 60 fps es suficiente en frecuencia (la energía útil de la onda P está en ~1–10 Hz).
- Pero la cámara mide **movimiento de píxeles**, no aceleración: si la cámara y la
  escena se mueven juntas, la señal se cancela; si solo tiembla el soporte, se amplifica.
- La onda P suele ser **pequeña**; es probable que una webcam no la distinga del ruido.
- Personas, mascotas, luces y ventiladores generan falsos positivos.

Por eso la webcam debería ser **un sensor más**, no el único. Un acelerómetro MEMS
(el del teléfono, o un ADXL355/MPU6050 con ESP32) mide aceleración real, cuesta
poco y es lo que usan MyShake, Earthquake Network, GeoShake y la red de Bangladesh.

## 3. Mejoras propuestas, por prioridad

### Prioridad 1 — Detector sísmico estándar (en el propio programa)
- **STA/LTA** (promedio corto / promedio largo), el disparador clásico de sismología,
  junto al z‑robusto actual.
- **Filtro de banda 1–10 Hz** para descartar derivas lentas y golpes muy agudos.
- **Rechazo de impulsos**: un paso o un portazo dura décimas de segundo; un sismo
  mantiene energía durante segundos. Usar duración y forma del evento (ya registradas
  en `vibration_end`).

### Prioridad 2 — Nuevos sensores (Plugin API v2, ya en el ROADMAP)
- **Acelerómetro del teléfono** mediante una página local que use la API
  `DeviceMotion` del navegador y envíe datos por WebSocket al programa.
- **ESP32 + ADXL355/MPU6050** por USB serie o MQTT (~10–150 USD por nodo).
- Fusión: declarar evento solo si **dos sensores independientes** coinciden en tiempo.

### Prioridad 3 — Estimación en el sitio (onda P)
- Con aceleración en unidades físicas, calcular **Pd** (desplazamiento pico) y
  **τc** (periodo característico) en los primeros 1–3 s.
- Umbral de referencia en la literatura: **Pd ≥ 0,35 cm** sugiere movimiento fuerte.
- Emitir `p_wave_candidate` con nivel de confianza, nunca "terremoto confirmado".

### Prioridad 4 — Red comunitaria
- Cada nodo publica disparadores mínimos (hora sincronizada por NTP, ubicación
  aproximada, amplitud) a un servidor de retransmisión abierto.
- El servidor agrupa disparadores en espacio y tiempo (DBSCAN espacio‑temporal,
  como MyShake) y exige **N nodos en un radio y ventana** para declarar evento.
- Envía a los nodos lejanos un aviso con **cuenta regresiva estimada** de llegada de
  la onda S (distancia ÷ 3,5 km/s).
- Privacidad: ubicación redondeada, sin vídeo, sin identificadores personales.

### Prioridad 5 — Entrega de la alerta
- Sonido/sirena local, notificación de escritorio, Home Assistant, Telegram.
- Mensaje corto y accionable: **"Agáchate, cúbrete y sujétate"**.
- Latencia medida de punta a punta (sensor → alerta) y publicada.

### Prioridad 6 — Validación (imprescindible antes de cualquier afirmación)
- Reproducir **registros reales** de sismos (FDSN/IRIS, dataset STEAD, dataset MEMS de
  Italia central) a través del pipeline y medir tiempo de alerta y aciertos.
- Mesa vibratoria casera para pruebas repetibles; comparar con un Raspberry Shake.
- Publicar **falsas alarmas por día** y detecciones perdidas por magnitud y distancia.
- Las falsas alarmas generan pánico y destruyen la confianza: el umbral debe ser
  conservador y el sistema debe decir claramente que es experimental.

## 4. Recomendación inmediata para las personas

Mientras OptiQuake madura, la protección más eficaz disponible hoy es:
- Activar **Android Earthquake Alerts** (incluido en Android, usa la red global de
  teléfonos) o instalar **Earthquake Network** / **MyShake** según el país.
- Seguir las alertas oficiales del organismo nacional de protección civil.
- Practicar "agáchate, cúbrete y sujétate"; incluso 3 segundos bastan para hacerlo.

## 5. Siguiente paso técnico sugerido

1. Implementar STA/LTA + filtro de banda + rechazo de impulsos (Prioridad 1).
2. Plugin de acelerómetro de teléfono por navegador (Prioridad 2), que no requiere
   comprar hardware.
3. Herramienta de reproducción de registros sísmicos reales para validar (Prioridad 6).

## Fuentes

- Allen et al., *Global earthquake detection and warning using Android phones*, Science (2025). https://www.science.org/doi/10.1126/science.ads4779
- Finazzi et al. (Earthquake Network), *Smartphones enabled up to 58 s strong-shaking warning in the M7.8 Türkiye earthquake*, Scientific Reports (2024). https://www.nature.com/articles/s41598-024-55279-z
- Kong et al., *MyShake: A smartphone seismic network for earthquake early warning and beyond*, Science Advances (2016). https://www.science.org/doi/10.1126/sciadv.1501055
- *Toward Global Earthquake Early Warning with the MyShake Smartphone Seismic Network, Part 1* (SRL, 2020). https://arxiv.org/abs/1909.08136
- Wu et al., *Determination of earthquake early warning parameters, τc and Pd, for southern California*, GJI. https://academic.oup.com/gji/article/170/2/711/849109
- *A Review on the Development of Earthquake Warning System Using Low-Cost Sensors in Taiwan*. https://pmc.ncbi.nlm.nih.gov/articles/PMC8622038/
- *Low-cost MEMS accelerometers for earthquake early warning systems: dataset from Central Italy*. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10875240/
- BUET Low-Cost Seismic Monitoring Device (Bangladesh). https://github.com/tasminkhan/Low-Cost-Seismic-Monitoring-Device
- GeoShake community sensor network. https://geoshake.org/
