"""Guiones en JSON: validación en español y comportamiento de las piezas y acciones."""
import math

import numpy as np
import pytest

from dnp import biblioteca as bib
from dnp import piezas as pz
from dnp.config import ErrorConfig, validar
from dnp.objetos import CARA_GOLPEO


def errores(datos):
    with pytest.raises(ErrorConfig) as e:
        validar(datos)
    return e.value.errores


# =============================================================== VALIDACIÓN
def test_los_cuatro_episodios_son_validos(datos, datos_roca, datos_martillos):
    for d in (datos, datos_roca, datos_martillos):
        validar(d)


def test_accion_desconocida_sugiere(datos):
    datos["guion"]["arriba"]["personajes"][0]["acciones"][2]["accion"] = "sorprenderce"
    e = errores(datos)[0]
    assert "'guion.arriba.personajes[0].acciones[2].accion' vale \"sorprenderce\"" in e
    assert "¿Querías decir \"sorprenderse\"?" in e


def test_accion_de_objeto_no_vale_para_munecos(datos):
    datos["guion"]["arriba"]["personajes"][0]["acciones"][2]["accion"] = "sacar_clavo"
    assert "no está permitido" in errores(datos)[0]


def test_referencia_a_objeto_que_no_existe(datos):
    datos["guion"]["arriba"]["personajes"][0]["acciones"][1]["objeto"] = "mesa"
    e = " ".join(errores(datos))
    assert "'guion.arriba.personajes[0].acciones[1].objeto' es \"mesa\", pero no hay ningún objeto con ese id" in e


def test_referencia_a_objeto_de_otro_tipo(datos):
    datos["guion"]["arriba"]["personajes"][0]["acciones"][1]["objeto"] = "madera"
    assert "apunta a un objeto \"pila_madera\"" in " ".join(errores(datos))


def test_acciones_fuera_de_tiempo(datos_roca):
    datos_roca["guion"]["arriba"]["personajes"][0]["acciones"][0]["desde_s"] = 1.0
    assert "tienen que pasar entre el final del rebobinado (3 s)" in errores(datos_roca)[0]


def test_acciones_solapadas(datos_roca):
    datos_roca["guion"]["abajo"]["personajes"][0]["acciones"][1]["desde_s"] = 12.0
    assert "empieza (12.0 s) antes de que termine la acción anterior (13.0 s)" in errores(datos_roca)[0]


def test_golpear_necesita_mandarria(datos_roca):
    datos_roca["guion"]["arriba"]["personajes"][0]["herramienta"] = "martillo"
    assert "necesita \"herramienta\": \"mandarria\"" in " ".join(errores(datos_roca))


def test_plano_necesita_estar_sentado(datos):
    del datos["guion"]["abajo"]["personajes"][0]["postura"]
    assert "\"postura\": \"sentado_suelo\"" in errores(datos)[0]


def test_solo_un_cartel(datos):
    datos["guion"]["arriba"]["escena"]["cartel"] = dict(datos["guion"]["abajo"]["escena"]["cartel"])
    assert "Solo puede haber 1 cartel" in errores(datos)[0]


def test_taller_solo_en_escena_unica(datos):
    datos["guion"]["arriba"]["escena"]["tipo"] = "taller"
    assert "solo sirve con \"formato\": \"escena_unica\"" in errores(datos)[0]


def test_contador_de_un_personaje_que_no_existe(datos_roca):
    datos_roca["guion"]["arriba"]["objetos"][1]["de"] = "fantasma"
    assert "no hay ningún personaje con ese id" in errores(datos_roca)[0]


def test_lista_de_numeros(datos):
    datos["guion"]["arriba"]["personajes"][0]["acciones"][5]["golpes_s"] = [11.15, "once"]
    assert "'guion.arriba.personajes[0].acciones[5].golpes_s[1]' debe ser número" in errores(datos)[0]


def test_ids_repetidos(datos):
    datos["guion"]["arriba"]["objetos"].append({"tipo": "silla"})
    assert "hay dos objetos con el id \"silla\"" in errores(datos)[0]


def test_formato_desconocido(datos):
    datos["guion"]["formato"] = "tres_paneles"
    assert "'guion.formato' vale \"tres_paneles\"" in errores(datos)[0]


def test_escena_unica_con_habitacion_es_valida(datos_martillos):
    datos_martillos["guion"]["escena"] = {"tipo": "habitacion", "lampara": {"x": 540, "cable": 150},
                                          "siluetas": "ciudad"}
    validar(datos_martillos)


# ============================================================ EPISODIO 1
def test_silla_se_tuerce_se_tambalea_y_se_arregla(escena):
    silla = escena.objeto(0, "silla")
    assert silla.inclinacion(8.0) == 0
    assert silla.inclinacion(9.0) == pytest.approx(7)
    assert silla.inclinacion(14) == pytest.approx(2.5)
    assert len(silla.t_golpe) == 6


def test_perfeccionista_arruga_tres_hojas(escena):
    perf = escena.actor(1, "perfeccionista")
    assert len(perf.lanzamientos()) == 3
    assert perf.fase_plano(14.0)[0] == "fin"


