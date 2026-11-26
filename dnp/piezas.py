"""Objetos de la escena que se declaran en el JSON ("objetos": [...]).

Cada objeto se dibuja a partir del tiempo `ts` (segundos del vídeo) y de lo
que le hacen las acciones de los personajes (construirlo, golpearlo,
arreglarlo...). Las acciones se lo comunican al preparar el episodio.

Tipos: pila_madera, silla, escalera, caja, tabla, plano, roca, contador,
marca_ok (✓ verde) y aro_rojo.
"""
from __future__ import annotations

import math
import random

from . import biblioteca as bib
from . import decorado as dec
from .lienzo import BLANCO, ROJO, VERDE, Lienzo, fondo, mezcla, rotar, tenue
from .personajes import Pose
from .tiempo import entra, lerp, limitar, pulso, rebote, sale, suave, tramo

SUELO = dec.SUELO
MESA = 1250


def rect(r):
    x0, y0, x1, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


class Pieza:
    """Base: un objeto con id, que puede dibujarse detrás o delante de los personajes."""

    def __init__(self, conf: dict):
        self.conf = conf
        self.id = conf.get("id", conf["tipo"])
        self.indice = 0  # zona donde está (0 = arriba o escena única, 1 = abajo)
        self.dx = conf.get("dx", 0)  # desplazamiento horizontal de todo el dibujo

    def dibujar(self, lz: Lienzo, ts: float):
        pass

    def dibujar_delante(self, lz: Lienzo, ts: float):
        pass

    def texto(self, img, ts: float, oy: float):
        pass

    def eventos(self) -> list:
        return []


# ===================================================================== MADERA
class PilaMadera(Pieza):
    """Pila de tablas que cae del cielo al empezar. Las tablas se gastan al construir."""

    def __init__(self, conf):
        super().__init__(conf)
        self.x = conf["x"]
        self.n = conf.get("tablas", 6)
        self.cae = (conf.get("cae_desde_s", 3.0), conf.get("cae_hasta_s", 3.4))
        self.vuelos: list[float] = []  # instantes en que una tabla sale volando hacia la obra

    def origen(self, i: int):
        return (self.x, SUELO - 15 - (self.n - 1 - i) * 26)

    def dibujar(self, lz, ts):
        d, h = self.cae
        caida = 0.0 if ts >= h else 900 * (1 - entra(tramo(ts, d, h)))
        aplasta = pulso(ts, h + 0.07, 0.14) * 6
        quitar = sum(1 for t0 in self.vuelos if ts >= t0)
        for i in range(self.n):
            if i >= self.n - quitar:
                break
            off = (-8 if i % 2 else 6) + (i * 3 % 5)
            c = (self.x + off, SUELO + aplasta - 15 - i * 26 - caida)
            dec.tabla(lz, c, 230, 24, (-1.5 if i % 2 else 1.2), semilla=200 + i)

    def eventos(self):
        if self.conf.get("sonido", True):
            return [(self.cae[1], "golpe_madera", 0.9, 0.0, {})]
        return []


def tabla_volando(lz, pila: PilaMadera, ts, t0, t1, i, destino, largo, grosor, vertical, desfase=0):
    if not (t0 <= ts < t1):
        return
    u = tramo(ts, t0, t1)
    origen = pila.origen(i)
    origen = (origen[0] + pila.dx - desfase, origen[1])
    c = lerp(origen, destino, sale(u))
    c = (c[0], c[1] - math.sin(math.pi * u) * 160)
    ang = lerp(0.0, 90.0 if vertical else 0.0, sale(u)) + math.sin(math.pi * u) * 30
    dec.tabla(lz, c, lerp(230, largo, u), lerp(24, grosor, u), ang, semilla=300 + i)


def chispas(lz, golpe, u):
    for k in range(5):
        ang = math.radians(-20 + k * 45)
        r0, r1 = 18 + 30 * u, 34 + 40 * u
        lz.linea([(golpe[0] + math.cos(ang) * r0, golpe[1] - math.sin(ang) * r0),
                  (golpe[0] + math.cos(ang) * r1, golpe[1] - math.sin(ang) * r1)], 4 * (1 - u) + 1)


