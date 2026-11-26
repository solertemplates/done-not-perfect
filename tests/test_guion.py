"""Episodios hechos solo con JSON (bloque "guion") y piezas de la biblioteca."""
import numpy as np
import pytest

from dnp import biblioteca as bib
from dnp.config import ErrorConfig, validar


def errores(datos):
    with pytest.raises(ErrorConfig) as e:
        validar(datos)
    return e.value.errores


# --- Validación ------------------------------------------------------------------------

def test_ep4_es_valido(datos_roca):
    validar(datos_roca)


def test_guion_no_necesita_bloques_de_episodios_programados(datos_roca):
    datos_roca["hacedor"] = {"inclinacion_tapa_grados": 1}
    assert "Campo desconocido 'hacedor'" in errores(datos_roca)[0]


def test_accion_desconocida_sugiere(datos_roca):
    datos_roca["guion"]["abajo"]["acciones"][1]["accion"] = "rendirsee"
    e = errores(datos_roca)[0]
    assert "'guion.abajo.acciones[1].accion' vale \"rendirsee\"" in e
    assert "¿Querías decir \"rendirse\"?" in e


def test_golpear_necesita_golpes_y_velocidad(datos_roca):
    ac = datos_roca["guion"]["arriba"]["acciones"][0]
    del ac["golpes"]
    ac["velocidad"] = "media"
    e = " ".join(errores(datos_roca))
    assert "Falta el campo obligatorio 'guion.arriba.acciones[0].golpes'." in e
    assert "'guion.arriba.acciones[0].velocidad' vale \"media\"" in e


def test_acciones_fuera_de_tiempo(datos_roca):
    datos_roca["guion"]["arriba"]["acciones"][0]["desde_s"] = 1.0
    assert "tienen que ocurrir entre el final del rebobinado (3 s)" in errores(datos_roca)[0]


def test_acciones_solapadas(datos_roca):
    datos_roca["guion"]["abajo"]["acciones"][1]["desde_s"] = 12.0
    assert "empieza (12.0 s) antes de que termine la acción anterior (13.0 s)" in errores(datos_roca)[0]


def test_golpear_sin_herramienta(datos_roca):
    datos_roca["guion"]["arriba"]["herramienta"] = "ninguna"
    assert "no tiene herramienta" in errores(datos_roca)[0]


def test_escena_desconocida(datos_roca):
    datos_roca["guion"]["escena"] = "playa"
    assert "'guion.escena' vale \"playa\", que no está permitido" in errores(datos_roca)[0]


def test_acciones_debe_ser_lista(datos_roca):
    datos_roca["guion"]["abajo"]["acciones"] = {"accion": "celebrar"}
    assert "'guion.abajo.acciones' debe ser lista [ ]" in errores(datos_roca)[0]


# --- Episodio 4 ------------------------------------------------------------------------------

def test_contadores_99_y_100(roca):
    arriba, abajo = roca.panel("arriba"), roca.panel("abajo")
    assert arriba.golpes_hasta(roca.D) == 100
    assert abajo.golpes_hasta(roca.D) == 99
    assert arriba.golpes_hasta(13.0) == abajo.golpes_hasta(13.0) == 99  # llegan juntos al 99


def test_la_roca_se_parte_en_el_golpe_100(roca):
    arriba, abajo = roca.panel("arriba"), roca.panel("abajo")
    assert arriba.t_partida == pytest.approx(14.0)
    assert arriba.separacion(13.99) == 0 and arriba.separacion(15) == 1
    assert abajo.t_partida is None  # con 99 golpes no se parte


def test_velocidad_rapida_acelera_y_lenta_es_regular(roca):
    golpes = roca.panel("abajo").golpes
    huecos = np.diff(golpes)
    assert huecos[0] > 5 * huecos[-1]  # al final van mucho más rápido
    lento = roca.panel("arriba")._instantes({"desde_s": 0, "hasta_s": 4, "golpes": 4, "velocidad": "lenta"})
    assert lento == pytest.approx([1, 2, 3, 4])


def test_el_perfeccionista_se_rinde_de_espaldas(roca):
    c = roca.panel("abajo").cuerpo(roca.A)
    assert c.pose.espalda and c.pose.mira == -1
    assert c.agarre is None and c.suelo is not None  # soltó la mandarria
    assert c.escala < 1 and c.subida > 0  # se aleja hacia el fondo
    assert c.pose.cabeza > 10  # cabizbajo


def test_el_hacedor_celebra_con_su_mandarria(roca):
    c = roca.panel("arriba").cuerpo(roca.A)
    assert c.agarre is not None and not c.pose.espalda and c.pose.sonrisa > 1


def test_sonidos(roca):
    nombres = [e[1] for e in roca.eventos_audio()]
    for s in ("mandarria", "grieta", "crac", "suspiro", "ding", "rebobinado"):
        assert s in nombres, s
    assert nombres.count("crac") == 1


def test_gancho_muestra_100_y_99(roca):
    assert roca.accion(0) == 11
    ts = roca.ts(roca.accion(0))
    assert roca.panel("arriba").golpes_hasta(ts) == 100
    assert roca.panel("abajo").golpes_hasta(ts) == 99


# --- Biblioteca ---------------------------------------------------------------------------

def test_roca_igual_para_la_misma_semilla():
    assert bib.Roca().contorno == bib.Roca().contorno


def test_roca_mitades_comparten_la_grieta():
    r = bib.Roca()
    assert r.grieta[0] == r.arriba and r.grieta[-1] == r.abajo
    assert all(p in r.mitad_izq for p in r.grieta) and all(p in r.mitad_der for p in r.grieta)


def test_cara_de_golpe_de_la_mandarria():
    p = bib.cara_golpe_mandarria((0, 0), 90)
    assert p == pytest.approx((bib.LARGO_MANDARRIA + 24, 0))
