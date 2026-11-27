from pathlib import Path

import numpy as np
import pytest

from dnp import audio, musica


@pytest.fixture(scope="module")
def mezcla(escena):
    ajustes = dict(escena.ep["audio"], musica="generada")
    return audio.mezclar(escena.D, escena.eventos_audio(), ajustes, Path("."))


def test_duracion_y_canales(mezcla, escena):
    x, origen = mezcla
    assert x.shape == (int(escena.D * audio.SR), 2)
    assert origen.startswith("generada por código: estilo ")


def test_sin_saturar_ni_nan(mezcla):
    x, _ = mezcla
    assert np.isfinite(x).all()
    assert np.max(np.abs(x)) <= 0.9


def test_no_esta_en_silencio(mezcla):
    x, _ = mezcla
    assert np.sqrt(np.mean(x ** 2)) > 0.02


@pytest.mark.parametrize("estilo", musica.ESTILOS)
def test_cada_estilo_en_bucle_sin_salto(estilo):
    m, r = musica.generar(18, "ep09_prueba", estilo)
    assert r["estilo"] == estilo and m.shape == (18 * audio.SR, 2) and np.isfinite(m).all()
    salto = np.max(np.abs(m[0] - m[-1]))
    paso_normal = np.percentile(np.abs(np.diff(m, axis=0)), 99)
    assert salto <= paso_normal * 3
    assert np.max(np.abs(m)) < 1


def test_hay_al_menos_8_estilos():
    assert {"alegre", "epico_suave", "lofi", "piano", "ukelele", "electronico_suave", "misterio",
            "triunfal"} <= set(musica.ESTILOS)


def test_ocho_episodios_seguidos_no_repiten_estilo():
    estilos = [musica.receta(f"ep{n:02d}_x")["estilo"] for n in range(7, 15)]
    assert len(set(estilos)) == 8


def test_cada_episodio_suena_distinto():
    """Mismo estilo, otro id: cambia la tonalidad, el tempo, la progresión o la melodía."""
    recetas = [musica.receta(f"ep{n:02d}_x") for n in (3, 11, 19, 27)]  # mismo estilo (n*3 % 8)
    assert len({r["estilo"] for r in recetas}) == 1
    claves = {(r["tonica"], round(r["bpm"]), tuple(r["progresion"]), r["semilla"]) for r in recetas}
    assert len(claves) == 4
    a, _ = musica.generar(16, "ep03_x")
    b, _ = musica.generar(16, "ep11_x")
    assert not np.allclose(a, b)


def test_la_misma_musica_para_el_mismo_id():
    a, _ = musica.generar(16, "ep05_igual")
    b, _ = musica.generar(16, "ep05_igual")
    assert np.array_equal(a, b)


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
