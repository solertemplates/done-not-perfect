"""Dibujo del vídeo largo (1920x1080): personajes con expresiones y las escenas de cada capítulo.

La pantalla se parte en dos mitades de 960x1080: el Hacedor a la izquierda y el
Perfeccionista a la derecha. Cada mitad tiene su suelo en y=SUELO. Todo se
dibuja en coordenadas de la mitad (0..960) con un Lienzo desplazado.

Cada escena recibe `u` (0..1, avance del capítulo) y `t` (segundos del vídeo,
para respirar, parpadear y moverse con suavidad).
"""
from __future__ import annotations

import math
import random

from . import personajes as per
from .lienzo import AMARILLO, AMBAR, BLANCO, ROJO, TINTA, VERDE, Lienzo, fondo, mezcla, tenue
from .tiempo import rebote, suave

ANCHO, ALTO = 1920, 1080
MITAD = 960
SUELO = 880
ESCALA_FIG = 0.78  # los muñecos, un poco más pequeños que en los Shorts
X_FIG = 300  # posición del muñeco dentro de su mitad (el objeto va a la derecha)


def compuesto(u: float, k: float = 3.2) -> float:
    """Progreso con efecto compuesto: lento al principio y rápido al final (0..1)."""
    u = min(1.0, max(0.0, u))
    return (math.exp(k * u) - 1) / (math.exp(k) - 1)


def mitad(img, lado: int) -> Lienzo:
    """Lienzo de una mitad: 0 = izquierda (Hacedor), 1 = derecha (Perfeccionista)."""
    return Lienzo(img, lado * MITAD, 0)


# =============================================================== PERSONAJES
def pose(x: float, t: float, animo: str = "alegre", mira: int = 1, **kw) -> per.Pose:
    """Postura de pie que respira y parpadea. `animo`: alegre, tranquilo, triste, agobiado, sorprendido."""
    resp = math.sin(2 * math.pi * t / 3.4)
    y = SUELO - 186 + resp * 2.5
    parpado = 1.0 if (t + x * 0.01) % 4.3 < 0.12 else 0.0
    sonrisa = {"alegre": 1.0, "tranquilo": 0.8, "triste": -0.9, "agobiado": -1.0, "sorprendido": 2.2,
               "neutro": 0.15}[animo]
    inclinacion = {"triste": 14, "agobiado": 12}.get(animo, 4)
    hombros = {"triste": 9, "agobiado": 7}.get(animo, 0) + resp * 0.8
    mirada = (0.0, 0.7) if animo in ("triste", "agobiado") else (0.2, -0.1)
    p = per.Pose(cadera=(x, y), inclinacion=inclinacion, mira=mira, sonrisa=sonrisa, parpado=parpado,
                 mirada=mirada, hombros=hombros,
                 pie_delante=(x + 26 * mira, SUELO - 2), pie_atras=(x - 20 * mira, SUELO - 2),
                 mano_delante=(x + 40 * mira, y + 92), mano_atras=(x - 36 * mira, y + 96))
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def cabeza_y(p: per.Pose) -> float:
    return p.cadera[1] - per.TORSO - per.CUELLO - per.R_CABEZA


def dibujar_muneco(lz: Lienzo, p: per.Pose, perfeccionista: bool, escala: float = ESCALA_FIG):
    """Dibuja al personaje (siempre blanco) a escala, apoyado en el suelo."""
    per.dibujar(per.a_escala(lz, escala, (p.cadera[0], SUELO)), p, perfeccionista)


def mano_hacia(p: per.Pose, objetivo, u: float, delante: bool = True) -> per.Pose:
    """Lleva una mano hacia `objetivo` (coordenadas a escala real de la mitad) con suavidad."""
    ancla = (p.cadera[0], SUELO)
    obj = (ancla[0] + (objetivo[0] - ancla[0]) / ESCALA_FIG, ancla[1] + (objetivo[1] - ancla[1]) / ESCALA_FIG)
    u = suave(min(1.0, max(0.0, u)))
    if delante:
        m = p.mano_delante
        p.mano_delante = (m[0] + (obj[0] - m[0]) * u, m[1] + (obj[1] - m[1]) * u)
    else:
        m = p.mano_atras
        p.mano_atras = (m[0] + (obj[0] - m[0]) * u, m[1] + (obj[1] - m[1]) * u)
    return p


