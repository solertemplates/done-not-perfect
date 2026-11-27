"""Comprobaciones del MP4 final (ffprobe + blackdetect + bucle + miniatura)."""
from __future__ import annotations

import json
import re
import struct
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image


@dataclass
class Resultado:
    nombre: str
    ok: bool
    detalle: str


def _ffprobe(ruta: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-count_packets", "-of", "json", str(ruta)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)


def atomos_principales(datos: bytes) -> list[str]:
    """Lista de átomos de primer nivel de un MP4 (para comprobar +faststart)."""
    nombres, i = [], 0
    while i + 8 <= len(datos):
        tam, tipo = struct.unpack(">I4s", datos[i:i + 8])
        if tam == 1 and i + 16 <= len(datos):
            tam = struct.unpack(">Q", datos[i + 8:i + 16])[0]
        elif tam == 0:
            tam = len(datos) - i
        nombres.append(tipo.decode("latin-1"))
        if tam < 8:
            break
        i += tam
    return nombres


def _atomos_archivo(ruta: Path) -> list[str]:
    nombres, i = [], 0
    total = ruta.stat().st_size
    with open(ruta, "rb") as f:
        while i + 8 <= total:
            f.seek(i)
            cab = f.read(16)
            tam, tipo = struct.unpack(">I4s", cab[:8])
            if tam == 1:
                tam = struct.unpack(">Q", cab[8:16])[0]
            elif tam == 0:
                tam = total - i
            nombres.append(tipo.decode("latin-1"))
            if tam < 8:
                break
            i += tam
    return nombres


def zonas_negras(salida_ffmpeg: str) -> list[str]:
    return re.findall(r"black_start:\s*[\d.]+\s+black_end:\s*[\d.]+\s+black_duration:\s*[\d.]+", salida_ffmpeg)


def _blackdetect(ruta: Path) -> str:
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(ruta), "-vf", "blackdetect=d=0.03:pix_th=0.10",
         "-an", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return r.stderr


def _fotograma(ruta: Path, indice: int, ancho: int, alto: int) -> np.ndarray:
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(ruta), "-vf", f"select=eq(n\\,{indice})", "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True,
    )
    return np.frombuffer(r.stdout, np.uint8).reshape(alto, ancho, 3)


def silencios(ruta: Path, umbral_db: float = -45, minimo: float = 0.5) -> list[str]:
    """Tramos en silencio (silencedetect)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(ruta), "-map", "0:a:0", "-af",
                        f"silencedetect=noise={umbral_db}dB:d={minimo}", "-f", "null", "-"],
                       capture_output=True, text=True)
    return re.findall(r"silence_start: ([\d.]+)", r.stderr)


def verificar(mp4: Path, miniatura: Path | None, ancho: int, alto: int, fps: int, duracion: float,
              rango: tuple[float, float] = (15, 20), tam_miniatura: tuple[int, int] | None = None,
              silencio: bool = False) -> list[Resultado]:
    res: list[Resultado] = []

    def chk(nombre, ok, detalle):
        res.append(Resultado(nombre, bool(ok), detalle))

    if not mp4.exists() or mp4.stat().st_size == 0:
        return [Resultado("Archivo MP4", False, f"No existe o está vacío: {mp4}")]
    info = _ffprobe(mp4)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    esperados = int(round(duracion * fps))
    if v is None:
        chk("Pista de vídeo", False, "No hay pista de vídeo")
    else:
        chk("Códec de vídeo H.264", v.get("codec_name") == "h264", v.get("codec_name"))
        chk("Perfil High", v.get("profile") == "High", v.get("profile"))
        chk("Píxeles yuv420p", v.get("pix_fmt") == "yuv420p", v.get("pix_fmt"))
        chk("Resolución", (v.get("width"), v.get("height")) == (ancho, alto), f"{v.get('width')}x{v.get('height')}")
        rf, af = Fraction(v.get("r_frame_rate", "0/1")), Fraction(v.get("avg_frame_rate", "0/1"))
        chk(f"{fps} fps constantes", rf == fps and af == fps, f"r_frame_rate={rf}, avg_frame_rate={af}")
        n = int(v.get("nb_read_packets") or v.get("nb_frames") or 0)
        chk("Número de fotogramas", n == esperados, f"{n} (esperados {esperados})")
        dur_v = float(v.get("duration", 0))
        nombre_dur = f"Duración {rango[0]:g}-{rango[1]:g} s" if rango[0] != rango[1] else f"Duración exacta {rango[0]:g} s"
        chk(nombre_dur, rango[0] - 1.5 / fps <= dur_v <= rango[1] + 1.5 / fps and abs(dur_v - duracion) < 1.5 / fps,
            f"{dur_v:.3f} s")
        # Marcas de tiempo equiespaciadas (CFR real, no solo la cabecera).
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts", "-of", "csv=p=0",
             str(mp4)], capture_output=True, text=True, check=True)
        pts = sorted(int(x) for x in r.stdout.split() if x.strip().lstrip("-").isdigit())
        difs = set(np.diff(pts).tolist()) if len(pts) > 1 else set()
        chk("Intervalo entre fotogramas constante", len(difs) == 1, f"saltos distintos: {sorted(difs)[:5]}")
    if a is None:
        chk("Pista de audio", False, "No hay pista de audio")
    else:
        chk("Audio AAC", a.get("codec_name") == "aac", a.get("codec_name"))
        chk("Audio 48 kHz", a.get("sample_rate") == "48000", a.get("sample_rate"))
        chk("Audio estéreo", a.get("channels") == 2, f"{a.get('channels')} canales")
    atomos = _atomos_archivo(mp4)
    ok_fs = "moov" in atomos and "mdat" in atomos and atomos.index("moov") < atomos.index("mdat")
    chk("+faststart (moov antes que mdat)", ok_fs, " > ".join(atomos))
    negras = zonas_negras(_blackdetect(mp4))
    chk("Cero fotogramas en negro (blackdetect d=0.03 pix_th=0.10)", not negras,
        "ninguno" if not negras else "; ".join(negras[:3]))
    if v is not None:
        primero = _fotograma(mp4, 0, ancho, alto).astype(np.int16)
        ultimo = _fotograma(mp4, esperados - 1, ancho, alto).astype(np.int16)
        dif = float(np.mean(np.abs(primero - ultimo)))
        chk("Bucle: último fotograma = primero", dif < 1.0, f"diferencia media {dif:.3f} (máx. 1.0)")
    if miniatura is not None:
        if miniatura.exists():
            with Image.open(miniatura) as im:
                tam = tam_miniatura or (ancho, alto)
                chk("Miniatura", im.size == tam, f"{miniatura.name} {im.size[0]}x{im.size[1]}")
        else:
            chk("Miniatura", False, "no existe")
    if silencio and a is not None:
        tramos = silencios(mp4)
        chk("Nunca en silencio (silencedetect -45 dB, 0,5 s)", not tramos,
            "ninguno" if not tramos else "silencio en " + ", ".join(f"{float(x):.1f} s" for x in tramos[:5]))
    return res


def informe(res: list[Resultado]) -> str:
    lineas = [f"{'✅' if r.ok else '❌'} {r.nombre}: {r.detalle}" for r in res]
    total = sum(r.ok for r in res)
    lineas.append(f"\n{total}/{len(res)} comprobaciones superadas.")
    return "\n".join(lineas)