class ConstruiblePorPartes(Pieza):
    """Algo que se construye por partes con martillazos (silla, escalera)."""

    def __init__(self, conf):
        super().__init__(conf)
        self.incl0 = float(conf.get("inclinacion_inicial_grados", 7))
        self.incl1 = float(conf.get("inclinacion_final_grados", 2.5))
        self.t_golpe: list[float] = []
        self.vuelo_s = 0.48
        self.pila: PilaMadera | None = None
        self.tambaleo = None  # (desde, hasta)
        self.arreglo: tuple = ()  # instantes de los martillazos del arreglo

    def partes(self) -> list:
        """[(centro, largo, grosor, vertical, punto_de_golpe)] en orden de montaje."""
        raise NotImplementedError

    def punto_arreglo(self, ts: float):
        raise NotImplementedError


# ====================================================================== SILLA
PIVOTE_SILLA = (501, SUELO)
PATA_CORTA = 16
PIEZAS_SILLA = [
    ("poste", (492, 470, 510, SUELO), (510, 640), False),
    ("asiento", (486, 684, 672, 700), (672, 692), False),
    ("pata", (640, 700, 656, SUELO - PATA_CORTA), (656, 742), False),
    ("fondo", None, (662, 712), True),
    ("travesano", (510, 748, 640, 758), (640, 753), False),
    ("respaldo", (484, 474, 518, 600), (518, 530), False),
]


class Silla(ConstruiblePorPartes):
    """Silla de seis piezas. Sale con una pata corta: se tuerce, se tambalea y se calza con una cuña verde."""

    def __init__(self, conf):
        super().__init__(conf)
        self.se_tuerce = conf.get("se_tuerce_s", None)

    def partes(self):
        out = []
        for _, r, golpe, _ in PIEZAS_SILLA:
            if r is None:
                r = (516, 694, 530, SUELO - 14)
            destino = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            largo, grosor = max(r[2] - r[0], r[3] - r[1]), min(r[2] - r[0], r[3] - r[1])
            out.append((destino, largo, grosor, (r[3] - r[1]) > (r[2] - r[0]), golpe))
        return out

    def inclinacion(self, ts: float) -> float:
        i0, i1 = self.incl0, self.incl1
        if self.se_tuerce is None or ts < self.se_tuerce:
            return 0.0
        t = self.tambaleo
        if t is None or ts < t[0]:
            if not self.arreglo or ts < self.arreglo[0]:
                return i0 * rebote(tramo(ts, self.se_tuerce, self.se_tuerce + 0.35), 2.4)
        elif ts < t[1]:
            u = ts - t[0]
            return i0 + 3.2 * math.sin(2 * math.pi * 3.2 * u) * math.exp(-1.9 * u) * (1 - tramo(ts, t[1] - 0.3, t[1]))
        if not self.arreglo:
            return i0
        c0, c1 = self.arreglo[0], self.arreglo[-1]
        if ts < c0:
            return i0
        if ts < c1:
            return lerp(i0, (i0 + i1) / 2, sale(tramo(ts, c0, c0 + 0.08)))
        return lerp((i0 + i1) / 2, i1, sale(tramo(ts, c1, c1 + 0.08)))

    def punto_arreglo(self, ts):
        pie = rotar((648, SUELO - PATA_CORTA), PIVOTE_SILLA, self.inclinacion(ts))
        return (pie[0] + 14, SUELO - 6)

    def sentado(self, incl: float, variante: str = "normal") -> Pose:
        p = Pose(cadera=(548, 672), inclinacion=-6, mira=1, pie_delante=(676, SUELO - 2), pie_atras=(652, SUELO - 2),
                 mano_delante=(640, 646), mano_atras=(520, 682), sonrisa=1.0)
        if variante == "tambalea":
            p.mano_delante, p.mano_atras, p.sonrisa = (700, 520), (430, 548), 2.0
        elif variante == "feliz":
            p.mano_delante, p.sonrisa, p.cabeza = (652, 620), 1.15, 4
        p.cadera = rotar(p.cadera, PIVOTE_SILLA, incl)
        p.mano_atras = rotar(p.mano_atras, PIVOTE_SILLA, incl)
        p.mano_delante = rotar(p.mano_delante, PIVOTE_SILLA, incl)
        p.inclinacion += incl
        return p

    def dibujar(self, lz, ts):
        incl = self.inclinacion(ts)
        self._cuna(lz, ts, incl)

        def R(p):
            return rotar(p, PIVOTE_SILLA, incl)

        n_puestas = sum(1 for t in self.t_golpe if ts >= t - 0.1)
        if n_puestas > 3:
            for r in ((516, 694, 530, SUELO - 14), (664, 694, 678, SUELO - PATA_CORTA - 14)):
                lz.poligono([R(p) for p in rect(r)], relleno=fondo(), borde=tenue(0.6), ancho=3)
        for i, (nombre, r, _, del_fondo) in enumerate(PIEZAS_SILLA):
            if del_fondo or i >= n_puestas:
                continue
            lz.poligono([R(p) for p in rect(r)], relleno=fondo(), borde=BLANCO, ancho=3.4)
            if nombre == "respaldo":
                lz.linea([R((490, 500)), R((512, 500))], 2, tenue(0.6))
                lz.linea([R((490, 570)), R((512, 570))], 2, tenue(0.6))
        if self.pila:
            for i, (c, largo, grosor, vertical, _) in enumerate(self.partes()):
                if i < len(self.t_golpe):
                    tg = self.t_golpe[i]
                    tabla_volando(lz, self.pila, ts, tg - self.vuelo_s, tg - 0.10, i, c, largo, grosor, vertical,
                                  self.dx)
        golpes = list(self.t_golpe) + list(self.arreglo)
        for i, tg in enumerate(golpes):
            if tg <= ts < tg + 0.16:
                golpe = PIEZAS_SILLA[i][2] if i < len(self.t_golpe) else self.punto_arreglo(ts)
                chispas(lz, golpe, tramo(ts, tg, tg + 0.16))

    def _cuna(self, lz, ts, incl):
        if not self.arreglo:
            return
        c0 = self.arreglo[0]
        if ts < c0 - 0.2:
            return
        u = sale(tramo(ts, c0 - 0.2, c0 - 0.05))
        pie = rotar((648, SUELO - PATA_CORTA), PIVOTE_SILLA, incl)
        h = max(14.0, SUELO - pie[1] + 2)
        x = pie[0] + lerp(70, 0, u)
        lz.poligono([(x - 30, SUELO), (x + 40, SUELO), (x + 40, SUELO - h), (x - 30, SUELO - h * 0.4)],
                    relleno=mezcla(fondo(), VERDE, 0.35), borde=VERDE, ancho=3)

    def eventos(self):
        ev = []
        if self.se_tuerce is not None:
            ev.append((self.se_tuerce + 0.12, "crujido", 0.6, -0.25, {}))
        if self.tambaleo:
            ev.append((self.tambaleo[0] + 0.05, "crujido", 0.4, -0.25, {"semilla": 3}))
        return ev