def a_pantalla(p: per.Pose, punto) -> tuple:
    """Punto del esqueleto (sin escalar) a coordenadas de la mitad."""
    a = (p.cadera[0], SUELO)
    return (a[0] + (punto[0] - a[0]) * ESCALA_FIG, a[1] + (punto[1] - a[1]) * ESCALA_FIG)


def gota_sudor(lz: Lienzo, p: per.Pose, t: float):
    """Gotitas de agobio que caen junto a la cabeza (blancas)."""
    c = a_pantalla(p, (p.cadera[0], cabeza_y(p)))
    for k in range(2):
        f = (t * 0.9 + k * 0.5) % 1.0
        x = c[0] + (70 + 18 * k) * (1 if k else -1)
        y = c[1] - 30 + f * 60
        lz.poligono([(x, y - 14), (x - 7, y + 2), (x + 7, y + 2)], relleno=tenue(0.85))
        lz.circulo((x, y + 3), 7, relleno=tenue(0.85))


def bocadillo(img, lz: Lienzo, centro, cadena: str, tam: float = 30, alfa: float = 1.0):
    """Bocadillo de pensamiento con texto (en coordenadas de la mitad)."""
    from .rotulos import ancho_texto
    from .lienzo import texto

    if alfa <= 0.02:
        return
    w = ancho_texto(cadena, tam) + 50
    h = tam * 1.9
    x0, y0 = centro[0] - w / 2, centro[1] - h / 2
    lz.elipse(centro, w / 2 + 10, h / 2 + 6, relleno=mezcla(fondo(), BLANCO, 0.12 * alfa), borde=tenue(0.8 * alfa),
              ancho=3)
    for k, r in enumerate((10, 6)):
        lz.circulo((x0 + 40 - k * 22, y0 + h + 16 + k * 16), r, borde=tenue(0.8 * alfa), ancho=3)
    texto(img, [(cadena, mezcla(fondo(), BLANCO, alfa))], (centro[0] + lz.ox, centro[1] + lz.oy), tam, 1.0)


def destello(lz: Lienzo, c, u: float, color=VERDE, radio: float = 60):
    """Brillo de logro: rayos que salen y se apagan (u de 0 a 1)."""
    if not 0 <= u < 1:
        return
    s = rebote(min(1.0, u * 1.6), 2.0)
    for k in range(10):
        a = 2 * math.pi * k / 10 + 0.3
        r0, r1 = radio * (0.6 + 0.5 * u), radio * (0.9 + 0.9 * u) * max(0.2, s)
        lz.linea([(c[0] + math.cos(a) * r0, c[1] + math.sin(a) * r0),
                  (c[0] + math.cos(a) * r1, c[1] + math.sin(a) * r1)], 5 * (1 - u) + 1, color)


def marca(lz: Lienzo, c, tam: float, color=VERDE):
    lz.linea([(c[0] - tam * 0.5, c[1]), (c[0] - tam * 0.12, c[1] + tam * 0.38), (c[0] + tam * 0.55, c[1] - tam * 0.45)],
             tam * 0.22, color)


def cruz(lz: Lienzo, c, tam: float, color=ROJO):
    lz.linea([(c[0] - tam / 2, c[1] - tam / 2), (c[0] + tam / 2, c[1] + tam / 2)], tam * 0.2, color)
    lz.linea([(c[0] + tam / 2, c[1] - tam / 2), (c[0] - tam / 2, c[1] + tam / 2)], tam * 0.2, color)


def moneda(lz: Lienzo, c, r: float = 16):
    lz.circulo(c, r, relleno=AMBAR, borde=BLANCO, ancho=2.5)
    lz.linea([(c[0], c[1] - r * 0.5), (c[0], c[1] + r * 0.5)], 3, mezcla(AMBAR, TINTA, 0.5))


