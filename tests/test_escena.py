"""Reglas comunes a todos los episodios (bucle, cero negros, fondo, estrellas, luz)."""
import numpy as np
import pytest

from dnp.lienzo import FONDOS

UMBRAL_LUMA = 26  # umbral de blackdetect (pix_th=0.10) en luma de rango completo


def luma(img):
    a = np.asarray(img).astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def test_tamano_y_fondo_en_degradado_radial(cada_escena):
    """Degradado radial: el centro lleva el color vivo del fondo y los bordes se oscurecen."""
    img = cada_escena.fotograma(0)
    assert img.size == (1080, 1920)
    mapa = cada_escena._componer.dif + np.array(FONDOS[cada_escena.ep["fondo"]], np.float32)[:, None, None]
    lum = 0.2126 * mapa[0] + 0.7152 * mapa[1] + 0.0722 * mapa[2]
    for y0, y1, _ in cada_escena._zonas_color():
        zona = lum[int(y0):int(y1)]
        centro = zona[len(zona) // 2 - 100:len(zona) // 2 + 100, 440:640].mean()
        esquinas = [zona[:20, :20].mean(), zona[-20:, -20:].mean()]
        assert all(e < centro * 0.35 for e in esquinas)
        assert centro > 30  # el centro siempre tiene color


def test_los_personajes_siguen_blancos(cada_escena):
    """El degradado no toca lo que tiene color propio: el blanco sigue siendo blanco puro."""
    from PIL import Image

    from dnp.lienzo import BLANCO

    img = Image.new("RGB", (1080, 1920), FONDOS[cada_escena.ep["fondo"]])
    img.paste(BLANCO, (0, 0, 60, 60))
    img.paste(BLANCO, (1000, 1840, 1080, 1920))
    out = np.asarray(cada_escena._componer(img))
    assert (out[:60, :60] == BLANCO).all() and (out[-60:, -60:] == BLANCO).all()


def test_colores_de_concepto_intactos_con_halo(cada_escena):
    from PIL import Image

    from dnp.lienzo import ROJO

    y0, y1, _ = cada_escena._zonas_color()[0]
    cy = int((y0 + y1) / 2)
    img = Image.new("RGB", (1080, 1920), FONDOS[cada_escena.ep["fondo"]])
    img.paste(ROJO, (500, cy - 40, 580, cy + 40))
    out = np.asarray(cada_escena._componer(img)).astype(int)
    assert (out[cy - 30:cy + 30, 510:570] == ROJO).all()
    fuera = out[cy, 588]  # justo al lado: fondo oscurecido (halo)
    lejos = out[cy, 640]
    assert fuera.sum() < lejos.sum()


def test_ultimo_fotograma_empalma_con_el_primero(cada_escena):
    ep = cada_escena.ep
    primero = np.asarray(cada_escena.fotograma(0))
    ultimo = np.asarray(cada_escena.fotograma((ep.num_fotogramas - 1) / ep.fps))
    assert np.array_equal(primero, ultimo)


def test_gancho_y_final_misma_escena(cada_escena):
    e = cada_escena
    assert e.accion(0) == e.accion(0.9) == e.accion(e.A + 0.01) == 11


def test_rebobinado_vuelve_al_principio(cada_escena):
    e = cada_escena
    a = [e.accion(e.g + i * 0.1) for i in range(int((e.r - e.g) / 0.1))]
    assert all(x >= y for x, y in zip(a, a[1:]))
    assert e.accion(e.r - 1e-6) < 0.05


@pytest.mark.parametrize("seg", [i * 0.5 for i in range(36)])
def test_nunca_negro(cada_escena, seg):
    """Margen amplio frente a blackdetect: >= 4 % de píxeles claros (el límite es 2 %)."""
    claros = float(np.mean(luma(cada_escena.fotograma(seg)) > UMBRAL_LUMA))
    assert claros > 0.04, f"segundo {seg}: solo {claros:.1%} de píxeles claros"


def test_eventos_de_audio_dentro_del_video(cada_escena):
    ev = cada_escena.eventos_audio()
    nombres = {e[1] for e in ev}
    assert {"suspiro", "ding", "rebobinado", "titulo"} <= nombres
    assert nombres & {"martillo", "mandarria"}
    assert all(0 <= e[0] < cada_escena.D for e in ev)


def test_hay_estrellas_que_parpadean(cada_escena):
    e = cada_escena
    assert len(e.estrellas) >= 3
    brillos = [[s.brillo_en(f) for f in np.linspace(0, 1, 9)] for s in e.estrellas]
    assert any(max(b) - min(b) > 0.1 for b in brillos)
    for s in e.estrellas:
        assert s.brillo_en(0.0) == pytest.approx(s.brillo_en(1.0))


def test_luz_de_lampara_ambar_y_suave(cada_escena):
    from dnp.lienzo import LUZ_LAMPARA

    conf = cada_escena.ep["guion"]
    escenas = [conf[z]["escena"] for z in ("arriba", "abajo")] if "arriba" in conf else [conf["escena"]]
    if not any("lampara" in e for e in escenas):
        pytest.skip("este episodio no tiene lámpara")
    arr = np.asarray(cada_escena._fondo.reduce(2)).astype(np.float32)
    base = np.array(FONDOS[cada_escena.ep["fondo"]], np.float32)
    hacia = np.array(LUZ_LAMPARA, np.float32) - base
    alfa = ((arr - base) @ hacia) / (hacia @ hacia)  # cuánta luz ámbar tiene cada píxel
    luz = (alfa > 0.03) & (np.linalg.norm(arr - base - alfa[..., None] * hacia, axis=-1) < 6)
    assert luz.mean() > 0.02  # hay luz
    assert np.percentile(alfa[luz], 90) < 0.35  # y es suave
