"""Elementos de decorado comunes a todos los episodios.

* Suelo en línea de boceto.
* Ventana con estrellitas detrás (algunas parpadean muy suave).
* Lámpara colgante con un cono de luz ámbar cálido, suave y con degradado.
* Cartel en la pared (máximo uno por episodio).

Lo estático se pinta una sola vez en la imagen de fondo; solo las estrellas que
parpadean se dibujan en cada fotograma.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .lienzo import BLANCO, ESCALA, LUZ_LAMPARA, VERDE, Lienzo, fondo, mezcla, rotar, tenue
from .tiempo import rebote, tramo

SUELO = 800


@dataclass(frozen=True)
class Estrella:
    panel: int
    x: float
    y: float
    r: float
    brillo: float
    ciclos: int  # parpadeos completos en todo el vídeo (bucle perfecto)
    fase: float

    def brillo_en(self, fase_bucle: float) -> float:
        """`fase_bucle` va de 0 a 1 a lo largo del bucle; vale lo mismo en 0 y en 1."""
        onda = 0.5 + 0.5 * math.sin(2 * math.pi * (self.ciclos * fase_bucle + self.fase))
        return self.brillo * (0.55 + 0.45 * onda)


def suelo(lz: Lienzo, semilla: int):
    linea, suave_c = tenue(0.72), tenue(0.38)
    lz.boceto((36, SUELO), (1044, SUELO), 2.6, linea, semilla=10 + semilla)
    lz.boceto((36, SUELO - 22), (1044, SUELO - 22), 1.6, suave_c, semilla=20 + semilla, doble=False)
    for j, x in enumerate((120, 300, 520, 760, 960)):
        lz.boceto((x, SUELO + 26), (x - 40 + j * 20, SUELO + 120), 1.4, tenue(0.25), semilla=30 + semilla * 9 + j,
                  doble=False)


def ventana(lz: Lienzo, rect, panel: int, semilla: int, luna=None, densidad: float = 1.0) -> list[Estrella]:
    """Ventana de boceto con estrellas detrás. Devuelve las estrellas que parpadean."""
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rnd = random.Random(semilla)
    parpadean: list[Estrella] = []
    n = int((x1 - x0) * (y1 - y0) / 1700 * densidad)
    for _ in range(n):
        x, y = rnd.uniform(x0 + 10, x1 - 10), rnd.uniform(y0 + 10, y1 - 10)
        if abs(x - cx) < 9 or abs(y - cy) < 9:  # no tapar los travesaños
            continue
        if luna and math.dist((x, y), luna[:2]) < luna[2] + 14:
            continue
        r = rnd.choice((1.1, 1.3, 1.5, 1.8, 2.3))
        brillo = rnd.uniform(0.45, 0.9)
        if rnd.random() < 0.35:
            parpadean.append(Estrella(panel, x, y, r, brillo, rnd.choice((1, 2, 3)), rnd.random()))
        else:
            lz.circulo((x, y), r, relleno=tenue(brillo))
    linea = tenue(0.72)
    lz.boceto_poli([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 2.4, linea, semilla=semilla + 1, cerrado=True)
    lz.boceto((cx, y0), (cx, y1), 1.8, linea, semilla=semilla + 2)
    lz.boceto((x0, cy), (x1, cy), 1.8, linea, semilla=semilla + 3)
    lz.boceto((x0 - 14, y1 + 8), (x1 + 14, y1 + 8), 2.2, linea, semilla=semilla + 4)
    if luna:
        lz.arco(luna[:2], luna[2], 110, 330, 2.0, tenue(0.38))
    return parpadean


def estrellas(lz: Lienzo, lista, panel: int, fase_bucle: float):
    for e in lista:
        if e.panel == panel:
            lz.circulo((e.x, e.y), e.r, relleno=tenue(e.brillo_en(fase_bucle)))


def cono_luz(img: Image.Image, x: float, y_boca: float, oy: float, ancho_boca: float = 70,
             ancho_suelo: float = 460, alfa_max: float = 0.15, y_suelo: float = SUELO):
    """Funde en `img` (a ESCALA) un cono de luz ámbar con degradado hacia abajo.

    La luz llega hasta `y_suelo` (el suelo o, por ejemplo, el tablero de una mesa).
    """
    SUELO = y_suelo  # noqa: N806
    s = ESCALA
    arr = np.asarray(img).astype(np.float32)
    y0, y1 = int((y_boca + oy) * s), int((SUELO + 70 + oy) * s)
    x0 = int((x - ancho_suelo / 2 - 40) * s)
    x1 = int((x + ancho_suelo / 2 + 40) * s)
    x0, x1 = max(0, x0), min(arr.shape[1], x1)
    ys = (np.arange(y0, y1) / s - oy)[:, None]
    xs = (np.arange(x0, x1) / s)[None, :]
    v = np.clip((ys - y_boca) / (SUELO - y_boca), 0, 1.12)
    medio = (ancho_boca + (ancho_suelo - ancho_boca) * np.minimum(v, 1)) / 2
    d = np.abs(xs - x) / medio
    borde = np.clip((1.0 - d) / 0.35, 0, 1)
    borde = borde * borde * (3 - 2 * borde)
    vertical = (1 - np.clip(v, 0, 1)) ** 1.35 * 0.85 + 0.15
    vertical = np.where(v > 1, vertical * np.clip(1 - (v - 1) / 0.12, 0, 1), vertical)
    alfa = alfa_max * borde * vertical
    # Charco de luz en el suelo, muy suave.
    charco = np.clip(1 - ((xs - x) / (ancho_suelo * 0.55)) ** 2 - ((ys - SUELO - 10) / 34) ** 2, 0, 1)
    alfa = np.maximum(alfa, charco * alfa_max * 0.45)
    # Brillo pequeño justo bajo la pantalla de la lámpara.
    foco = np.clip(1 - np.hypot(xs - x, (ys - y_boca - 6) * 1.6) / 46, 0, 1) ** 2
    alfa = np.maximum(alfa, foco * 0.55)
    luz = np.array(LUZ_LAMPARA, np.float32)
    zona = arr[y0:y1, x0:x1]
    arr[y0:y1, x0:x1] = zona * (1 - alfa[..., None]) + luz * alfa[..., None]
    img.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)))


def lampara(img: Image.Image, lz: Lienzo, x: float, cable: float, oy: float, semilla: int, luz: bool = True,
            techo: float = 0.0, **luz_kw):
    """Lámpara colgante del techo. Con `luz`, cono ámbar cálido debajo (opciones en `luz_kw`)."""
    boca = cable + 48
    if luz:
        cono_luz(img, x, boca, oy, **luz_kw)
        lz = Lienzo(img, lz.ox, lz.oy)
    linea = tenue(0.72)
    lz.boceto((x, techo), (x, cable), 1.8, linea, semilla=semilla)
    lz.boceto_poli([(x - 40, boca), (x + 40, boca), (x + 20, cable), (x - 20, cable)], 2.2, linea,
                   semilla=semilla + 1, cerrado=True)
    lz.arco((x, boca), 10, 0, 180, 2.0, linea)
    return lz


def cartel(lz: Lienzo, rect, trazos, cotas, semilla: int):
    """Cartel colgado con un dibujo 'ideal' dentro (trazos) y líneas de cota."""
    linea, suave_c = tenue(0.72), tenue(0.38)
    x0, y0, x1, y1 = rect
    lz.boceto_poli([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], 2.4, linea, semilla=semilla, cerrado=True)
    lz.circulo(((x0 + x1) / 2, y0 + 6), 5, relleno=linea)
    for j, (p0, p1) in enumerate(trazos):
        lz.boceto(p0, p1, 2.0, linea, semilla=semilla + 10 + j, amp=0.6)
    for p0, p1 in cotas:
        lz.linea([p0, p1], 1.2, suave_c)
        for p in (p0, p1):
            lz.linea([(p[0] - 4, p[1] - 4), (p[0] + 4, p[1] + 4)], 1.2, suave_c)


def tabla(lz: Lienzo, centro, largo, grosor, angulo, semilla, color=BLANCO):
    """Tabla de madera (contorno blanco, vetas tenues), girada `angulo` grados sobre su centro."""
    hx, hy = largo / 2, grosor / 2
    pts = [rotar((centro[0] + dx, centro[1] + dy), centro, angulo)
           for dx, dy in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]
    lz.poligono(pts, relleno=fondo(), borde=color, ancho=3)
    rnd = random.Random(semilla)
    for _ in range(2):
        y = rnd.uniform(-hy * 0.4, hy * 0.4)
        x0, x1 = rnd.uniform(-hx * 0.8, -hx * 0.2), rnd.uniform(hx * 0.1, hx * 0.8)
        lz.linea([rotar((centro[0] + x0, centro[1] + y), centro, angulo),
                  rotar((centro[0] + x1, centro[1] + y), centro, angulo)], 1.4, mezcla(color, fondo(), 0.5))


def marca_ok(lz: Lienzo, a: float, c, t0: float):
    """Marca verde de 'conseguido' que aparece en `t0` con un pequeño estallido."""
    if a < t0:
        return
    s = rebote(tramo(a, t0, t0 + 0.3), 2.2)
    pts = [(-34, 0), (-10, 26), (38, -30)]
    lz.linea([(c[0] + x * s, c[1] + y * s) for x, y in pts], 12 * max(s, 0.1), VERDE)
    u = tramo(a, t0, t0 + 0.45)
    if u < 1:
        for k in range(8):
            ang = 2 * math.pi * k / 8
            r0, r1 = 50 + 40 * u, 62 + 52 * u
            lz.linea([(c[0] + math.cos(ang) * r0, c[1] + math.sin(ang) * r0),
                      (c[0] + math.cos(ang) * r1, c[1] + math.sin(ang) * r1)], 4 * (1 - u) + 0.5, VERDE)
