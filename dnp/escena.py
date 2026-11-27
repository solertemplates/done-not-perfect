"""Escenas y detalles de ambiente, todo configurable desde el JSON.

Escenas base (`"tipo"`):
* "habitacion": suelo de tablas en boceto (para la pantalla partida).
* "taller": techo, mesa de taller con balda y suelo (escena única).
* "cantera_noche": cantera al aire libre de noche con cielo estrellado.
* "calle_mercado": calle de noche con farolas, cielo estrellado y ciudad con ventanas encendidas.

Todas las escenas tienen un fondo en degradado (más claro arriba, más oscuro
abajo). En exteriores, el cielo tira a violeta/índigo con un resplandor naranja
suave en el horizonte.

Detalles opcionales: "ventana" (con estrellas que parpadean y luna), "lampara"
(con luz ámbar #FFC873), "cartel" (máximo uno) y "siluetas".

Todas las coordenadas son de la zona: en pantalla partida, cada panel mide
1080x960 y el suelo está en y=800; en escena única, la zona es 1080x1920.
"""
from __future__ import annotations

import random

import numpy as np
from PIL import Image

from . import biblioteca as bib
from . import decorado as dec
from .decorado import decor
from .lienzo import AMBIENTE, INDIGO, NARANJA, Lienzo, fondo, mezcla

MESA = 1250  # tablero de la mesa del taller (escena única)
TECHO = 205

# Dibujos "ideales" para los carteles, relativos a la esquina del cartel.
_CARTELES = {
    "silla_ideal": dict(
        trazos=[((70, 70), (70, 200)), ((70, 140), (170, 140)), ((170, 140), (170, 200)), ((70, 170), (170, 170))],
        cotas=[((70, 214), (170, 214)), ((188, 140), (188, 200)), ((50, 70), (50, 200))],
    ),
    "escalera_ideal": dict(
        trazos=[((50, 34), (50, 204)), ((140, 34), (140, 204))] + [((50, y), (140, y)) for y in (74, 114, 154, 194)],
        cotas=[((30, 74), (30, 114)), ((50, 220), (140, 220))],
    ),
}
CARTELES = list(_CARTELES)
ESCENAS = ["habitacion", "taller", "cantera_noche", "calle_mercado"]
EXTERIORES = ("cantera_noche", "calle_mercado")
# Altura del horizonte (para el resplandor) en coordenadas de zona.
_RESPLANDOR = {"cantera_noche": 520, "calle_mercado": 700}
SILUETAS = ["sierra", "ciudad", "bancales", "ninguna"]


def _mover(trazos, x0, y0):
    return [((a[0] + x0, a[1] + y0), (b[0] + x0, b[1] + y0)) for a, b in trazos]


def degradado(img: Image.Image, y0: float, y1: float, horizonte: float, exterior: bool, resplandor=None):
    """Fondo nunca plano: más claro y violeta/índigo arriba, el color del fondo en el horizonte
    y más oscuro abajo. En exteriores, un resplandor naranja suave sobre el horizonte."""
    from .lienzo import ESCALA

    s = ESCALA
    arr = np.asarray(img).astype(np.float32)
    ys = (np.arange(int(y0 * s), int(y1 * s)) / s)[:, None]
    base = np.array(fondo(), np.float32)
    tinte = np.array(INDIGO, np.float32) - base
    arriba = np.clip((horizonte - ys) / max(1.0, horizonte - y0), 0, 1) ** 1.15
    abajo = np.clip((ys - horizonte) / max(1.0, y1 - horizonte), 0, 1)
    fila = base + tinte * arriba * (0.40 if exterior else 0.24)
    fila = fila * (1 - 0.30 * abajo)
    if exterior and resplandor is not None:
        g = np.exp(-(((ys - resplandor) / 120.0) ** 2)) * (ys <= horizonte + 40)
        fila = fila + (np.array(NARANJA, np.float32) - fila) * (0.13 * g)
    arr[int(y0 * s):int(y1 * s)] = fila[:, None, :]
    img.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)))


