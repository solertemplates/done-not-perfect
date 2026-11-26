import numpy as np
import pytest

from dnp.lienzo import FONDO

# Umbral de blackdetect (pix_th=0.10) en luma de rango completo: ~25.5.
UMBRAL_LUMA = 26


def luma(img):
    a = np.asarray(img).astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def test_tamano_y_fondo(escena):
    img = escena.fotograma(0)
    assert img.size == (1080, 1920)
    assert img.getpixel((1070, 1000)) == FONDO


def test_ultimo_fotograma_empalma_con_el_primero(escena):
    ep = escena.ep
    primero = np.asarray(escena.fotograma(0))
    ultimo = np.asarray(escena.fotograma((ep.num_fotogramas - 1) / ep.fps))
    assert np.array_equal(primero, ultimo)


def test_gancho_y_final_misma_escena(escena):
    # Durante el gancho y el cierre la acción está en su estado final.
    assert escena.accion(0) == escena.accion(0.9) == escena.accion(escena.A + 0.01) == 11


def test_rebobinado_vuelve_al_principio(escena):
    a = [escena.accion(escena.g + i * 0.1) for i in range(int((escena.r - escena.g) / 0.1))]
    assert all(x >= y for x, y in zip(a, a[1:]))
    assert escena.accion(escena.r - 1e-6) < 0.05


@pytest.mark.parametrize("seg", [i * 0.5 for i in range(36)])
def test_nunca_negro(escena, seg):
    """Margen amplio frente a blackdetect: >= 4 % de píxeles claros (el límite es 2 %)."""
    claros = float(np.mean(luma(escena.fotograma(seg)) > UMBRAL_LUMA))
    assert claros > 0.04, f"segundo {seg}: solo {claros:.1%} de píxeles claros"


def test_hacedor_termina_y_perfeccionista_no(escena):
    _, final = escena.tiempos_ciclo()
    assert escena._inclinacion(11) == pytest.approx(escena.incl1)
    assert escena._fases(11)[0] == "fin"
    assert len(escena.tiempos_ciclo()[0]) == escena.intentos == 3


def test_eventos_de_audio_dentro_del_video(escena):
    ev = escena.eventos_audio()
    nombres = {e[1] for e in ev}
    assert {"martillo", "borrador", "papel", "suspiro", "ding", "rebobinado"} <= nombres
    assert all(0 <= e[0] < escena.D for e in ev)
    assert sum(1 for e in ev if e[1] == "papel") == 3