# =================================================================== ESCALERA
BASE_ESCALERA = (470, SUELO)
RIEL_I = ((404, SUELO), (420, 380))
RIEL_D = ((536, SUELO), (524, 380))
PELDANOS_Y = [736, 672, 608, 544, 480]
TORCIDO = 2
INCLINACION_FIJA = [1.2, -1.6, 0.0, 0.9, -1.1]


def x_riel(riel, y):
    (x0, y0), (x1, y1) = riel
    return x0 + (x1 - x0) * (y - y0) / (y1 - y0)


def y_nivel(nivel: float) -> float:
    """Altura de los pies: nivel 0 = suelo, nivel k = peldaño k-1."""
    alturas = [SUELO] + PELDANOS_Y
    k = int(limitar(math.floor(nivel), 0, len(alturas) - 2))
    f = limitar(nivel - k, 0, 1)
    return alturas[k] + (alturas[k + 1] - alturas[k]) * f


class Escalera(ConstruiblePorPartes):
    """Escalera de 2 largueros y 5 peldaños. El del medio sale torcido y se refuerza con una pieza verde."""

    def __init__(self, conf):
        super().__init__(conf)
        self.vuelo_s = 0.45

    def partes(self):
        out = []
        for riel in (RIEL_I, RIEL_D):
            (x0, y0), (x1, y1) = riel
            c = ((x0 + x1) / 2, (y0 + y1) / 2)
            golpe_y = 560 if riel is RIEL_I else 600
            out.append((c, math.dist(riel[0], riel[1]), 16, True, (x_riel(riel, golpe_y) + 9, golpe_y)))
        for y in PELDANOS_Y:
            xi, xd = x_riel(RIEL_I, y), x_riel(RIEL_D, y)
            out.append((((xi + xd) / 2, y), xd - xi + 18, 13, False, (xd + 8, y)))
        return out

    def punto_arreglo(self, ts):
        return (x_riel(RIEL_D, PELDANOS_Y[TORCIDO]) + 8, PELDANOS_Y[TORCIDO] + 4)

    def torcido(self, ts):
        i0, i1 = self.incl0, self.incl1
        if self.tambaleo:
            t0, t1 = self.tambaleo
            if t0 <= ts < t1:
                return i0 + 4.0 * abs(math.sin(2 * math.pi * 3.0 * (ts - t0))) * (1 - tramo(ts, t1 - 0.25, t1))
        if not self.arreglo:
            return i0
        c0, c1 = self.arreglo[0], self.arreglo[-1]
        if ts < c0:
            return i0
        if ts < c1:
            return lerp(i0, (i0 + i1) / 2, sale(tramo(ts, c0, c0 + 0.08)))
        return lerp((i0 + i1) / 2, i1, sale(tramo(ts, c1, c1 + 0.08)))

    def balanceo(self, ts):
        if not self.tambaleo:
            return 0.0
        t0, t1 = self.tambaleo
        if not (t0 <= ts < t1):
            return 0.0
        return 3.2 * math.sin(2 * math.pi * 3.0 * (ts - t0)) * math.exp(-1.6 * (ts - t0)) * (1 - tramo(ts, t1 - 0.2, t1))

    def dibujar(self, lz, ts):
        balanceo = self.balanceo(ts)

        def R(p):
            return rotar(p, BASE_ESCALERA, balanceo)

        puestas = sum(1 for t in self.t_golpe if ts >= t - 0.1)
        piezas = self.partes()
        for i, (c, largo, grosor, vertical, _) in enumerate(piezas):
            if i >= puestas:
                continue
            if vertical:
                riel = RIEL_I if i == 0 else RIEL_D
                ang = math.degrees(math.atan2(riel[1][1] - riel[0][1], riel[1][0] - riel[0][0]))
            else:
                j = i - 2
                ang = self.torcido(ts) if j == TORCIDO else INCLINACION_FIJA[j]
            dec.tabla(lz, R(c), largo, grosor, ang + balanceo, semilla=400 + i)
        self._refuerzo(lz, ts, R)
        if self.pila:
            for i, (c, largo, grosor, vertical, _) in enumerate(piezas):
                if i < len(self.t_golpe):
                    tg = self.t_golpe[i]
                    tabla_volando(lz, self.pila, ts, tg - self.vuelo_s, tg - 0.10, i, c, largo, grosor, vertical,
                                  self.dx)
        for i, tg in enumerate(list(self.t_golpe) + list(self.arreglo)):
            if tg <= ts < tg + 0.16:
                golpe = piezas[i][4] if i < len(self.t_golpe) else self.punto_arreglo(ts)
                chispas(lz, golpe, tramo(ts, tg, tg + 0.16))

    def _refuerzo(self, lz, ts, R):
        if not self.arreglo:
            return
        c0 = self.arreglo[0]
        if ts < c0 - 0.2:
            return
        u = sale(tramo(ts, c0 - 0.2, c0 - 0.05))
        y = PELDANOS_Y[TORCIDO]
        xd = x_riel(RIEL_D, y)
        p0, p1 = (xd - 44, y + 9), (xd - 3, y + 46)
        dx = lerp(80, 0, u)
        pts = [(p0[0] + dx, p0[1]), (p1[0] + dx, p1[1]), (p1[0] + dx - 9, p1[1] + 7), (p0[0] + dx - 9, p0[1] + 7)]
        lz.poligono([R(p) for p in pts], relleno=mezcla(fondo(), VERDE, 0.35), borde=VERDE, ancho=3)

    def eventos(self):
        if not self.tambaleo:
            return []
        t0 = self.tambaleo[0]
        return [(t0, "crujido", 0.75, -0.25, {"semilla": 1}), (t0 + 0.3, "crujido", 0.45, -0.25, {"semilla": 2})]


