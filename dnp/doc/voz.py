"""Voz del narrador: Edge TTS (voces neuronales de Microsoft, gratis y sin clave).

* Inglés: en-US-AndrewNeural (cercana y con energía). Español: es-MX-JorgeNeural.
* Velocidad ajustada sola a unas 165 palabras por minuto.
* Devuelve el audio de cada frase y el momento exacto de cada palabra (para los subtítulos).
* Si Edge TTS falla, usa Piper como respaldo y lo avisa (va a ERRORES.txt sin bloquear).
* Todo se guarda en caché: la misma frase no se vuelve a pedir.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SR = 48000
VOCES = {"en": "en-US-AndrewNeural", "es": "es-MX-JorgeNeural"}
VOCES_RESPALDO = {"en": ["en-US-AvaNeural"], "es": ["es-US-AlonsoNeural"]}
PIPER = {"en": "en_US-ryan-high", "es": "es_MX-claude-high"}
OBJETIVO_PPM = 165  # palabras por minuto
PAUSA = 0.32  # segundos entre frases


@dataclass
class Locucion:
    audio: np.ndarray  # mono float32 a 48 kHz
    palabras: list[tuple[str, float, float]]  # (palabra, inicio, fin) en segundos
    motor: str  # "edge:<voz>" o "piper:<voz>"

    @property
    def duracion(self) -> float:
        return len(self.audio) / SR


def _decodificar(datos: bytes) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", "-", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                       input=datos, capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


def _recortar(audio: np.ndarray, palabras, umbral=0.006):
    """Quita el silencio del principio y del final y reajusta los tiempos de las palabras."""
    fuerte = np.nonzero(np.abs(audio) > umbral)[0]
    if not len(fuerte):
        return audio, palabras
    i0 = max(0, fuerte[0] - int(0.03 * SR))
    i1 = min(len(audio), fuerte[-1] + int(0.08 * SR))
    d = i0 / SR
    return audio[i0:i1], [(w, max(0.0, a - d), max(0.0, b - d)) for w, a, b in palabras]


async def _edge(texto: str, voz: str, velocidad: str):
    import edge_tts

    com = edge_tts.Communicate(texto, voz, rate=velocidad, boundary="WordBoundary")
    audio = bytearray()
    palabras = []
    async for trozo in com.stream():
        if trozo["type"] == "audio":
            audio += trozo["data"]
        elif trozo["type"] == "WordBoundary":
            ini = trozo["offset"] / 1e7
            palabras.append((trozo["text"], ini, ini + trozo["duration"] / 1e7))
    if not audio:
        raise RuntimeError("Edge TTS no devolvió audio")
    return bytes(audio), palabras


def edge(texto: str, voz: str, velocidad: str = "+0%") -> Locucion:
    datos, palabras = asyncio.run(_edge(texto, voz, velocidad))
    audio, palabras = _recortar(_decodificar(datos), palabras)
    return Locucion(audio, palabras, f"edge:{voz}")


def piper(texto: str, idioma: str, carpeta: Path, longitud: float = 1.0) -> Locucion:
    """Respaldo: Piper (local). Los tiempos de las palabras se reparten por letras."""
    from piper import PiperVoice, SynthesisConfig

    nombre = PIPER[idioma]
    modelo = carpeta / f"{nombre}.onnx"
    if not modelo.exists():
        carpeta.mkdir(parents=True, exist_ok=True)
        subprocess.run(["python", "-m", "piper.download_voices", nombre, "--data-dir", str(carpeta)], check=True)
    voz = PiperVoice.load(str(modelo))
    trozos = list(voz.synthesize(texto, SynthesisConfig(length_scale=longitud)))
    audio = np.concatenate([c.audio_float_array for c in trozos])
    sr = trozos[0].sample_rate
    audio = np.interp(np.arange(int(len(audio) * SR / sr)) * sr / SR, np.arange(len(audio)), audio).astype(np.float32)
    audio, _ = _recortar(audio, [])
    return Locucion(audio, repartir(texto, len(audio) / SR), f"piper:{nombre}")


def repartir(texto: str, duracion: float) -> list[tuple[str, float, float]]:
    """Tiempos aproximados de cada palabra (proporcionales a sus letras)."""
    palabras = texto.split()
    pesos = [len(re.sub(r"\W", "", w)) + 2 for w in palabras]
    total = sum(pesos) or 1
    t, out = 0.0, []
    for w, p in zip(palabras, pesos):
        d = duracion * p / total
        out.append((w, t, t + d))
        t += d
    return out


class Narrador:
    """Sintetiza frases con caché, calibra la velocidad y recuerda si tuvo que usar el respaldo."""

    def __init__(self, idioma: str, cache: Path):
        self.idioma = idioma
        self.cache = cache / "voz"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.velocidad = "+0%"
        self.avisos: list[str] = []
        self.voz = VOCES[idioma]

    def _clave(self, texto, voz, vel):
        return hashlib.sha1(f"{voz}|{vel}|{texto}".encode()).hexdigest()[:20]

    def decir(self, texto: str) -> Locucion:
        for voz in [self.voz] + VOCES_RESPALDO[self.idioma]:
            k = self._clave(texto, voz, self.velocidad)
            wav, meta = self.cache / f"{k}.f32", self.cache / f"{k}.json"
            if wav.exists() and meta.exists():
                m = json.loads(meta.read_text())
                return Locucion(np.fromfile(wav, np.float32), [tuple(x) for x in m["palabras"]], m["motor"])
            for intento in range(3):
                try:
                    loc = edge(texto, voz, self.velocidad)
                    loc.audio.astype(np.float32).tofile(wav)
                    meta.write_text(json.dumps({"palabras": loc.palabras, "motor": loc.motor}))
                    if voz != self.voz:
                        self.avisos.append(f"La voz {self.voz} falló; se usó {voz}.")
                    return loc
                except Exception as e:  # noqa: BLE001 — red o servicio: se reintenta y luego se pasa al respaldo
                    ultimo = e
                    import time

                    time.sleep(2 + 3 * intento)
        self.avisos.append(f"Edge TTS falló ({type(ultimo).__name__}: {ultimo}); se usó Piper como respaldo.")
        return piper(texto, self.idioma, self.cache / "piper")

    def calibrar(self, frases: list[str]):
        """Ajusta la velocidad para que la narración vaya a unas 165 palabras por minuto."""
        muestra = " ".join(frases[:4])
        loc = self.decir(muestra)
        palabras = len(muestra.split())
        ppm = palabras / max(0.5, loc.duracion) * 60
        pct = int(round((OBJETIVO_PPM * 1.06 / ppm - 1) * 100))  # +6 %: las pausas entre frases también cuentan
        pct = max(-20, min(25, pct))
        self.velocidad = f"{pct:+d}%"
        return ppm, self.velocidad
