"""Piezas de negocio: calle_mercado, kiosco, limonada, cartel_precio, monedas, bolsa_dinero, clientes y sus acciones."""
import json
from pathlib import Path

import numpy as np
import pytest

from dnp import audio
from dnp.config import ErrorConfig, validar
from dnp.lienzo import AMARILLO, AMBIENTE, AZUL, ROJO, VERDE
from dnp.render import crear_escena

DATOS = Path(__file__).parent / "datos" / "mercado.json"


@pytest.fixture(scope="module")
def mercado():
    return crear_escena(validar(json.loads(DATOS.read_text(encoding="utf-8"))))


@pytest.fixture
def datos_mercado():
    return json.loads(DATOS.read_text(encoding="utf-8"))


def test_es_valido_y_dibuja(mercado):
    for t in (0, 5, 8, 11, 13.5):
        img = np.asarray(mercado.fotograma(t))
        assert (img.sum(-1) > 300).mean() > 0.03


def test_bucle(mercado):
    n = mercado.ep.num_fotogramas
    assert np.array_equal(np.asarray(mercado.fotograma(0)), np.asarray(mercado.fotograma((n - 1) / 30)))


def test_stock_baja_sube_y_se_vacia(mercado):
    h, p = mercado.objeto(0, "limo_h"), mercado.objeto(0, "limo_p")
    assert h.stock(6.0) == 4
    assert h.stock(9.4) == 1  # vendió 3
    assert h.stock(10.0) == 4  # repuso 3
    assert p.stock(12.0) == 6 and p.stock(13.5) == 0  # el otro se lo compró todo


def test_bolsas_crecen_con_las_ventas(mercado):
    bh, bp = mercado.objeto(0, "bolsa_h"), mercado.objeto(0, "bolsa_p")
    assert bh.monedas(6.0) == 1 and bh.monedas(10.0) == 4
    assert bp.monedas(14) == 1 + 5  # pago de comprar_todo


def test_precio_cambia_y_se_tacha(mercado):
    c = mercado.objeto(0, "precio_p")
    assert c.precio(9.0)[0] == "$5" and c.precio(11.0)[0] == "$3"


def test_clientes_se_cambian_de_kiosco_y_se_van_servidos(mercado):
    gente = mercado.objeto(0, "gente")
    kp, kh = mercado.objeto(0, "kp"), mercado.objeto(0, "kh")
    antes = [p[0] for p in gente._simular(5.0)]
    assert antes == [kp.puesto_cola(i) for i in range(3)]  # en la cola del kiosco de la derecha
    despues = [p[0] for p in gente._simular(7.0)]
    assert despues == [kh.puesto_cola(i) for i in range(3)]  # se han cambiado al de la izquierda
    final = gente._simular(12.0)
    assert all(p[3] for p in final)  # los tres se llevan su vaso...
    assert all(p[0][0] > 1160 for p in final)  # ...y se van de la pantalla


def test_acciones_de_gesto(mercado):
    p = mercado.actor(0, "perfeccionista")
    assert p.estado(4.8).pose.parpado >= 0.7  # se ríe con los ojos cerrados
    assert p.estado(9.4).pose.hombros > 10  # hombros caídos
    h = mercado.actor(0, "hacedor")
    assert h.estado(13.8).cajas == 3  # se lleva todo en cajas


def test_sonidos_de_negocio(mercado):
    nombres = [e[1] for e in mercado.eventos_audio()]
    for s in ("monedas", "caja_registradora", "risa", "cajas", "ding"):
        assert s in nombres, s
    for s in ("monedas", "caja_registradora", "risa", "cajas"):
        x = audio.EFECTOS[s]()
        assert np.isfinite(x).all() and 0.05 < np.abs(x).max() <= 1.0


def test_kiosco_de_otro_id(datos_mercado):
    datos_mercado["guion"]["objetos"][2]["kiosco"] = "kx"
    with pytest.raises(ErrorConfig) as e:
        validar(datos_mercado)
    assert "no hay ningún kiosco con ese id" in str(e.value)


def test_toldo_desconocido(datos_mercado):
    datos_mercado["guion"]["objetos"][0]["toldo"] = "verde_blanco"
    with pytest.raises(ErrorConfig) as e:
        validar(datos_mercado)
    assert "'guion.objetos[0].toldo' vale \"verde_blanco\"" in str(e.value)


def test_paleta_de_ambiente_distinta_de_los_colores_de_concepto():
    for nombre, c in AMBIENTE.items():
        for concepto in (VERDE, ROJO, AZUL):
            assert sum(abs(a - b) for a, b in zip(c, concepto)) > 100, nombre
    assert AMBIENTE["ambar"] != AMARILLO