# ================================================================ PLANO + BOLAS
PLANO = [(470, 814), (722, 814), (752, 904), (448, 904)]
BOLAS = [(262, 792), (212, 794), (238, 752), (168, 795)]
BOCETOS = {
    "silla": [((0.18, 0.2), (0.18, 0.85)), ((0.18, 0.55), (0.62, 0.55)), ((0.62, 0.55), (0.62, 0.85)),
              ((0.18, 0.7), (0.62, 0.7))],
    "escalera": [((0.2, 0.15), (0.24, 0.9)), ((0.56, 0.15), (0.52, 0.9))]
    + [((0.22, v), (0.54, v)) for v in (0.3, 0.45, 0.6, 0.75)],
}


def uv(u, v, plano=PLANO):
    a, b, c, d = plano
    top = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
    bot = (d[0] + (c[0] - d[0]) * u, d[1] + (c[1] - d[1]) * u)
    return (top[0] + (bot[0] - top[0]) * v, top[1] + (bot[1] - top[1]) * v)


def bola(lz, c, r=22, semilla=0):
    lz.circulo(c, r, relleno=fondo(), borde=BLANCO, ancho=3.5)
    rnd = random.Random(semilla)
    pts = [(c[0] + rnd.uniform(-0.6, 0.6) * r, c[1] + rnd.uniform(-0.6, 0.6) * r) for _ in range(5)]
    lz.linea(pts, 1.8, tenue(0.7), puntas=False)


