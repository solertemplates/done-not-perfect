"""Música real con licencia libre para YouTube: Kevin MacLeod (incompetech.com), CC BY 4.0.

Cada sección del vídeo pide un ambiente (suspense, emotivo, épico...). Para cada uno hay
varias canciones candidatas: se usa la primera que se pueda descargar y no se repite
ninguna en el mismo vídeo. Se guardan en caché. El crédito obligatorio va al final de
la descripción (_textos.txt).
"""
from __future__ import annotations

import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

SR = 48000
URL = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/{}.mp3"
CANCIONES = {
    "suspense": ["Hitman", "Volatile Reaction", "Long Note Three", "Dark Times", "Ossuary 6 - Air"],
    "intriga": ["Cipher", "Sneaky Snitch", "Investigations", "Hitman"],
    "emotivo": ["Heartwarming", "Dreams Become Real", "Inspired", "Touching Moments Two - Higher"],
    "epico": ["Crossing the Chasm", "Ascending the Vale", "Impact Prelude", "Rising Tide", "Heroic Age"],
    "tension": ["Volatile Reaction", "Long Note Four", "Darkest Child", "Hitman"],
    "esperanza": ["Inspired", "Heartwarming", "Dreams Become Real", "Ascending the Vale"],
}


def credito(titulo: str) -> str:
    return (f"\"{titulo}\" Kevin MacLeod (incompetech.com)\n"
            "Licensed under Creative Commons: By Attribution 4.0 License\nhttp://creativecommons.org/licenses/by/4.0/")


class Discoteca:
    def __init__(self, cache: Path):
        self.cache = cache / "musica"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.usadas: list[str] = []
        self.fallos: list[str] = []
        self._cache: dict = {}

    def _descargar(self, titulo: str) -> Path | None:
        destino = self.cache / f"{titulo}.mp3"
        if destino.exists() and destino.stat().st_size > 100_000:
            return destino
        url = URL.format(urllib.parse.quote(titulo))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "done-not-perfect/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                datos = r.read()
            if len(datos) < 100_000 or not (datos[:3] == b"ID3" or datos[:2] == b"\xff\xfb"):
                raise ValueError("no es un MP3")
            destino.write_bytes(datos)
            return destino
        except Exception as e:  # noqa: BLE001
            self.fallos.append(f"{titulo}: {e}")
            return None

    def cancion(self, ambiente: str, evitar: str | None = None) -> tuple[np.ndarray, str]:
        """(audio, título) de una canción del ambiente: primero las que aún no han sonado, nunca la misma
        que la anterior. Con muchas escenas, una canción puede volver más tarde (desde otra parte)."""
        lista = CANCIONES[ambiente] + [t for v in CANCIONES.values() for t in v if t not in CANCIONES[ambiente]]
        orden = [t for t in lista if t not in self.usadas] + [t for t in lista if t in self.usadas]
        for titulo in orden:
            if titulo == evitar:
                continue
            ruta = self._descargar(titulo)
            if ruta is None:
                continue
            if titulo not in self.usadas:
                self.usadas.append(titulo)
            if titulo not in self._cache:
                self._cache[titulo] = leer(ruta)
            return self._cache[titulo], titulo
        raise RuntimeError("No se pudo descargar música de incompetech.com: " + "; ".join(self.fallos[-4:]))


def leer(ruta: Path) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(ruta), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()


def ajustar(x: np.ndarray, duracion: float, fundido: float = 3.0) -> np.ndarray:
    n = int(round(duracion * SR))
    f = int(fundido * SR)
    out = x.copy()
    while len(out) < n:  # repetir con un fundido cruzado
        cola = out[-f:] * np.linspace(1, 0, f)[:, None]
        cabeza = x[:f] * np.linspace(0, 1, f)[:, None]
        out = np.concatenate([out[:-f], cola + cabeza, x[f:]])
    out = out[:n]
    rms = np.sqrt(np.mean(out ** 2)) + 1e-9
    return out * (0.2 / rms)
