import shutil
import struct
import subprocess

import pytest

from dnp.verificar import atomos_principales, verificar, zonas_negras

hay_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="falta ffmpeg")


def atomo(tipo, contenido=b""):
    return struct.pack(">I4s", 8 + len(contenido), tipo) + contenido


def test_atomos_faststart():
    assert atomos_principales(atomo(b"ftyp") + atomo(b"moov", b"x" * 4) + atomo(b"mdat")) == ["ftyp", "moov", "mdat"]


def test_parse_blackdetect():
    texto = "[blackdetect @ 0x1] black_start:0 black_end:0.5 black_duration:0.5\n"
    assert len(zonas_negras(texto)) == 1
    assert zonas_negras("nada") == []


@hay_ffmpeg
def test_video_negro_falla(tmp_path):
    mp4 = tmp_path / "negro.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:s=1080x1920:r=30:d=15", "-f", "lavfi",
         "-i", "anullsrc=r=44100:cl=mono", "-t", "15", "-c:v", "libx264", "-profile:v", "main", "-pix_fmt",
         "yuv420p", "-c:a", "aac", str(mp4)], check=True)
    res = {r.nombre: r.ok for r in verificar(mp4, None, 1080, 1920, 30, 15)}
    assert not res["Cero fotogramas en negro (blackdetect d=0.03 pix_th=0.10)"]
    assert not res["Perfil High"]
    assert not res["Audio 48 kHz"]
    assert not res["Audio estéreo"]
    assert not res["+faststart (moov antes que mdat)"]
    assert res["Resolución"]