class Plano(Pieza):
    """Hoja de planos en el suelo. La dibuja, mide, borra y arruga quien la usa (bolas de papel incluidas)."""

    def __init__(self, conf):
        super().__init__(conf)
        self.boceto = BOCETOS[conf.get("boceto", "silla")]
        self.usuario = None  # el personaje que la usa (pone las fases)
        self.dibujos = []
        self.borrones_final = [(0.24, 0.32), (0.5, 0.42), (0.36, 0.7), (0.62, 0.74), (0.8, 0.5), (0.2, 0.6)]

    def preparar(self, hojas_arrugadas: int):
        rnd = random.Random(7)
        self.dibujos = []
        for k in range(hojas_arrugadas + 1):
            segs = [((a[0] + rnd.uniform(-0.04, 0.04), a[1] + rnd.uniform(-0.05, 0.05)),
                     (b[0] + rnd.uniform(-0.04, 0.04), b[1] + rnd.uniform(-0.05, 0.05))) for a, b in self.boceto]
            segs += [((0.72, 0.2 + 0.1 * j), (0.9, 0.2 + 0.1 * j)) for j in range(3)]
            borrones = [(rnd.uniform(0.18, 0.65), rnd.uniform(0.3, 0.8)) for _ in range(2 + k)]
            self.dibujos.append((segs, borrones))
        self.n_arrugadas = hojas_arrugadas

    def dibujar(self, lz, ts):
        if self.usuario is None:
            return
        for k, (t0, t1) in enumerate(self.usuario.lanzamientos()):
            if ts < t0:
                break
            destino = BOLAS[k % len(BOLAS)]
            if ts < t1:
                u = tramo(ts, t0, t1)
                pos = lerp((560, 740), destino, u)
                pos = (pos[0], pos[1] - math.sin(math.pi * u) * 260)
                bola(lz, pos, semilla=500 + k)
            else:
                rebota = pulso(ts, t1 + 0.06, 0.12) * 12
                bola(lz, (destino[0], destino[1] - rebota), semilla=500 + k)
        self._hoja(lz, *self.usuario.fase_plano(ts))

    def _hoja(self, lz, fase, u, k):
        final = k >= self.n_arrugadas
        segs, borr = self.dibujos[k]
        if fase == "espera":
            return
        aparece = 1.0
        if fase == "dibuja":
            aparece = rebote(tramo(u, 0, 0.12 if not final else 0.2))
        if fase in ("tira", "pausa"):
            return
        centro = uv(0.5, 0.5)
        plano = PLANO
        if fase == "arruga":
            q = suave(u)
            destino = lerp(centro, (560, 740), q)
            plano = [(destino[0] + (c[0] - centro[0]) * (1 - q * 0.92), destino[1] + (c[1] - centro[1]) * (1 - q * 0.92))
                     for c in PLANO]
            if q > 0.55:
                bola(lz, destino, 22 * (0.6 + 0.4 * tramo(q, 0.55, 1)), semilla=500 + k)
                return
        elif aparece < 1:
            plano = [(centro[0] + (c[0] - centro[0]) * aparece, centro[1] + (c[1] - centro[1]) * aparece) for c in PLANO]
        lz.poligono(plano, relleno=mezcla(fondo(), BLANCO, 0.06), borde=BLANCO, ancho=3)
        n = len(segs)
        hechas = u * n if fase == "dibuja" else n
        for j, (s0, s1) in enumerate(segs):
            if j >= hechas:
                break
            f = min(1.0, hechas - j)
            lz.linea([uv(*s0, plano), uv(*lerp(s0, s1, f), plano)], 2.2, tenue(0.85), puntas=False)
        if fase == "mide" and not final:
            regla = [uv(0.08, 0.62, plano), uv(0.92, 0.62, plano)]
            lz.linea(regla, 9, tenue(0.9))
            for j in range(9):
                x = 0.1 + j * 0.1
                lz.linea([uv(x, 0.6, plano), uv(x, 0.66, plano)], 1.6, fondo())
        if fase in ("borra", "arruga", "suspira", "fin"):
            lista = self.borrones_final if final else borr
            progreso = u if fase == "borra" else 1.0
            for j, (bu, bv) in enumerate(lista):
                g = limitar((progreso - j / len(lista)) * len(lista))
                if g <= 0:
                    continue
                c = uv(bu, bv, plano)
                rnd = random.Random(900 + k * 31 + j)
                lz.elipse(c, 26 * g, 12 * g, relleno=mezcla(fondo(), BLANCO, 0.3))
                pts = [(c[0] + rnd.uniform(-24, 24) * g, c[1] + rnd.uniform(-10, 10) * g) for _ in range(7)]
                lz.linea(pts, 1.6, tenue(0.55), puntas=False)
            for j in range(2 if final else 1):
                if progreso < 0.55 + j * 0.2:
                    continue
                bu, bv = lista[j * 2 % len(lista)]
                c = uv(bu + 0.06, bv - 0.05, plano)
                r = 13 * rebote(tramo(progreso, 0.55 + j * 0.2, 0.7 + j * 0.2))
                lz.linea([(c[0] - r, c[1] - r * 0.6), (c[0] + r, c[1] + r * 0.6)], 5, ROJO)
                lz.linea([(c[0] + r, c[1] - r * 0.6), (c[0] - r, c[1] + r * 0.6)], 5, ROJO)