def construir(img: Image.Image, zonas: list) -> list:
    """Pinta el fondo estático de cada zona.

    `zonas` = [(conf_escena, oy, indice_de_zona, (y0, y1) de la zona en pantalla)].
    Devuelve las estrellas que parpadean (se dibujan en cada fotograma).
    """
    estrellas = []
    for conf, oy, indice, (y0, y1) in zonas:
        tipo = conf["tipo"]
        suelo_local = MESA if tipo == "taller" else dec.SUELO
        res = _RESPLANDOR.get(tipo)
        degradado(img, y0, y1, oy + suelo_local, tipo in EXTERIORES, None if res is None else oy + res)
        lz = Lienzo(img, 0, oy)
        # 1) Luz de las lámparas (primero, para que las líneas queden encima).
        lamp = conf.get("lampara")
        if lamp:
            kw = {}
            if "luz_hasta_y" in lamp:
                kw["y_suelo"] = lamp["luz_hasta_y"]
            if "ancho_luz" in lamp:
                kw["ancho_suelo"] = lamp["ancho_luz"]
                kw["ancho_boca"] = 70
            lz = dec.lampara(img, lz, lamp["x"], lamp["cable"], oy, semilla=lamp.get("semilla", 50),
                             luz=lamp.get("luz", True), techo=lamp.get("techo", 0.0), **kw)
        if tipo == "calle_mercado":
            for j, x in enumerate(conf.get("farolas", [150, 930])):
                lz = dec.farola(img, lz, x, oy, semilla=800 + j * 7)
        # 2) Escena base.
        if tipo == "habitacion":
            dec.suelo(lz, conf.get("semilla", indice))
        elif tipo == "taller":
            _taller(lz)
        elif tipo == "cantera_noche":
            estrellas += bib.cantera_noche(lz, indice, luna=conf.get("luna", indice == 0), semilla=conf.get("semilla", indice))
        elif tipo == "calle_mercado":
            estrellas += calle_mercado(lz, indice, luna=conf.get("luna", indice == 0), semilla=conf.get("semilla", indice),
                                       cielo_desde=y0 - oy, farolas=conf.get("farolas", [150, 930]))
        # 2b) Siluetas de fondo (sierra, ciudad o bancales), muy tenues.
        if conf.get("siluetas", "ninguna") != "ninguna":
            siluetas(lz, conf["siluetas"], conf.get("siluetas_y", 520 if tipo != "taller" else 1000), indice)
        # 3) Ventana con estrellas (y luna, si se pide).
        v = conf.get("ventana")
        if v:
            luna = v.get("luna")
            luna_t = (luna["x"], luna["y"], luna["radio"]) if luna else None
            estrellas += dec.ventana(lz, (v["x"], v["y"], v["x"] + v["ancho"], v["y"] + v["alto"]), panel=indice,
                                     semilla=v.get("semilla", 41), luna=luna_t,
                                     densidad=v.get("estrellas", 1.0))
        # 4) Cartel (máximo uno por zona).
        c = conf.get("cartel")
        if c:
            dib = _CARTELES[c["dibujo"]]
            x0, y0 = c["x"], c["y"]
            dec.cartel(lz, (x0, y0, x0 + c["ancho"], y0 + c["alto"]), _mover(dib["trazos"], x0, y0),
                       _mover(dib["cotas"], x0, y0), semilla=c.get("semilla", 60))
    return estrellas


def _taller(lz: Lienzo):
    """Techo, mesa de taller con balda y suelo (coordenadas de pantalla completa)."""
    linea, suave_c = decor(0.72), decor(0.38)
    lz.boceto((0, TECHO), (1080, TECHO), 2.0, suave_c, semilla=121, doble=False)
    lz.boceto_poli([(46, MESA), (1034, MESA), (1034, MESA + 34), (46, MESA + 34)], 2.6, linea, semilla=140,
                   cerrado=True)
    for j, x in enumerate((84, 970)):
        lz.boceto_poli([(x, MESA + 34), (x + 26, MESA + 34), (x + 26, 1760), (x, 1760)], 2.2, linea,
                       semilla=150 + j, cerrado=True)
    lz.boceto((110, 1612), (970, 1612), 2.2, linea, semilla=160)
    lz.boceto((110, 1630), (970, 1630), 1.6, suave_c, semilla=161, doble=False)
    lz.boceto((110, MESA + 70), (970, MESA + 70), 1.6, suave_c, semilla=162, doble=False)
    lz.boceto((20, 1760), (1060, 1760), 2.4, linea, semilla=170)
    for j, x in enumerate((140, 380, 640, 900)):
        lz.boceto((x, 1782), (x - 30 + j * 20, 1900), 1.4, decor(0.25), semilla=180 + j, doble=False)
    lz.boceto_poli([(240, 1612), (240, 1560), (360, 1560), (360, 1612)], 1.8, suave_c, semilla=190)
    lz.boceto((700, 1600), (820, 1606), 1.6, suave_c, semilla=191, doble=False)


