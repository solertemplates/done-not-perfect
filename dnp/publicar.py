"""Publica episodios: valida, renderiza, verifica y deja el MP4 y la miniatura en una carpeta.

Uso (lo lanza el workflow cuando cambia un archivo de episodios/):
    python -m dnp.publicar episodios/04_roca.json [más archivos...] --destino salida/videos
    python -m dnp.publicar --todos --destino salida/videos
    python -m dnp.publicar --todos --solo-comprobar

Si algún JSON tiene errores, escribe ERRORES.txt en la carpeta de destino, en
español sencillo. Si todo va bien, deja un aviso para borrar el ERRORES.txt viejo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import sys
from pathlib import Path

from .config import ErrorConfig, cargar

RAIZ = Path(__file__).resolve().parent.parent
SIN_ERRORES = ".sin_errores"  # aviso para que el workflow borre videos/ERRORES.txt


def _render_y_verificar(ruta: Path, salida: Path):
    from .render import renderizar
    from .verificar import verificar

    ep, mp4, mini = renderizar(str(ruta), salida, capturas=[0, 8, 16])
    ancho, alto = ep.tamano
    return ep, mp4, mini, verificar(mp4, mini, ancho, alto, ep.fps, ep.duracion)


def texto_errores(problemas: list[tuple[str, list[str]]]) -> str:
    fecha = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lineas = ["Hay que corregir algo antes de poder hacer el vídeo.", ""]
    for archivo, errores in problemas:
        lineas.append(f"Archivo: {archivo}")
        for i, e in enumerate(errores, 1):
            lineas.append(f"  {i}. {e}")
        lineas.append("")
    lineas += [
        "Cómo arreglarlo:",
        "  1. En github.com abre el archivo de arriba y pulsa el lápiz (Editar).",
        "  2. Corrige lo que dice cada punto. Los nombres entre comillas son los campos del JSON.",
        "  3. Guarda (Commit changes). El vídeo se volverá a hacer solo en unos minutos.",
        "  Truco: si escribes desde el iPhone, desactiva 'Puntuación inteligente' para que las comillas sean rectas.",
        "",
        f"(Comprobado el {fecha}. Este archivo se borra solo cuando todo está bien.)",
    ]
    return "\n".join(lineas) + "\n"


def procesar(archivos: list[Path], destino: Path | None, salida: Path, render=_render_y_verificar) -> int:
    """Devuelve el número de archivos con problemas."""
    problemas: list[tuple[str, list[str]]] = []
    publicados = []
    for ruta in archivos:
        nombre = os.path.relpath(ruta, RAIZ) if ruta.is_absolute() else str(ruta)
        try:
            cargar(ruta)
        except ErrorConfig as e:
            problemas.append((nombre, e.errores))
            print(f"❌ {nombre}: {len(e.errores)} error(es) en el JSON")
            continue
        ep, mp4, mini, resultados = render(ruta, salida / ruta.stem)
        fallos = [f"El vídeo no pasó la comprobación '{r.nombre}': {r.detalle}" for r in resultados if not r.ok]
        if fallos:
            problemas.append((nombre, fallos))
            print(f"❌ {nombre}: el vídeo no pasó {len(fallos)} comprobación(es)")
            continue
        print(f"✅ {nombre}: {len(resultados)}/{len(resultados)} comprobaciones")
        if destino is not None:
            destino.mkdir(parents=True, exist_ok=True)
            shutil.copy(mp4, destino / f"{ep['id']}.mp4")
            shutil.copy(mini, destino / f"{ep['id']}_miniatura.png")
            publicados.append(ep["id"])
    if destino is not None:
        destino.mkdir(parents=True, exist_ok=True)
        if problemas:
            (destino / "ERRORES.txt").write_text(texto_errores(problemas), encoding="utf-8")
        else:
            (destino / SIN_ERRORES).write_text("", encoding="utf-8")
    resumen = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumen:
        with open(resumen, "a", encoding="utf-8") as f:
            for i in publicados:
                f.write(f"- ✅ **{i}**: https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/raw/main/videos/{i}.mp4\n")
            if problemas:
                f.write("\n### ❌ Hay errores (también en videos/ERRORES.txt)\n\n```\n" + texto_errores(problemas) + "```\n")
    return len(problemas)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Valida, renderiza y publica episodios.")
    ap.add_argument("archivos", nargs="*")
    ap.add_argument("--todos", action="store_true", help="todos los JSON de episodios/")
    ap.add_argument("--destino", default=None, help="carpeta donde dejar MP4, miniaturas y ERRORES.txt")
    ap.add_argument("--solo-comprobar", action="store_true", help="no deja nada en el destino")
    ap.add_argument("--salida", default="salida")
    args = ap.parse_args(argv)
    archivos = [Path(a) for a in args.archivos if a.strip()]
    if args.todos or not archivos:
        archivos = sorted((RAIZ / "episodios").glob("*.json"))
    archivos = [a for a in archivos if a.suffix == ".json" and a.exists()]
    if not archivos:
        print("No hay episodios que procesar.")
        return 0
    destino = None if args.solo_comprobar or not args.destino else Path(args.destino)
    return 1 if procesar(archivos, destino, Path(args.salida)) else 0


if __name__ == "__main__":
    sys.exit(main())
