"""Biblioteca de piezas que se pueden usar desde el JSON (bloque "guion").

* Escenas:      "cantera_noche"
* Objetos:      "roca" (se agrieta con cada golpe y se parte al llegar al último)
* Herramientas: "mandarria" (mazo grande, a dos manos)
* Contador:     número grande que sube con cada golpe

Cada pieza es independiente de los episodios: se dibuja a partir de su estado
(por ejemplo, la roca a partir de su progreso de 0 a 1).
"""
from __future__ import annotations

import math
import random

from . import decorado as dec
from .decorado import decor
from .lienzo import (AMARILLO, AZUL, BLANCO, ROJO, VERDE, Lienzo, fondo, mezcla, rotar, tenue, texto)
from .tiempo import limitar

SUELO = dec.SUELO
COLORES = {"verde": VERDE, "rojo": ROJO, "amarillo": AMARILLO, "azul": AZUL, "blanco": BLANCO}


# ================================================================== ESCENAS
def cantera_noche(lz: Lienzo, panel: int, luna: bool, semilla: int = 0) -> list:
    """Cantera al aire libre, de noche: cielo estrellado, bancales de piedra al fondo y suelo de grava.

    Devuelve las estrellas que parpadean (el motor las dibuja en cada fotograma).
    """
    rnd = random.Random(500 + semilla * 17 + panel)
    parpadean = []
    zonas_libres = [(800, 40, 1080, 250)]  # sin estrellas detrás del contador
    if luna:
        zonas_libres.append((540, 130, 700, 290))
    from . import variedad

    for _ in range(int(46 * variedad.actual().estrellas)):
        x, y = rnd.uniform(20, 1060), rnd.uniform(18, 470)
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in zonas_libres):
            continue
        r = rnd.choice((1.1, 1.3, 1.6, 1.9, 2.4))
        brillo = rnd.uniform(0.45, 0.95)
        if rnd.random() < 0.35:
            parpadean.append(dec.Estrella(panel, x, y, r, brillo, rnd.choice((1, 2, 3)), rnd.random()))
        else:
            lz.circulo((x, y), r, relleno=tenue(brillo))
    if luna:
        c, r = (620, 210), 46  # arriba a la izquierda queda sitio para la etiqueta
        cielo = color_cielo(lz, (c[0] + 20, c[1] - 12))  # antes de pintar la luna
        lz.circulo(c, r, relleno=decor(0.88))
        lz.circulo((c[0] + 20, c[1] - 12), r * 0.92, relleno=cielo)  # creciente
    lejos, cerca = decor(0.28), decor(0.5)
    # Sierra lejana.
    sierra = [(0, 470), (120, 430), (210, 455), (330, 405), (470, 450), (590, 420), (720, 460), (860, 410),
              (980, 445), (1080, 425)]
    lz.boceto_poli(sierra, 1.6, lejos, semilla=semilla * 31 + 1)
    # Bancales escalonados de la cantera.
    izq = [(0, 540), (150, 540), (170, 590), (330, 590), (350, 645), (470, 645), (492, 705), (560, 705)]
    der = [(1080, 520), (940, 520), (918, 575), (800, 575), (780, 640), (660, 640), (640, 700), (600, 700)]
    lz.boceto_poli(izq, 2.0, cerca, semilla=semilla * 31 + 2)
    lz.boceto_poli(der, 2.0, cerca, semilla=semilla * 31 + 3)
    for j, (a, b) in enumerate(((( 40, 560), (120, 560)), ((210, 615), (300, 612)), ((850, 600), (900, 596)))):
        lz.boceto(a, b, 1.2, lejos, semilla=semilla * 31 + 10 + j, doble=False)
    # Suelo de grava.
    lz.boceto((20, SUELO), (1060, SUELO), 2.6, decor(0.72), semilla=semilla * 31 + 20)
    for j in range(26):
        x = rnd.uniform(30, 1050)
        y = rnd.uniform(SUELO + 18, SUELO + 140)
        w = rnd.uniform(4, 12)
        lz.poligono([(x - w, y), (x - w * 0.3, y - w * 0.7), (x + w, y - w * 0.2), (x + w * 0.6, y + w * 0.4)],
                    borde=decor(0.4), ancho=1.4)
    for x, w in ((90, 46), (995, 38)):  # piedras sueltas
        lz.poligono([(x - w, SUELO), (x - w * 0.6, SUELO - w * 0.8), (x + w * 0.4, SUELO - w * 0.9),
                     (x + w, SUELO)], relleno=fondo(), borde=decor(0.6), ancho=2.2)
    return parpadean


ESCENAS = {"cantera_noche": cantera_noche}


