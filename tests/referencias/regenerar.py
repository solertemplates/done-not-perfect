"""Regenera las huellas de referencia de los episodios (solo si un cambio visual es intencionado).

    python tests/referencias/regenerar.py
"""
import hashlib
import json
import sys
from multiprocessing import Pool
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from dnp.config import cargar  # noqa: E402
from dnp.render import crear_escena  # noqa: E402

EPISODIOS = ["ep01_la_silla", "ep02_la_escalera", "ep03_los_dos_martillos", "04_roca", "09_paneles"]
_e = None


def _ini(ruta):
    global _e
    _e = crear_escena(cargar(ruta))


def huella(i):
    return hashlib.sha1(_e.fotograma(i / _e.ep.fps).tobytes()).hexdigest()


def huellas(nombre):
    ruta = RAIZ / "tests" / "datos" / "episodios" / f"{nombre}.json"
    n = cargar(ruta).num_fotogramas
    with Pool(initializer=_ini, initargs=(ruta,)) as p:
        return p.map(huella, range(n), chunksize=8)


if __name__ == "__main__":
    for nombre in EPISODIOS:
        destino = Path(__file__).parent / f"{nombre}.json"
        destino.write_text(json.dumps({"fotogramas": huellas(nombre)}, indent=0) + "\n", encoding="utf-8")
        print("referencia guardada:", destino.name)