# ======================================================================= CAJA
TABLA_CAJA = (130, MESA - 28, 410, MESA)
PIEZAS_CAJA = [
    ((118, 1112, 138, MESA), (128, 1112)),
    ((402, 1112, 422, MESA), (412, 1112)),
    ((130, 1190, 410, 1218), (392, 1190)),
    ((130, 1158, 410, 1186), (392, 1158)),
    ((130, 1126, 410, 1154), (392, 1126)),
]
CLAVOS_CAJA = [170, 215, 260, 305, 350]
DOBLEZ = 55.0


def clavo(lz, base, alto, doblez=0.0, color=BLANCO):
    if alto <= 0.5:
        lz.linea([(base[0] - 9, base[1]), (base[0] + 9, base[1])], 5, color)
        return
    mitad = (base[0], base[1] - alto / 2)
    arriba = rotar((mitad[0], mitad[1] - alto / 2), mitad, -doblez)
    lz.linea([base, mitad, arriba], 4.5, color)
    d = (arriba[0] - mitad[0], arriba[1] - mitad[1])
    L = math.hypot(*d) or 1
    n = (-d[1] / L * 9, d[0] / L * 9)
    lz.linea([(arriba[0] + n[0], arriba[1] + n[1]), (arriba[0] - n[0], arriba[1] - n[1])], 5, color)


def punta_clavo(base, alto, doblez):
    mitad = (base[0], base[1] - alto / 2)
    return rotar((mitad[0], mitad[1] - alto / 2), mitad, -doblez)


def clavo_tumbado(lz, x, y):
    lz.linea([(x - 17, y), (x + 15, y)], 4, BLANCO)
    lz.linea([(x - 17, y - 6), (x - 17, y + 6)], 4, BLANCO)


