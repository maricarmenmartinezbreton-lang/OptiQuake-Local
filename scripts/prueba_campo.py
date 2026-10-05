#!/usr/bin/env python3
"""Prueba de campo guiada para OptiQuake Local con la Insta360 Link.

Graba ~50 s de vídeo y audio siguiendo un protocolo con instrucciones en
pantalla, analiza la grabación y guarda un informe JSON.

    python scripts/prueba_campo.py                  # graba y analiza
    python scripts/prueba_campo.py --analizar f.mp4 # solo analiza

La grabación se guarda SOLO en tu equipo (carpeta prueba_campo/) para que
puedas revisarla o compartirla si quieres. Bórrala cuando ya no la necesites.

Author: Lic. Juan Esteban Ramírez | License: AGPL-3.0-only
"""
import argparse, contextlib, datetime, io, json, pathlib, re, shutil
import subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import optiquake  # noqa: E402

# (inicio_s, fin_s, fase, instrucción, ¿se espera vibración?, tipo esperado)
PROTOCOLO = [
    (0, 12, "calma", "No toques nada ni te muevas delante de la cámara.", False, None),
    (12, 20, "golpes_mesa", "Da 3 golpes FIRMES en el mueble donde está la cámara.", True, "sacudida"),
    (20, 26, "calma_2", "Quieto otra vez.", False, None),
    (26, 34, "caminar", "Camina o mueve la mano DELANTE de la cámara sin tocar el mueble.", True, "local"),
    (34, 40, "calma_3", "Quieto otra vez.", False, None),
    (40, 48, "sacudir_soporte", "Sacude SUAVEMENTE el mueble/soporte de la cámara durante 3 s.", True, "sacudida"),
    (48, 52, "fin", "Quieto. Terminando...", False, None),
]
DURACION = PROTOCOLO[-1][1]

