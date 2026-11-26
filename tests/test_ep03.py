"""Episodio 3 'Los dos martillos' y el motor de objetos con vida."""
import math

import numpy as np
import pytest

from dnp import ep03_martillos as m
from dnp.objetos import (CARA_GOLPEO, Clave, EstadoObjeto, Expresion, PistaObjeto, martillo,
                         mezclar_expresion)


def test_cada_toc_cae_justo_en_su_clavo(martillos):
    obj = martillos.hacedor
    for i, ((_, clavo), tocs) in enumerate(zip(m.PIEZAS, m.TOCS)):
        for tau in tocs:
            est = martillos.pista_h.en(tau)
            cara = obj.a_panel(est, CARA_GOLPEO)
            assert math.dist(cara, clavo) < 8, f"pieza {i}, toc {tau}: golpea en {cara}, el clavo está en {clavo}"


def test_el_clavo_se_tuerce_y_se_endereza(martillos):
    assert martillos._altura_clavo(m.TORCIDO, m.T_TUERCE - 0.01)[1] == 0
    assert martillos._altura_clavo(m.TORCIDO, m.T_TUERCE + 0.2)[1] == pytest.approx(m.DOBLEZ)
    assert martillos._altura_clavo(m.TORCIDO, m.T_ENDEREZA + 0.1)[1] == 0


def test_hacedor_termina_la_caja(martillos):
    for i in range(len(m.PIEZAS)):
        assert martillos._altura_clavo(i, 11.0) == (0, 0)  # todos los clavos, hasta el fondo


def test_perfeccionista_no_termina_nunca(martillos):
    est, clavo, regla = martillos._estado_p(11.0)
    assert clavo == ("tabla", 20.0)  # el clavo sigue a medio poner
    assert martillos._fase_p(11.0)[0] == "final"
    assert math.dist(regla, (m.CLAVO_P[0] + 22, m.CLAVO_P[1] - m.REGLA_LARGO / 2)) < 1  # midiéndolo
    # Levanta el martillo y lo vuelve a bajar sin golpear.
    estados = [martillos._estado_p(a)[0] for a in np.linspace(*m.T_DUDA, 30)]
    assert min(e.pos[1] for e in estados) < m.MESA - 40  # se despega de la mesa
    assert max(e.angulo for e in estados) > -8 + 8
    assert estados[-1].angulo == pytest.approx(-8.0) and estados[-1].pos[1] == m.MESA


def test_tres_intentos_con_regla(martillos):
    ev = martillos.eventos_audio()
    assert sum(1 for e in ev if e[1] == "regla") == 2 * martillos.intentos == 6
    assert sum(1 for e in ev if e[1] == "clavo_torcido") == 1


def test_martillos_dentro_de_la_pantalla(martillos):
    """Ninguna parte de los martillos se sale por los lados en todo el episodio."""
    for a in np.linspace(0, 11, 111):
        for obj, est in ((martillos.hacedor, martillos._estado_h(a)), (martillos.perfeccionista,
                                                                       martillos._estado_p(a)[0])):
            for f in obj.formas:
                for p in f.puntos:
                    x, _ = obj.a_panel(est, p)
                    assert -5 <= x <= 1085, f"a={a:.1f}: se sale por x={x:.0f}"


# --- Motor de objetos ----------------------------------------------------------------

def test_espejo_invierte_horizontalmente():
    obj = martillo()
    normal = obj.a_panel(EstadoObjeto(pos=(500, 500)), CARA_GOLPEO)
    espejo = obj.a_panel(EstadoObjeto(pos=(500, 500), espejo=True), CARA_GOLPEO)
    assert normal[0] - 500 == pytest.approx(500 - espejo[0])
    assert normal[1] == pytest.approx(espejo[1])


def test_tam_escala_desde_el_apoyo():
    grande = martillo(tam=2.0).a_panel(EstadoObjeto(pos=(0, 0)), (10, -100))
    assert grande == pytest.approx((20, -200))


def test_pista_de_estados_interpola_y_salta():
    a = EstadoObjeto(pos=(0, 0))
    b = EstadoObjeto(pos=(100, 0), angulo=30, expresion=Expresion(sonrisa=-1))
    pista = PistaObjeto([Clave(0, a), Clave(1, b, "lineal", salto=50)])
    medio = pista.en(0.5)
    assert medio.pos == pytest.approx((50, -50))
    assert medio.angulo == pytest.approx(15)
    assert medio.expresion.sonrisa == pytest.approx(0)
    assert pista.en(5).pos == (100, 0)


def test_mezclar_expresion():
    e = mezclar_expresion(Expresion(cejas=1), Expresion(cejas=-1, ojos_felices=1), 0.25)
    assert e.cejas == pytest.approx(0.5)
    assert e.ojos_felices == pytest.approx(0.25)


def test_objeto_se_dibuja_en_blanco():
    from PIL import Image

    from dnp.lienzo import BLANCO, FONDOS, Lienzo, usar_fondo

    usar_fondo(FONDOS["gris_pizarra"])
    img = Image.new("RGB", (800, 800), FONDOS["gris_pizarra"])
    martillo(gafas=True, brazos=True).dibujar(Lienzo(img, 0, 0, escala=2), EstadoObjeto(pos=(200, 380)))
    arr = np.asarray(img)
    blancos = np.all(arr == BLANCO, axis=-1).mean()
    assert blancos > 0.03  # el cuerpo es blanco y se ve