# ============================================================ EPISODIO 2
def test_escalera_se_refuerza_y_sube_hasta_arriba(escalera):
    esc = escalera.objeto(0, "escalera")
    assert esc.torcido(14) == pytest.approx(2.5)
    assert esc.torcido(14) < esc.torcido(9.0)
    assert esc.balanceo(14) == 0
    hacedor = escalera.actor(0, "hacedor")
    assert hacedor.estado(14).pose.cadera[1] == pytest.approx(pz.y_nivel(4) - 182)


# ============================================================ EPISODIO 3
def test_cada_toc_cae_justo_en_su_clavo(martillos):
    h = martillos.actor(0, "martillo_hacedor")
    caja = martillos.objeto(0, "caja")
    for i, ((_, clavo), tocs) in enumerate(zip(pz.PIEZAS_CAJA, caja.tocs)):
        for tau in tocs:
            cara = h.forma.a_panel(h.estado(tau), CARA_GOLPEO)
            assert math.dist(cara, clavo) < 8, (i, tau, cara, clavo)


def test_el_clavo_se_tuerce_y_se_endereza(martillos):
    caja = martillos.objeto(0, "caja")
    parte, tt, te = caja.torcido
    assert caja.altura_clavo(parte, tt - 0.01)[1] == 0
    assert caja.altura_clavo(parte, tt + 0.2)[1] == pytest.approx(pz.DOBLEZ)
    assert caja.altura_clavo(parte, te + 0.1)[1] == 0
    for i in range(5):
        assert caja.altura_clavo(i, 14.0) == (0, 0)


def test_perfeccionista_martillo_no_termina(martillos):
    p = martillos.actor(0, "martillo_perfeccionista")
    assert p.clavo_en(14.0) == ("tabla", 20.0)
    estados = [p.estado(t) for t in np.linspace(10.2, 11.6, 30)]
    assert min(e.pos[1] for e in estados) < 1250 - 40  # levanta el martillo...
    assert estados[-1].pos[1] == 1250  # ...y lo baja sin golpear


def test_martillos_dentro_de_la_pantalla(martillos):
    for t in np.linspace(3, 14, 111):
        for a in martillos.zonas[0][2]:
            est = a.estado(t)
            for f in a.forma.formas:
                for p in f.puntos:
                    assert -5 <= a.forma.a_panel(est, p)[0] <= 1085


# ============================================================ EPISODIO 4
def test_contadores_99_y_100(roca):
    h, p = roca.actor(0, "hacedor"), roca.actor(1, "perfeccionista")
    assert h.golpes_hasta(roca.D) == 100 and p.golpes_hasta(roca.D) == 99
    assert h.golpes_hasta(13.0) == p.golpes_hasta(13.0) == 99


def test_la_roca_se_parte_en_el_golpe_100(roca):
    r = roca.objeto(0, "roca")
    assert r.t_partida == pytest.approx(14.0)
    assert r.separacion(13.99) == 0 and r.separacion(15) == 1
    assert roca.objeto(1, "roca").t_partida is None


def test_el_perfeccionista_se_rinde_de_espaldas(roca):
    c = roca.actor(1, "perfeccionista").estado(roca.A)
    assert c.pose.espalda and c.pose.mira == -1 and c.agarre is None and c.suelo is not None
    assert c.escala < 1 and c.subida > 0 and c.pose.cabeza > 10


# ======================================================= PIEZAS NUEVAS
def test_caminar_y_dudar_y_suspirar_de_pie(datos_roca):
    from dnp.render import crear_escena
    from dnp.config import validar as v

    acc = datos_roca["guion"]["abajo"]["personajes"][0]["acciones"]
    acc[1] = {"accion": "dudar", "desde_s": 13.0, "hasta_s": 13.8}
    acc.append({"accion": "suspirar", "desde_s": 13.8, "hasta_s": 14.3})
    acc.append({"accion": "caminar", "desde_s": 14.3, "hasta_s": 15.0, "x": 200, "de_espaldas": True})
    e = crear_escena(v(datos_roca))
    p = e.actor(1, "perfeccionista")
    assert p.estado(15.0).pose.cadera[0] == pytest.approx(200)
    assert p.estado(15.0).pose.espalda
    assert p.estado(14.3).pose.sonrisa < 0
    assert np.asarray(e.fotograma(16)).std() > 5


def test_roca_igual_para_la_misma_semilla():
    assert bib.Roca().contorno == bib.Roca().contorno


def test_escena_unica_con_munecos_y_dx(datos):
    """Los dos muñecos juntos en una habitación, cada uno en su lado con dx."""
    from dnp.render import crear_escena

    g = datos["guion"]
    arr, aba = g["arriba"], g["abajo"]
    h, p = arr["personajes"][0], aba["personajes"][0]
    h["dx"], p["dx"] = -250, 290
    for a in h["acciones"]:
        if a.get("madera"):
            a["madera"] = "madera_h"
    objetos = [dict(arr["objetos"][0], id="madera_h", dx=-130), dict(arr["objetos"][1], dx=-250),
               dict(aba["objetos"][1], dx=290)]
    datos["guion"] = {"formato": "escena_unica", "escena": {"tipo": "habitacion", "siluetas": "ciudad",
                      "lampara": {"x": 820, "cable": 120}}, "objetos": objetos, "personajes": [p, h]}
    e = crear_escena(validar(datos))
    img = np.asarray(e.fotograma(6))
    assert img.shape == (1920, 1080, 3) and (img.sum(-1) > 300).mean() > 0.02