def dispositivos_dshow():
    """Devuelve (videos, audios) que FFmpeg ve en DirectShow."""
    r = subprocess.run([optiquake.find_ffmpeg(), "-hide_banner", "-f", "dshow",
                        "-list_devices", "true", "-i", "dummy"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    videos, audios = [], []
    for line in r.stderr.splitlines():
        m = re.search(r'"([^"]+)"\s+\((video|audio)\)', line)
        if m:
            (videos if m.group(2) == "video" else audios).append(m.group(1))
    return videos, audios

def elegir(nombres, preferido, tipo):
    for n in nombres:
        if preferido.lower() in n.lower():
            return n
    raise SystemExit(f"No encontré un dispositivo de {tipo} con '{preferido}'. "
                     f"Disponibles: {nombres}. Usa --camara / --microfono.")

def grabar(salida, camara, microfono, fps):
    cmd = [optiquake.find_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
           "-f", "dshow", "-framerate", str(fps), "-audio_buffer_size", "50",
           "-i", f"video={camara}:audio={microfono}", "-t", str(DURACION),
           "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
           "-c:a", "aac", str(salida)]
    return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stderr=subprocess.PIPE)

def guiar(proc):
    t0 = time.monotonic()
    fase_actual = None
    while proc.poll() is None:
        t = time.monotonic() - t0
        for ini, fin, fase, texto, _, _ in PROTOCOLO:
            if ini <= t < fin and fase != fase_actual:
                fase_actual = fase
                print(f"\n[{ini:>2}-{fin:>2} s] {texto}", flush=True)
        print(f"\r  t = {t:5.1f} s", end="", flush=True)
        time.sleep(0.2)
    print()

def analizar(archivo, fps, extra):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        optiquake.main(["--input", str(archivo), "--fps", str(fps), "--audio", *extra])
    return [json.loads(x) for x in out.getvalue().splitlines() if x.startswith("{")]

def fase_de(t):
    for ini, fin, fase, *_ in PROTOCOLO:
        if ini <= t < fin:
            return fase
    return "fuera"

def informe(archivo, fps):
    base = analizar(archivo, fps, [])
    filtrado = analizar(archivo, fps, ["--min-coverage", "0.5"])
    fins = [x for x in base if x.get("status") == "vibration_end"]
    fins_filtrados = [x for x in filtrado if x.get("status") == "vibration_end"]
    filas = []
    for ini, fin, fase, _, esperada, tipo in PROTOCOLO:
        # Margen de 1,5 s: FFmpeg tarda en arrancar y la persona en reaccionar.
        evs = [x for x in fins if ini - 1.5 <= x["start"] < fin + 1.5]
        evf = [x for x in fins_filtrados if ini - 1.5 <= x["start"] < fin + 1.5]
        filas.append({"fase": fase, "esperada": esperada, "tipo": tipo,
                      "eventos": len(evs), "eventos_min_coverage_0_5": len(evf),
                      "detalle": evs})
    return {"archivo": str(archivo), "fecha": datetime.datetime.now().isoformat(),
            "version": optiquake.__version__, "fps": fps, "fases": filas,
            "estado": [x for x in base if "status" in x and x["status"] != "vibration_end"]}

def imprimir(rep):
    print("\n=== RESULTADO ===")
    print(f"{'Fase':<17}{'¿Esperada?':<12}{'Eventos':<9}{'Con filtro':<12}"
          f"{'Cobertura':<11}{'Hz':<7}{'Audio z':<9}")
    aciertos = 0
    for f in rep["fases"]:
        d = f["detalle"][0] if f["detalle"] else {}
        esperado = "sí" if f["esperada"] else "no"
        if f["tipo"] == "local":
            ok = f["eventos_min_coverage_0_5"] == 0
        else:
            ok = (f["eventos"] > 0) == f["esperada"]
        aciertos += ok
        print(f"{f['fase']:<17}{esperado:<12}{f['eventos']:<9}"
              f"{f['eventos_min_coverage_0_5']:<12}"
              f"{str(d.get('peak_coverage', '-')):<11}{str(d.get('dominant_hz', '-')):<7}"
              f"{str(d.get('audio_peak_z', '-')):<9}{'OK' if ok else 'REVISAR'}")
    print(f"\nFases correctas: {aciertos}/{len(rep['fases'])}")
    print("Nota: en 'caminar' lo correcto es que el filtro --min-coverage 0.5 lo descarte.")

def main():
    ap = argparse.ArgumentParser(description="Prueba de campo guiada (Insta360 Link)")
    ap.add_argument("--camara", default="Insta360 Link")
    ap.add_argument("--microfono", default="Insta360",
                    help="parte del nombre del micrófono (se busca en la lista)")
    ap.add_argument("--fps", type=int, default=60,
                    help="fps de grabación y de análisis")
    ap.add_argument("--analizar", metavar="ARCHIVO", help="analizar una grabación existente")
    args = ap.parse_args()

    carpeta = ROOT / "prueba_campo"
    carpeta.mkdir(exist_ok=True)
    if args.analizar:
        archivo = pathlib.Path(args.analizar)
    else:
        if not sys.platform.startswith("win"):
            raise SystemExit("La grabación guiada usa DirectShow (Windows). "
                             "En otros sistemas graba un vídeo y usa --analizar.")
        if not shutil.which("ffmpeg"):
            raise SystemExit("FFmpeg no está en el PATH.")
        videos, audios = dispositivos_dshow()
        camara = elegir(videos, args.camara, "vídeo")
        microfono = elegir(audios, args.microfono, "audio")
        archivo = carpeta / f"prueba_{datetime.datetime.now():%Y%m%d_%H%M%S}.mp4"
        print(f"Cámara: {camara}\nMicrófono: {microfono}\nGrabando en: {archivo}")
        print("Antes de empezar: seguimiento IA y reducción de ruido DESACTIVADOS.")
        input("Pulsa Enter para empezar la prueba de 52 segundos...")
        proc = grabar(archivo, camara, microfono, args.fps)
        time.sleep(3)
        if proc.poll() is not None and args.fps != 30:
            print(f"No se pudo grabar a {args.fps} fps; reintentando a 30 fps.")
            args.fps = 30
            proc = grabar(archivo, camara, microfono, args.fps)
        guiar(proc)
        if proc.returncode != 0:
            raise SystemExit("FFmpeg falló: " + proc.stderr.read().decode("utf-8", "replace"))

    rep = informe(archivo, args.fps)
    imprimir(rep)
    destino = carpeta / (archivo.stem + "_informe.json")
    destino.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nInforme guardado en: {destino}")

if __name__ == "__main__":
    main()
