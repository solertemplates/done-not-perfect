"""Vídeos largos estilo documental.

    python -m dnp.doc episodios_largos/01_mismo_sueldo.txt --destino salida/largos_videos
    python -m dnp.doc --todos --solo-validar

Los errores (y los avisos, por ejemplo si Edge TTS falló y se usó Piper) van a
ERRORES_LARGOS.txt, que el workflow junta en el apartado LARGOS de videos/ERRORES.txt.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import traceback
from pathlib import Path

from ..config import ErrorConfig
from .guion import cargar

RAIZ = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get("DNP_CACHE", Path.home() / ".cache" / "dnp"))


def comprobar(mp4: Path, mini: Path, duracion: float, prueba: bool):
    from ..verificar import Resultado, verificar

    rango = (duracion, duracion) if prueba else (510, 570)
    res = verificar(mp4, mini, 1920, 1080, 30, duracion, rango=rango, tam_miniatura=(1280, 720), silencio=True,
                    bucle=False)
    mb = mp4.stat().st_size / 1e6
    res.append(Resultado("Tamaño menor de 95 MB", 0 < mb < 95, f"{mb:.1f} MB"))
    return res


def procesar(archivos: list[Path], destino: Path | None, salida: Path, solo_prueba: bool = False) -> int:
    from ..publicar import texto_errores
    from .montaje import renderizar
    from .textos import generar

    problemas, avisos_todos = [], []
    for ruta in archivos:
        nombre = os.path.relpath(ruta, RAIZ) if ruta.is_absolute() else str(ruta)
        try:
            g = cargar(ruta)
            if solo_prueba:
                g.modo = "prueba"
            resultado = renderizar(g, salida / g.id, CACHE)
        except ErrorConfig as e:
            problemas.append((nombre, e.errores))
            continue
        except Exception as e:  # noqa: BLE001 — un largo que falla no bloquea los Shorts
            traceback.print_exc()
            problemas.append((nombre, [f"No se pudo hacer el vídeo largo ({type(e).__name__}: {e})."]))
            continue
        fallos = []
        for idioma, r in resultado.items():
            for c in comprobar(r["mp4"], r["miniatura"], r["linea"].duracion, g.modo == "prueba"):
                print(f"  [{idioma}] {'✅' if c.ok else '❌'} {c.nombre}: {c.detalle}")
                if not c.ok:
                    fallos.append(f"[{idioma}] El vídeo no pasó '{c.nombre}': {c.detalle}")
        avisos = sorted(set(next(iter(resultado.values()))["avisos"]))
        avisos_todos += [(nombre, avisos)] if avisos else []
        if fallos:
            problemas.append((nombre, fallos))
            continue
        if destino is not None:
            destino.mkdir(parents=True, exist_ok=True)
            for idioma, r in resultado.items():
                n = g.nombre(idioma)
                shutil.copy(r["mp4"], destino / f"{n}.mp4")
                shutil.copy(r["miniatura"], destino / f"{n}_miniatura.png")
                (destino / f"{n}_textos.txt").write_text(generar(g, idioma, r["linea"], r["musica"]), encoding="utf-8")
        print(f"✅ {nombre}: publicado en {', '.join(g.nombre(i) for i in resultado)}")
    if destino is not None:
        destino.mkdir(parents=True, exist_ok=True)
        todo = problemas + [(n, [f"Aviso: {a}" for a in av]) for n, av in avisos_todos]
        if todo:
            (destino / "ERRORES_LARGOS.txt").write_text(texto_errores(todo), encoding="utf-8")
        else:
            (destino / ".sin_errores_largos").write_text("", encoding="utf-8")
    return len(problemas)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Vídeos largos estilo documental (Mark y Sarah).")
    ap.add_argument("archivos", nargs="*")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--destino", default=None)
    ap.add_argument("--salida", default="salida/largos")
    ap.add_argument("--solo-validar", action="store_true", help="solo comprueba que los guiones estén bien")
    ap.add_argument("--prueba", action="store_true", help="solo los primeros 60 s (para los pull requests)")
    args = ap.parse_args(argv)
    archivos = [Path(a) for a in args.archivos if a.strip().endswith(".txt")]
    if args.todos or not archivos:
        archivos = sorted((RAIZ / "episodios_largos").glob("*.txt"))
    archivos = [a for a in archivos if a.exists()]
    if not archivos:
        print("No hay vídeos largos que procesar.")
        return 0
    if args.solo_validar:
        malos = 0
        for a in archivos:
            try:
                g = cargar(a)
                print(f"✅ {a.name}: {len(g.frases())} frases, modo {g.modo}")
            except ErrorConfig as e:
                malos += 1
                print(f"❌ {e}")
        return 1 if malos else 0
    return 1 if procesar(archivos, Path(args.destino) if args.destino else None, Path(args.salida), args.prueba) else 0


if __name__ == "__main__":
    sys.exit(main())