# ================================================================== ROCA
class Roca:
    """Roca grande. `progreso` (0..1) hace crecer las grietas; al partirse se separa en dos mitades.

    Siempre se genera igual para la misma semilla: así las dos rocas de un episodio son "la misma roca".
    """

    def __init__(self, centro_x: float = 720, ancho: float = 330, alto: float = 250, semilla: int = 7):
        rnd = random.Random(semilla)
        cx, cy = centro_x, SUELO - alto / 2
        rx, ry = ancho / 2, alto / 2

        def punto(grados):
            t = math.radians(grados)
            f = rnd.uniform(0.93, 1.06)
            return (cx + rx * math.cos(t) * f, min(SUELO, cy + ry * math.sin(t) * f))

        t_arriba, t_abajo = -112.0, 96.0
        derecha = [punto(a) for a in range(int(t_arriba) + 16, int(t_abajo), 16)]
        izquierda = [punto(a) for a in range(int(t_arriba) - 16, int(t_abajo) - 360, -16)]
        self.arriba = (cx + rx * math.cos(math.radians(t_arriba)), cy + ry * math.sin(math.radians(t_arriba)))
        self.abajo = (cx + rx * 0.12, SUELO)
        derecha = [self.arriba] + derecha + [(p[0], SUELO) for p in derecha[-1:]] + [self.abajo]
        izquierda = [self.arriba] + izquierda + [(p[0], SUELO) for p in izquierda[-1:]] + [self.abajo]
        # Grieta principal en zigzag, de arriba abajo.
        n = 7
        self.grieta = [self.arriba]
        for i in range(1, n):
            u = i / n
            x = self.arriba[0] + (self.abajo[0] - self.arriba[0]) * u + rnd.uniform(-20, 20)
            y = self.arriba[1] + (self.abajo[1] - self.arriba[1]) * u
            self.grieta.append((x, y))
        self.grieta.append(self.abajo)
        self.contorno = derecha + izquierda[::-1][1:-1]
        self.mitad_izq = izquierda + self.grieta[::-1][1:-1]
        self.mitad_der = derecha + self.grieta[::-1][1:-1]
        self.pivote_izq = (min(p[0] for p in izquierda), SUELO)
        self.pivote_der = (max(p[0] for p in derecha), SUELO)
        # Grietas secundarias: aparecen poco a poco (umbral) y crecen.
        self.ramas = []
        for k in range(7):
            f = rnd.uniform(0.08, 0.85)
            lado = -1 if k % 2 else 1
            umbral = 0.08 + k * 0.12
            ang = math.radians(rnd.uniform(15, 60)) * (-1 if rnd.random() < 0.5 else 1)
            largo = rnd.uniform(34, 80)
            self.ramas.append((f, lado, umbral, ang, largo))
        # Vetas de textura (fijas).
        self.vetas = []
        for _ in range(6):
            x = cx + rnd.uniform(-rx * 0.6, rx * 0.6)
            y = cy + rnd.uniform(-ry * 0.4, ry * 0.5)
            self.vetas.append(((x, y), (x + rnd.uniform(14, 34), y + rnd.uniform(-6, 6))))
        self.punto_golpe = (self.arriba[0] + 4, self.arriba[1] + 2)

    def _en_grieta(self, f):
        """Punto a fracción f (0..1) de la grieta principal."""
        pts = self.grieta
        largos = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
        objetivo = sum(largos) * limitar(f)
        for (a, b), L in zip(zip(pts, pts[1:]), largos):
            if objetivo <= L:
                u = objetivo / L if L else 0
                return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
            objetivo -= L
        return pts[-1]

    def _trozo_grieta(self, f):
        """Grieta principal revelada hasta la fracción f."""
        pts = [self.grieta[0]]
        largos = [math.dist(a, b) for a, b in zip(self.grieta, self.grieta[1:])]
        objetivo = sum(largos) * limitar(f)
        for (a, b), L in zip(zip(self.grieta, self.grieta[1:]), largos):
            if objetivo >= L:
                pts.append(b)
                objetivo -= L
            else:
                u = objetivo / L if L else 0
                pts.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
                break
        return pts

    def dibujar(self, lz: Lienzo, progreso: float, separacion: float = 0.0, brillo=None):
        relleno = mezcla(fondo(), BLANCO, 0.07)
        if separacion <= 0:
            lz.poligono(self.contorno, relleno=relleno)
            lz.linea(self.contorno + [self.contorno[0]], 4, BLANCO, puntas=False)
            for a, b in self.vetas:
                lz.linea([a, b], 1.6, decor(0.35))
            principal = 0.98 * limitar(progreso / 0.92)
            if principal > 0.01:
                lz.linea(self._trozo_grieta(principal), 3.6, BLANCO)
            for f, lado, umbral, ang, largo in self.ramas:
                g = limitar((progreso - umbral) / 0.18)
                if g <= 0 or f > principal:
                    continue
                p0 = self._en_grieta(f)
                d = (lado * math.cos(ang), math.sin(ang))
                p1 = (p0[0] + d[0] * largo * 0.55 * g, p0[1] + d[1] * largo * 0.55 * g)
                p2 = (p1[0] + d[0] * largo * 0.45 * g + lado * 6, p1[1] + d[1] * largo * 0.45 * g + 5)
                lz.linea([p0, p1, p2], 2.4, decor(0.85))
            return
        # Partida en dos: cada mitad gira hacia fuera sobre su base.
        s = limitar(separacion)
        mitades = ((self.mitad_izq, self.pivote_izq, -10 * s, -52 * s), (self.mitad_der, self.pivote_der, 10 * s, 52 * s))
        if brillo is not None:
            # Brillo dentro de la grieta abierta (suave).
            izq = [self._mover(p, self.pivote_izq, -10 * s, -52 * s) for p in self.grieta]
            der = [self._mover(p, self.pivote_der, 10 * s, 52 * s) for p in self.grieta]
            lz.poligono(izq + der[::-1], relleno=mezcla(fondo(), brillo, 0.13))
        for poli, piv, ang, dx in mitades:
            pts = [self._mover(p, piv, ang, dx) for p in poli]
            lz.poligono(pts, relleno=relleno)
            lz.linea(pts + [pts[0]], 4, BLANCO, puntas=False)
            for a, b in self.vetas:
                lado_veta = -1 if a[0] < self._en_grieta(0.5)[0] else 1
                if (lado_veta < 0) == (dx < 0):
                    lz.linea([self._mover(a, piv, ang, dx), self._mover(b, piv, ang, dx)], 1.6, decor(0.35))
            if brillo is not None:
                borde = [self._mover(p, piv, ang, dx) for p in self.grieta]
                lz.linea(borde, 9, mezcla(fondo(), brillo, 0.35))
                lz.linea(borde, 3, brillo)

    @staticmethod
    def _mover(p, pivote, angulo, dx):
        q = rotar(p, pivote, angulo)
        return (q[0] + dx, q[1])


