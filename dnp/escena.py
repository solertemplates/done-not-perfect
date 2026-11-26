"""Escenas y detalles de ambiente, todo configurable desde el JSON.

Escenas base (`"tipo"`):
* "habitacion": suelo de tablas en boceto (para la pantalla partida).
* "taller": techo, mesa de taller con balda y suelo (escena única).
* "cantera_noche": cantera al aire libre de noche con cielo estrellado.

Detalles opcionales: "ventana" (con estrellas que parpadean y luna), "lampara"
(con luz ámbar #FFC873), "cartel" (máximo uno) y "siluetas".

Todas las coordenadas son de la zona: en pantalla partida, cada panel mide
1080x960 y el suelo está en y=800; en escena única, la zona es 1080x1920.
"""
from __future__ import annotations

from PIL import Image

from . import biblioteca as bib
from . import decorado as dec
from .lienzo import Lienzo, tenue

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
ESCENAS = ["habitacion", "taller", "cantera_noche"]
SILUETAS = ["sierra", "ciudad", "bancales", "ninguna"]


def _mover(trazos, x0, y0):
    return [((a[0] + x0, a[1] + y0), (b[0] + x0, b[1] + y0)) for a, b in trazos]


def construir(img: Image.Image, zonas: list[tuple[dict, float, int]]) -> list:
    """Pinta el fondo estático de cada zona. `zonas` = [(conf_escena, oy, indice_de_zona)].

    Devuelve las estrellas que parpadean (se dibujan en cada fotograma).
    """
    estrellas = []
    for conf, oy, indice in zonas:
        lz = Lienzo(img, 0, oy)
        tipo = conf["tipo"]
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
        # 2) Escena base.
        if tipo == "habitacion":
            dec.suelo(lz, conf.get("semilla", indice))
        elif tipo == "taller":
            _taller(lz)
        elif tipo == "cantera_noche":
            estrellas += bib.cantera_noche(lz, indice, luna=conf.get("luna", indice == 0), semilla=conf.get("semilla", indice))
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
    linea, suave_c = tenue(0.72), tenue(0.38)
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
        lz.boceto((x, 1782), (x - 30 + j * 20, 1900), 1.4, tenue(0.25), semilla=180 + j, doble=False)
    lz.boceto_poli([(240, 1612), (240, 1560), (360, 1560), (360, 1612)], 1.8, suave_c, semilla=190)
    lz.boceto((700, 1600), (820, 1606), 1.6, suave_c, semilla=191, doble=False)


def siluetas(lz: Lienzo, tipo: str, y: float, semilla: int = 0):
    """Siluetas lejanas en línea muy tenue: "sierra", "ciudad" o "bancales"."""
    import random

    rnd = random.Random(700 + semilla)
    color = tenue(0.26)
    if tipo == "sierra":
        pts = [(0, y)]
        x = 0
        while x < 1080:
            x += rnd.uniform(90, 160)
            pts.append((min(1080, x), y - rnd.uniform(20, 70)))
        lz.boceto_poli(pts, 1.6, color, semilla=700 + semilla)
    elif tipo == "ciudad":
        x = 0
        while x < 1080:
            w = rnd.uniform(60, 120)
            h = rnd.uniform(40, 140)
            lz.boceto_poli([(x, y), (x, y - h), (min(1080, x + w), y - h), (min(1080, x + w), y)], 1.4, color,
                           semilla=710 + int(x))
            x += w + rnd.uniform(4, 20)
    elif tipo == "bancales":
        pts, x, yy = [], 0, y - 60
        while x < 1080:
            pts += [(x, yy), (min(1080, x + rnd.uniform(110, 180)), yy)]
            x = pts[-1][0] + 16
            yy += rnd.uniform(18, 34)
        lz.boceto_poli(pts, 1.6, color, semilla=720 + semilla)