# ================================================================== OBJETOS
def hucha(lz: Lienzo, c, tam: float, lleno: float, color_lleno=VERDE, rota: bool = False):
    """Hucha de cerdito (contorno blanco). `lleno` 0..1 sube el nivel de color dentro."""
    rx, ry = 120 * tam, 88 * tam
    x, y = c
    # Patas
    for dx in (-0.55, -0.2, 0.25, 0.6):
        lz.linea([(x + dx * rx, y + ry * 0.75), (x + dx * rx, y + ry * 1.12)], 14 * tam, BLANCO)
    lz.elipse((x, y), rx, ry, relleno=fondo(), borde=BLANCO, ancho=6 * tam)
    if lleno > 0.01:  # nivel de "ahorro" (se dibuja como franjas horizontales dentro del cuerpo)
        nivel = y + ry - 2 * ry * min(1.0, lleno)
        for k in range(int(2 * ry)):
            yy = y + ry - k
            if yy < nivel:
                break
            dy = (yy - y) / ry
            if abs(dy) >= 1:
                continue
            w = rx * math.sqrt(1 - dy * dy) - 6 * tam
            lz.linea([(x - w, yy), (x + w, yy)], 1.6, mezcla(fondo(), color_lleno, 0.75), puntas=False)
        lz.elipse((x, y), rx, ry, borde=BLANCO, ancho=6 * tam)
    # Hocico, oreja, ojo, ranura y cola
    lz.elipse((x + rx * 0.98, y + ry * 0.05), 26 * tam, 32 * tam, relleno=fondo(), borde=BLANCO, ancho=5 * tam)
    for dy in (-8, 8):
        lz.circulo((x + rx * 1.0, y + ry * 0.05 + dy * tam), 4 * tam, relleno=BLANCO)
    lz.poligono([(x + rx * 0.45, y - ry * 0.85), (x + rx * 0.62, y - ry * 1.25), (x + rx * 0.72, y - ry * 0.78)],
                relleno=fondo(), borde=BLANCO, ancho=5 * tam)
    lz.circulo((x + rx * 0.62, y - ry * 0.25), 7 * tam, relleno=TINTA if not rota else BLANCO)
    lz.linea([(x - rx * 0.15, y - ry * 0.98), (x + rx * 0.2, y - ry * 0.98)], 8 * tam, BLANCO)
    lz.arco((x - rx * 1.08, y - ry * 0.1), 16 * tam, 160, 520, 4 * tam, BLANCO, pasos=30)
    if rota:
        lz.linea([(x - rx * 0.2, y - ry * 0.9), (x - rx * 0.05, y - ry * 0.3), (x - rx * 0.25, y + ry * 0.2),
                  (x - rx * 0.05, y + ry * 0.7)], 4, ROJO)


def barra(lz: Lienzo, x0, y, ancho, valor: float, color, alto: float = 26):
    """Barra de progreso (contorno blanco tenue y relleno de color)."""
    lz.poligono([(x0, y), (x0 + ancho, y), (x0 + ancho, y + alto), (x0, y + alto)], borde=tenue(0.7), ancho=3)
    v = min(1.0, max(0.0, valor))
    if v > 0.003:
        lz.poligono([(x0 + 4, y + 4), (x0 + 4 + (ancho - 8) * v, y + 4), (x0 + 4 + (ancho - 8) * v, y + alto - 4),
                     (x0 + 4, y + alto - 4)], relleno=color)


def caja(lz: Lienzo, c, w, h, etiqueta_roja=True, semilla=0):
    """Caja de compra (contorno blanco) con una etiqueta roja pequeña."""
    x, y = c
    lz.boceto_poli([(x - w / 2, y), (x + w / 2, y), (x + w / 2, y - h), (x - w / 2, y - h)], 3, BLANCO,
                   semilla=semilla, cerrado=True, amp=1.0)
    lz.linea([(x - w / 2, y - h * 0.62), (x + w / 2, y - h * 0.62)], 2.2, tenue(0.6))
    if etiqueta_roja:
        lz.poligono([(x + w * 0.1, y - h * 0.4), (x + w * 0.38, y - h * 0.4), (x + w * 0.38, y - h * 0.18),
                     (x + w * 0.1, y - h * 0.18)], relleno=ROJO)