def esquirlas(lz: Lienzo, centro, u: float, semilla: int = 0):
    """Trocitos de piedra que saltan al partirse la roca (u = 0..1)."""
    if not (0 < u < 1):
        return
    rnd = random.Random(semilla)
    for _ in range(9):
        ang = rnd.uniform(-160, -20)
        v = rnd.uniform(120, 260)
        x = centro[0] + math.cos(math.radians(ang)) * v * u
        y = centro[1] + math.sin(math.radians(ang)) * v * u + 320 * u * u
        w = rnd.uniform(4, 9) * (1 - 0.5 * u)
        lz.poligono([(x - w, y), (x, y - w), (x + w, y + w * 0.4)], relleno=tenue(1 - u * 0.7))


# ============================================================ HERRAMIENTAS
LARGO_MANDARRIA = 178  # del agarre al centro de la cabeza


def direccion(angulo: float):
    """Vector unitario: 0° = hacia arriba, 90° = hacia la derecha."""
    a = math.radians(angulo)
    return (math.sin(a), -math.cos(a))


def mandarria(lz: Lienzo, agarre, angulo: float):
    """Mazo grande: mango largo y cabeza rectangular. Devuelve el centro de la cabeza."""
    d = direccion(angulo)
    fin = (agarre[0] - d[0] * 22, agarre[1] - d[1] * 22)
    cabeza = (agarre[0] + d[0] * LARGO_MANDARRIA, agarre[1] + d[1] * LARGO_MANDARRIA)
    lz.linea([fin, cabeza], 10, BLANCO)
    n = (-d[1], d[0])
    w, h = 40, 24
    pts = [(cabeza[0] + n[0] * w * sx + d[0] * h * sy, cabeza[1] + n[1] * w * sx + d[1] * h * sy)
           for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
    lz.poligono(pts, relleno=BLANCO)
    return cabeza


def cara_golpe_mandarria(agarre, angulo: float):
    """Punto de la cabeza de la mandarria que golpea (la cara inferior)."""
    d = direccion(angulo)
    return (agarre[0] + d[0] * (LARGO_MANDARRIA + 24), agarre[1] + d[1] * (LARGO_MANDARRIA + 24))


HERRAMIENTAS = {"mandarria": mandarria}
OBJETOS = {"roca": Roca}


# ================================================================ CONTADOR
def contador(img, valor: int, centro_derecho, tam: float = 118):
    """Número grande alineado a la derecha (en coordenadas de pantalla)."""
    texto(img, [(str(valor), BLANCO)], centro_derecho, tam, 1.0, ancla="rm")


def barrita(lz: Lienzo, centro_derecho, color, ancho: float = 120, alfa: float = 1.0):
    """Barrita de color bajo el contador: el único toque de color del contador."""
    if color is None or alfa <= 0:
        return
    x1, y = centro_derecho[0], centro_derecho[1] + 74
    lz.linea([(x1 - ancho * alfa, y), (x1, y)], 8, color)


def color_cielo(lz: Lienzo, p):
    """Color del fondo (ya pintado) en un punto: para recortar la luna sin dejar un disco plano."""
    x = int((p[0] + lz.ox) * lz.s)
    y = int((p[1] + lz.oy) * lz.s)
    return lz.img.getpixel((max(0, min(lz.img.width - 1, x)), max(0, min(lz.img.height - 1, y))))
