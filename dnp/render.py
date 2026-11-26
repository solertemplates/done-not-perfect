"""Render de un episodio: fotogramas -> ffmpeg (H.264) + audio (AAC) -> MP4 y verificación.

Uso:
    python -m dnp.render episodios/ep01_la_silla.json
    python -m dnp.render episodios/ep01_la_silla.json --capturas 0,8,16
"""
from __future__ import annotations

import argparse
import multiprocessing as mp
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import audio
from .config import ErrorConfig, cargar
from .guion import EpisodioGuion
from .verificar import informe, verificar

RAIZ = Path(__file__).resolve().parent.parent

_escena = None


def crear_escena(ep):
    return EpisodioGuion(ep)


def _iniciar(ruta_json: str):
    global _escena
    _escena = crear_escena(cargar(ruta_json))


def _render(i: int) -> bytes:
    return _escena.fotograma(i / _escena.ep.fps).tobytes()


def comando_ffmpeg(salida: Path, wav: Path, ancho: int, alto: int, fps: int) -> list[str]:
    return [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ancho}x{alto}", "-framerate", str(fps), "-i", "-",
        "-i", str(wav),
        "-map", "0:v:0", "-map", "1:a:0",
        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
        "-g", str(fps * 2), "-r", str(fps), "-fps_mode", "cfr",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        str(salida),
    ]


def renderizar(ruta_json: str, carpeta: Path, capturas: list[float] | None = None, procesos: int | None = None):
    ep = cargar(ruta_json)
    escena = crear_escena(ep)
    carpeta.mkdir(parents=True, exist_ok=True)
    ancho, alto = ep.tamano
    fps, n = ep.fps, ep.num_fotogramas
    mp4 = carpeta / f"{ep['id']}.mp4"
    miniatura = carpeta / "miniatura.png"

    print(f"▶ Episodio {ep['episodio']}: {ep['titulo']} — {n} fotogramas a {fps} fps ({ep.duracion:g} s)")
    escena.fotograma(0).save(miniatura)
    for seg in capturas or []:
        i = min(n - 1, int(round(seg * fps)))
        escena.fotograma(i / fps).save(carpeta / f"captura_{seg:g}s.png")

    pista, origen = audio.mezclar(ep.duracion, escena.eventos_audio(), ep["audio"], RAIZ)
    print(f"♪ Música: {origen}")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "audio.wav"
        audio.guardar_wav(wav, pista)
        proc = subprocess.Popen(comando_ffmpeg(mp4, wav, ancho, alto, fps), stdin=subprocess.PIPE)
        t0 = time.time()
        procesos = procesos or max(1, (os.cpu_count() or 2))
        with mp.get_context("fork" if sys.platform != "win32" else "spawn").Pool(
                procesos, initializer=_iniciar, initargs=(ruta_json,)) as pool:
            for k, datos in enumerate(pool.imap(_render, range(n), chunksize=4)):
                proc.stdin.write(datos)
                if (k + 1) % (fps * 3) == 0:
                    print(f"  {k + 1}/{n} fotogramas ({time.time() - t0:.0f} s)")
        proc.stdin.close()
        if proc.wait() != 0:
            raise SystemExit("ffmpeg falló al codificar el vídeo.")
    print(f"✔ Vídeo: {mp4} ({mp4.stat().st_size / 1e6:.1f} MB) en {time.time() - t0:.0f} s")
    return ep, mp4, miniatura


def main(argv=None):
    ap = argparse.ArgumentParser(description="Renderiza un episodio de 'Done, not perfect'.")
    ap.add_argument("episodio", nargs="?", default="episodios/ep01_la_silla.json")
    ap.add_argument("--salida", default="salida")
    ap.add_argument("--capturas", default="", help="Segundos separados por comas, p. ej. 0,8,16")
    ap.add_argument("--sin-verificar", action="store_true")
    args = ap.parse_args(argv)
    capturas = [float(x) for x in args.capturas.split(",") if x.strip()]
    try:
        ep, mp4, mini = renderizar(args.episodio, Path(args.salida), capturas)
    except ErrorConfig as e:
        print(f"❌ {e}", file=sys.stderr)
        return 2
    if args.sin_verificar:
        return 0
    ancho, alto = ep.tamano
    res = verificar(mp4, mini, ancho, alto, ep.fps, ep.duracion)
    texto = informe(res)
    print("\nComprobaciones:\n" + texto)
    (Path(args.salida) / "informe.txt").write_text(texto + "\n", encoding="utf-8")
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a", encoding="utf-8") as f:
            f.write(f"## {ep['serie']} — Ep. {ep['episodio']}: {ep['titulo']}\n\n")
            f.write("\n".join(f"- {line}" for line in texto.splitlines() if line.strip()) + "\n")
            f.write("\nDescarga el MP4 y la miniatura en **Artifacts**, al final de esta página.\n")
    return 0 if all(r.ok for r in res) else 1


if __name__ == "__main__":
    sys.exit(main())
