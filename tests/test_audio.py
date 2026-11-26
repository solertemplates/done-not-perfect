from pathlib import Path

import numpy as np
import pytest

from dnp import audio


@pytest.fixture(scope="module")
def mezcla(escena):
    ajustes = dict(escena.ep["audio"], musica="generada")
    return audio.mezclar(escena.D, escena.eventos_audio(), ajustes, Path("."))


def test_duracion_y_canales(mezcla, escena):
    x, origen = mezcla
    assert x.shape == (int(escena.D * audio.SR), 2)
    assert origen == "generada por código"


def test_sin_saturar_ni_nan(mezcla):
    x, _ = mezcla
    assert np.isfinite(x).all()
    assert np.max(np.abs(x)) <= 0.9


def test_no_esta_en_silencio(mezcla):
    x, _ = mezcla
    assert np.sqrt(np.mean(x ** 2)) > 0.02


def test_musica_en_bucle_sin_salto():
    m = audio.musica(18, 80)
    salto = np.max(np.abs(m[0] - m[-1]))
    paso_normal = np.percentile(np.abs(np.diff(m, axis=0)), 99)
    assert salto <= paso_normal * 3


@pytest.mark.parametrize("nombre", list(audio.EFECTOS))
def test_efectos(nombre):
    params = {"dur": 0.6} if nombre in ("lapiz", "borrador", "rebobinado", "suspiro") else {}
    s = audio.EFECTOS[nombre](**params)
    assert len(s) > 0 and np.isfinite(s).all() and np.max(np.abs(s)) > 0.01


def test_buscar_musica(tmp_path):
    assert audio.buscar_musica(tmp_path, "auto") is None
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "LEEME.md").write_text("x")
    assert audio.buscar_musica(tmp_path, "auto") is None
    (tmp_path / "audio" / "otra.wav").write_bytes(b"")
    (tmp_path / "audio" / "musica.mp3").write_bytes(b"")
    assert audio.buscar_musica(tmp_path, "auto").name == "musica.mp3"
    assert audio.buscar_musica(tmp_path, "generada") is None
    with pytest.raises(FileNotFoundError):
        audio.buscar_musica(tmp_path, "audio/no_existe.mp3")


def test_wav(tmp_path):
    import wave

    p = tmp_path / "a.wav"
    audio.guardar_wav(p, np.zeros((480, 2)))
    with wave.open(str(p)) as w:
        assert (w.getnchannels(), w.getframerate(), w.getnframes()) == (2, 48000, 480)
