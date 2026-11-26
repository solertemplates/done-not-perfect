"""Reglas comunes a todos los episodios (bucle, cero negros, fondo, estrellas, luz)."""
import numpy as np
import pytest

from dnp.lienzo import FONDOS

UMBRAL_LUMA = 26  # umbral de blackdetect (pix_th=0.10) en luma de rango completo


def luma(img):
    a = np.asarray(img).astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def test_tamano_y_fondo(cada_escena):
    img = cada_escena.fotograma(0)
    assert img.size == (1080, 1920)
    colores, cuentas = np.unique(np.asarray(img).reshape(-1, 3), axis=0, return_counts=True)
    assert tuple(colores[cuentas.argmax()]) == FONDOS[cada_escena.ep["fondo"]]


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
    conf = cada_escena.ep["guion"]
    escenas = [conf[z]["escena"] for z in ("arriba", "abajo")] if "arriba" in conf else [conf["escena"]]
    if not any("lampara" in e for e in escenas):
        pytest.skip("este episodio no tiene lámpara")
    arr = np.asarray(cada_escena._fondo.reduce(2)).astype(int)
    fondo = np.array(FONDOS[cada_escena.ep["fondo"]])
    calidos = (arr[..., 0] - arr[..., 2] > fondo[0] - fondo[2] + 8) & (arr.sum(-1) < 300)
    assert calidos.mean() > 0.02
    assert arr[calidos].max() < 200