class Caja(Pieza):
    """Caja de madera sobre la mesa: tabla base con clavos tumbados y cinco piezas que se clavan."""

    def __init__(self, conf):
        super().__init__(conf)
        self.incl_tapa = float(conf.get("inclinacion_tapa_grados", 2.5))
        self.t_pieza: list[float] = []
        self.tocs: list[list[float]] = []
        self.alturas: list[list[float]] = []
        self.torcido = None  # (pieza, t_tuerce, t_endereza)

    def altura_clavo(self, i, ts):
        alto = 40.0
        for tau, h in zip(self.tocs[i], self.alturas[i]):
            if ts >= tau:
                alto = h
        doblez = 0.0
        if self.torcido and i == self.torcido[0]:
            _, tt, te = self.torcido
            doblez = DOBLEZ * sale(tramo(ts, tt, tt + 0.06)) * (1 - tramo(ts, te, te + 0.05))
        return alto, doblez

    def dibujar(self, lz, ts):
        base = ((TABLA_CAJA[0] + TABLA_CAJA[2]) / 2, (TABLA_CAJA[1] + TABLA_CAJA[3]) / 2)
        dec.tabla(lz, base, TABLA_CAJA[2] - TABLA_CAJA[0], 28, 0, semilla=600)
        n = len(self.t_pieza)
        for i, x in enumerate(CLAVOS_CAJA):
            if i >= n or ts < self.t_pieza[i]:
                clavo_tumbado(lz, x, MESA - 34)
        for i in [2, 3, 4, 0, 1]:
            if i >= n or ts < self.t_pieza[i]:
                continue
            (x0, y0, x1, y1), _ = PIEZAS_CAJA[i]
            caida = -50 * (1 - rebote(tramo(ts, self.t_pieza[i], self.t_pieza[i] + 0.18)))
            c = ((x0 + x1) / 2, (y0 + y1) / 2 + caida)
            vertical = (y1 - y0) > (x1 - x0)
            largo, grosor = (y1 - y0, x1 - x0) if vertical else (x1 - x0, y1 - y0)
            ang = 90.0 if vertical else (self.incl_tapa if i == 4 else 0.0)
            dec.tabla(lz, c, largo, grosor, ang, semilla=610 + i)
        for i, (_, cl) in enumerate(PIEZAS_CAJA):
            if i >= n or ts < self.t_pieza[i]:
                continue
            alto, doblez = self.altura_clavo(i, ts)
            caida = -50 * (1 - rebote(tramo(ts, self.t_pieza[i], self.t_pieza[i] + 0.18)))
            base = (cl[0], cl[1] + caida + (math.tan(math.radians(self.incl_tapa)) * (cl[0] - 270) if i == 4 else 0))
            clavo(lz, base, alto, doblez)
        for i in range(n):
            golpes = self.tocs[i] + ([self.torcido[2]] if self.torcido and i == self.torcido[0] else [])
            for tau in golpes:
                if tau <= ts < tau + 0.12:
                    u = tramo(ts, tau, tau + 0.12)
                    c = PIEZAS_CAJA[i][1]
                    for k in range(4):
                        ang = math.radians(20 + k * 47)
                        r0, r1 = 14 + 22 * u, 26 + 30 * u
                        lz.linea([(c[0] + math.cos(ang) * r0, c[1] - math.sin(ang) * r0),
                                  (c[0] + math.cos(ang) * r1, c[1] - math.sin(ang) * r1)], 3.5 * (1 - u) + 1)


# ====================================================================== TABLA
class Tabla(Pieza):
    """Tabla sobre la mesa con clavos tumbados y un sitio para un clavo (lo manejan los personajes)."""

    def __init__(self, conf):
        super().__init__(conf)
        self.x, self.ancho = conf.get("x", 600), conf.get("ancho", 280)
        self.y = conf.get("y", MESA)
        self.clavos = conf.get("clavos_tumbados", [])
        self.clavo_x = conf.get("clavo_x", self.x + self.ancho / 2)
        self.usuario = None

    @property
    def punto_clavo(self):
        return (self.clavo_x, self.y - 28)

    def dibujar(self, lz, ts):
        c = (self.x + self.ancho / 2, self.y - 14)
        dec.tabla(lz, c, self.ancho, 28, 0, semilla=600)
        estado = self.usuario.clavo_en(ts) if self.usuario else ("tumbado", None)
        for j, x in enumerate(self.clavos):
            if j == 1 and estado[0] != "tumbado":
                continue
            clavo_tumbado(lz, x, self.y - 34)
        if estado[0] == "tabla":
            clavo(lz, self.punto_clavo, estado[1])