def siluetas(lz: Lienzo, tipo: str, y: float, semilla: int = 0):
    """Siluetas lejanas en línea muy tenue: "sierra", "ciudad" o "bancales"."""
    import random

    rnd = random.Random(700 + semilla)
    color = decor(0.26)
    if tipo == "sierra":
        pts = [(0, y)]
        x = 0
        while x < 1080:
            x += rnd.uniform(90, 160)
            pts.append((min(1080, x), y - rnd.uniform(20, 70)))
        lz.boceto_poli(pts, 1.6, color, semilla=700 + semilla)
    elif tipo == "ciudad":
        ciudad(lz, y, rnd, alfa_linea=0.26)
    elif tipo == "bancales":
        pts, x, yy = [], 0, y - 60
        while x < 1080:
            pts += [(x, yy), (min(1080, x + rnd.uniform(110, 180)), yy)]
            x = pts[-1][0] + 16
            yy += rnd.uniform(18, 34)
        lz.boceto_poli(pts, 1.6, color, semilla=720 + semilla)


def ciudad(lz: Lienzo, base_y: float, rnd: random.Random, alfa_linea: float = 0.4, altura=(60, 220)):
    """Siluetas de edificios con ventanas encendidas en colores de ambiente (ámbar, naranja, rosa, violeta)."""
    colores = list(AMBIENTE.values())
    pesos = [0.55, 0.2, 0.12, 0.13]
    x = -10
    while x < 1090:
        w = rnd.uniform(70, 140)
        h = rnd.uniform(*altura)
        x1 = min(1090, x + w)
        lz.poligono([(x, base_y), (x, base_y - h), (x1, base_y - h), (x1, base_y)], relleno=mezcla(fondo(), (0, 0, 0), 0.25))
        lz.boceto_poli([(x, base_y), (x, base_y - h), (x1, base_y - h), (x1, base_y)], 1.4, decor(alfa_linea),
                       semilla=900 + int(x))
        for fy in range(int(base_y - h + 14), int(base_y - 18), 24):
            for fx in range(int(x + 10), int(x1 - 16), 20):
                if rnd.random() < 0.32:
                    color = rnd.choices(colores, pesos)[0]
                    lz.poligono([(fx, fy), (fx + 9, fy), (fx + 9, fy + 12), (fx, fy + 12)],
                                relleno=mezcla(fondo(), color, rnd.uniform(0.35, 0.65)))
        x = x1 + rnd.uniform(4, 18)


def calle_mercado(lz: Lienzo, panel: int, luna: bool, semilla: int, cielo_desde: float = 0.0, farolas=(150, 930)) -> list:
    """Calle de noche: cielo con estrellas (algunas parpadean), luna, ciudad con ventanas encendidas,
    acera y calzada. Las farolas (con su luz ámbar) se pintan aparte, antes."""
    rnd = random.Random(1000 + semilla * 17 + panel)
    parpadean = []
    alto_cielo = 470 - cielo_desde
    for _ in range(int(40 * alto_cielo / 450)):
        x, y = rnd.uniform(20, 1060), rnd.uniform(cielo_desde + 20, 470)
        if luna and (x - 900) ** 2 + (y - ((cielo_desde + 470) / 2 - 60)) ** 2 < 70 ** 2:
            continue
        r = rnd.choice((1.1, 1.3, 1.6, 1.9, 2.3))
        brillo = rnd.uniform(0.45, 0.95)
        if rnd.random() < 0.35:
            parpadean.append(dec.Estrella(panel, x, y, r, brillo, rnd.choice((1, 2, 3)), rnd.random()))
        else:
            lz.circulo((x, y), r, relleno=decor(brillo * 0.8))
    luna_c = (900, (cielo_desde + 470) / 2 - 60)
    if luna:
        corte = (luna_c[0] + 18, luna_c[1] - 12)
        cielo = bib.color_cielo(lz, corte)  # antes de pintar la luna
        lz.circulo(luna_c, 40, relleno=mezcla(fondo(), (255, 240, 220), 0.85))
        lz.circulo(corte, 37, relleno=cielo)
    # Ciudad al fondo: dos filas de edificios, la de atrás más tenue.
    ciudad(lz, 735, random.Random(1100 + semilla), alfa_linea=0.3, altura=(150, 300))
    ciudad(lz, 770, random.Random(1200 + semilla), alfa_linea=0.45, altura=(70, 170))
    # Acera, bordillo y calzada.
    lz.boceto((0, dec.SUELO), (1080, dec.SUELO), 2.6, decor(0.75), semilla=1300 + semilla)
    lz.boceto((0, dec.SUELO + 22), (1080, dec.SUELO + 22), 1.8, decor(0.5), semilla=1301 + semilla, doble=False)
    for j, x in enumerate(range(40, 1080, 170)):
        lz.linea([(x, dec.SUELO + 96), (x + 80, dec.SUELO + 96)], 3, decor(0.35))
    for j, x in enumerate(range(60, 1080, 120)):
        lz.boceto((x, dec.SUELO), (x - 10, dec.SUELO + 22), 1.2, decor(0.3), semilla=1320 + j, doble=False)
    return parpadean