def factura(lz: Lienzo, c, pagada: float, semilla=0):
    """Factura (hoja con líneas); con `pagada` aparece un sello verde."""
    x, y = c
    lz.boceto_poli([(x - 46, y - 60), (x + 46, y - 60), (x + 46, y + 60), (x - 46, y + 60)], 3, BLANCO,
                   semilla=semilla, cerrado=True, amp=0.8)
    for k in range(4):
        lz.linea([(x - 30, y - 34 + k * 20), (x + 30 - (k % 2) * 18, y - 34 + k * 20)], 3, tenue(0.6))
    if pagada > 0:
        marca(lz, (x + 6, y + 22), 60 * rebote(min(1.0, pagada), 2.0), VERDE)


def calendario(lz: Lienzo, x0, y0, celda, hechos: int, fallos: list[int], total: int = 35, nuevo: float = 1.0):
    """Hoja de calendario de 7 columnas: `hechos` marcas verdes y cruces rojas en `fallos`."""
    filas = math.ceil(total / 7)
    w, h = 7 * celda, filas * celda
    lz.poligono([(x0 - 8, y0 - 46), (x0 + w + 8, y0 - 46), (x0 + w + 8, y0 + h + 8), (x0 - 8, y0 + h + 8)],
                relleno=mezcla(fondo(), BLANCO, 0.06), borde=BLANCO, ancho=4)
    lz.linea([(x0 - 8, y0 - 8), (x0 + w + 8, y0 - 8)], 3, tenue(0.7))
    for k in (0.25, 0.75):
        lz.circulo((x0 + w * k, y0 - 46), 9, relleno=BLANCO)
    for i in range(total):
        cx, cy = x0 + (i % 7 + 0.5) * celda, y0 + (i // 7 + 0.5) * celda
        lz.poligono([(cx - celda * 0.42, cy - celda * 0.42), (cx + celda * 0.42, cy - celda * 0.42),
                     (cx + celda * 0.42, cy + celda * 0.42), (cx - celda * 0.42, cy + celda * 0.42)],
                    borde=tenue(0.35), ancho=1.6)
        if i < hechos:
            s = nuevo if i == hechos - 1 else 1.0
            marca(lz, (cx, cy), celda * 0.62 * rebote(min(1.0, s), 2.0), VERDE)
        elif i in fallos:
            cruz(lz, (cx, cy), celda * 0.42, ROJO)


def bolsa_compra(lz: Lienzo, c, tam=1.0):
    x, y = c
    w, h = 60 * tam, 70 * tam
    lz.poligono([(x - w / 2, y), (x + w / 2, y), (x + w * 0.42, y - h), (x - w * 0.42, y - h)], relleno=fondo(),
                borde=BLANCO, ancho=3)
    lz.arco((x, y - h), w * 0.22, 180, 360, 3, BLANCO)
    lz.circulo((x + w * 0.15, y - h * 0.45), 9 * tam, relleno=ROJO)


def puesto_limonada(lz: Lienzo, x, nivel: float, t: float):
    """Puesto que mejora con el tiempo: 0 = caja con jarra, 1 = mesa con toldo, 2 = puesto grande con cartel."""
    from .lienzo import ROSA_NEON

    base_y = SUELO
    if nivel < 1:  # caja de cartón con una jarra
        lz.boceto_poli([(x - 70, base_y), (x + 70, base_y), (x + 70, base_y - 90), (x - 70, base_y - 90)], 3, BLANCO,
                       semilla=11, cerrado=True)
        jarra(lz, (x - 20, base_y - 90), 0.8)
        return
    ancho = 230 if nivel < 2 else 300
    alto_m = 150 if nivel < 2 else 175
    top = base_y - alto_m
    lz.poligono([(x - ancho / 2, base_y), (x + ancho / 2, base_y), (x + ancho / 2, top), (x - ancho / 2, top)],
                relleno=fondo(), borde=BLANCO, ancho=4)
    lz.linea([(x - ancho / 2, top + 26), (x + ancho / 2, top + 26)], 3, tenue(0.6))
    for px in (x - ancho / 2 + 10, x + ancho / 2 - 10):
        lz.linea([(px, top), (px, top - 210)], 6, BLANCO)
    franjas = 6 if nivel < 2 else 8
    color = AMARILLO if nivel < 2 else ROSA_NEON
    w = (ancho + 30) / franjas
    for k in range(franjas):
        x0 = x - ancho / 2 - 15 + k * w
        lz.poligono([(x0, top - 210), (x0 + w, top - 210), (x0 + w, top - 170), (x0, top - 170)],
                    relleno=color if k % 2 == 0 else BLANCO)
        lz.arco((x0 + w / 2, top - 170), w / 2, 0, 180, 3, color if k % 2 == 0 else BLANCO)
    jarra(lz, (x - ancho * 0.25, top), 1.0)
    for k in range(3 if nivel < 2 else 5):
        vaso(lz, (x + 10 + k * 26, top))
    if nivel >= 2:  # cartel
        lz.poligono([(x - 110, top - 300), (x + 110, top - 300), (x + 110, top - 236), (x - 110, top - 236)],
                    relleno=fondo(), borde=AMBAR, ancho=4)


def jarra(lz: Lienzo, base, tam=1.0):
    x, y = base
    w, h = 44 * tam, 70 * tam
    lz.poligono([(x - w / 2, y), (x + w / 2, y), (x + w * 0.45, y - h), (x - w * 0.45, y - h)],
                relleno=mezcla(fondo(), AMARILLO, 0.55), borde=BLANCO, ancho=3)
    lz.arco((x + w * 0.55, y - h * 0.5), 16 * tam, -80, 80, 3, BLANCO)


def vaso(lz: Lienzo, base):
    x, y = base
    lz.poligono([(x - 10, y), (x + 10, y), (x + 12, y - 30), (x - 12, y - 30)],
                relleno=mezcla(fondo(), AMARILLO, 0.6), borde=BLANCO, ancho=2.4)


def cliente(lz: Lienzo, x, t: float, sentido: int = -1, alfa: float = 1.0):
    """Cliente pequeño y sencillo (palitos), que se balancea al andar."""
    c = tenue(0.75 * alfa)
    paso = math.sin(t * 7) * 12
    y = SUELO - 120
    lz.circulo((x, y - 40), 26, relleno=c)
    lz.linea([(x, y - 14), (x, y + 50)], 9, c)
    lz.linea([(x, y + 50), (x - paso, SUELO)], 9, c)
    lz.linea([(x, y + 50), (x + paso, SUELO)], 9, c)
    lz.linea([(x, y + 4), (x + 30 * sentido, y + 34)], 8, c)


def escritorio(lz: Lienzo, x, papeles: int, bolas: int, t: float, semilla=3):
    """Mesa con planos y bolas de papel arrugado que se acumulan."""
    top = SUELO - 170
    lz.boceto((x - 150, top), (x + 150, top), 4, BLANCO, semilla=semilla)
    for dx in (-130, 130):
        lz.linea([(x + dx, top), (x + dx, SUELO)], 6, BLANCO)
    for k in range(min(papeles, 12)):
        dy = k * 5
        lz.poligono([(x - 80 + k * 3, top - 6 - dy), (x + 60 + k * 3, top - 6 - dy), (x + 66 + k * 3, top - 14 - dy),
                     (x - 74 + k * 3, top - 14 - dy)], relleno=fondo(), borde=tenue(0.8), ancho=2)
    rnd = random.Random(semilla)
    for k in range(min(bolas, 40)):
        bx = x - 200 + rnd.uniform(-60, 420)
        by = SUELO - 14 - (k // 9) * 16
        lz.circulo((bx, by), 15, relleno=fondo(), borde=BLANCO, ancho=2.6)
        lz.linea([(bx - 7, by - 3), (bx + 5, by + 4)], 2, tenue(0.6))