# ======================================================================= ROCA
class Roca(Pieza):
    """Roca grande: se agrieta con cada golpe y se parte en dos al llegar a `golpes_para_partir`."""

    def __init__(self, conf):
        super().__init__(conf)
        self.roca = bib.Roca()
        self.golpes_partir = conf.get("golpes_para_partir", 100)
        self.brillo = bib.COLORES[conf["brillo"]] if conf.get("brillo") else None
        self.golpes: list[float] = []
        self.paneo = 0.0

    @property
    def t_partida(self):
        return self.golpes[self.golpes_partir - 1] if len(self.golpes) >= self.golpes_partir else None

    def golpes_hasta(self, ts):
        import bisect

        return bisect.bisect_right(self.golpes, ts + 1e-9)

    def separacion(self, ts):
        tp = self.t_partida
        if tp is None or ts < tp:
            return 0.0
        return sale(tramo(ts, tp, tp + 0.35))

    def dibujar(self, lz, ts):
        prog = limitar(self.golpes_hasta(ts) / self.golpes_partir)
        self.roca.dibujar(lz, prog, self.separacion(ts), self.brillo)
        if self.t_partida is not None:
            bib.esquirlas(lz, self.roca.punto_golpe, tramo(ts, self.t_partida, self.t_partida + 0.6), semilla=self.indice)

    def dibujar_delante(self, lz, ts):
        tp = self.t_partida
        if tp is not None and self.brillo is not None:
            u = tramo(ts, tp, tp + 0.4)
            if 0 < u < 1:
                cx, cy = self.roca.punto_golpe
                for k in range(10):
                    ang = 2 * math.pi * k / 10
                    r0, r1 = 30 + 80 * u, 50 + 110 * u
                    lz.linea([(cx + math.cos(ang) * r0, cy + math.sin(ang) * r0),
                              (cx + math.cos(ang) * r1, cy + math.sin(ang) * r1)], 5 * (1 - u) + 0.5, self.brillo)

    def eventos(self):
        pan = self.paneo
        ev = []
        ultimo = -1.0
        for i, t in enumerate(self.golpes):
            if i + 1 == self.golpes_partir:
                ev += [(t, "mandarria", 0.9, pan, {"semilla": i}), (t + 0.02, "crac", 0.95, pan, {}),
                       (t + 0.18, "ding", 0.9, pan, {})]
                ultimo = t
                continue
            if t - ultimo >= 0.06:
                ev.append((t, "mandarria", 0.55, pan, {"semilla": i % 7}))
                ultimo = t
            if (i + 1) % 20 == 0 and i + 1 < self.golpes_partir:
                ev.append((t + 0.03, "grieta", 0.6, pan, {"semilla": i}))
        return ev


# ================================================================ MARCAS
class MarcaOk(Pieza):
    """✓ verde de 'conseguido', con "ding"."""

    def dibujar_delante(self, lz, ts):
        dec.marca_ok(lz, ts, (self.conf["x"], self.conf["y"]), self.conf["aparece_s"])

    def eventos(self):
        if not self.conf.get("sonido", True):
            return []
        return [(self.conf["aparece_s"], "ding", 0.9, self.conf.get("paneo", -0.15), {})]


class AroRojo(Pieza):
    """Círculo rojo discontinuo que señala lo que quedó a medias."""

    def dibujar(self, lz, ts):
        t0 = self.conf["aparece_s"]
        if ts < t0:
            return
        s = rebote(tramo(ts, t0, t0 + 0.3), 2.0)
        centro = (self.conf["x"], self.conf["y"])
        r = self.conf.get("radio", 30) * s
        for j in range(10):
            a0 = 2 * math.pi * j / 10
            a1 = a0 + 2 * math.pi / 20
            lz.linea([(centro[0] + r * math.cos(a0), centro[1] + r * math.sin(a0)),
                      (centro[0] + r * math.cos(a1), centro[1] + r * math.sin(a1))], 3, ROJO)


class Contador(Pieza):
    """Número grande que cuenta los golpes de un personaje, con barrita de color al terminar."""

    def __init__(self, conf):
        super().__init__(conf)
        self.x, self.y = conf.get("x", 1030), conf.get("y", 150)
        self.color = bib.COLORES.get(conf.get("color_final")) if conf.get("color_final") else None
        self.de = None  # personaje cuyos golpes cuenta

    def dibujar_delante(self, lz, ts):
        if self.color is None or self.de is None:
            return
        ultima = self.de.acciones[-1]
        if ultima["accion"] == "golpear" or ts < ultima["desde_s"]:
            return
        bib.barrita(lz, (self.x, self.y), self.color, alfa=sale(tramo(ts, ultima["desde_s"], ultima["desde_s"] + 0.3)))

    def texto(self, img, ts, oy):
        if self.de is not None:
            bib.contador(img, self.de.golpes_hasta(ts), (self.x + self.dx, self.y + oy))


TIPOS = {
    "pila_madera": PilaMadera, "silla": Silla, "escalera": Escalera, "caja": Caja, "tabla": Tabla, "plano": Plano,
    "roca": Roca, "contador": Contador, "marca_ok": MarcaOk, "aro_rojo": AroRojo,
}
