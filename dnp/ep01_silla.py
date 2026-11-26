"""Episodio 1: "La silla".

Pantalla partida durante todo el episodio: arriba el Hacedor, abajo el
Perfeccionista. Cada panel es una función pura del "tiempo de acción" `a`
(0..11 unidades), de modo que:

* el gancho (0-1 s) y el final muestran exactamente el estado a = 11,
* el rebobinado (1-3 s) recorre `a` hacia atrás de 11 a 0,
* la acción (3-14 s) recorre `a` hacia delante de 0 a 11.

Como el último fotograma vuelve a ser idéntico al primero, el bucle no se nota.
"""
from __future__ import annotations

import math
import random

import numpy as np
from PIL import Image

from . import personajes as pj
from .config import Episodio
from .lienzo import (BLANCO, ESCALA, FONDO, ROJO, VERDE, Lienzo, capa, fuente, mezcla, rotar, tenue, texto)
from .personajes import Pose
from .tiempo import entra, lerp, limitar, oscila, pista, pulso, rebote, sale, suave, tramo

A_FIN = 11.0  # duración de la acción en unidades internas
ALTO_PANEL = 960
SUELO = 800

# --- Silla (coordenadas del panel superior, sin inclinar) ---------------------
PIVOTE = (501, SUELO)  # pie de la pata trasera: la silla gira sobre él
PATA_CORTA = 16  # la pata delantera queda corta: por eso la silla sale torcida

# (nombre, rectángulo x0,y0,x1,y1, punto de martillazo, es_del_fondo)
PIEZAS = [
    ("poste", (492, 470, 510, SUELO), (510, 640), False),
    ("asiento", (486, 684, 672, 700), (672, 692), False),
    ("pata", (640, 700, 656, SUELO - PATA_CORTA), (656, 742), False),
    ("fondo", None, (662, 712), True),
    ("travesano", (510, 748, 640, 758), (640, 753), False),
    ("respaldo", (484, 474, 518, 600), (518, 530), False),
]

PILA_H = (210, SUELO)  # pila de madera del Hacedor (lado izquierdo)
PILA_P = (880, SUELO)  # pila del Perfeccionista (lado derecho, intacta)
N_TABLAS = 6

# --- Plano del Perfeccionista (trapecio sobre el suelo, en primer plano) ------
PLANO = [(470, 814), (722, 814), (752, 904), (448, 904)]  # sup-izq, sup-der, inf-der, inf-izq
BOLAS = [(262, 792), (212, 794), (238, 752), (168, 795)]


def _rect(r):
    x0, y0, x1, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _uv(u, v, plano=PLANO):
    a, b, c, d = plano
    top = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
    bot = (d[0] + (c[0] - d[0]) * u, d[1] + (c[1] - d[1]) * u)
    return (top[0] + (bot[0] - top[0]) * v, top[1] + (bot[1] - top[1]) * v)


class EpisodioSilla:
    def __init__(self, ep: Episodio):
        self.ep = ep
        t = ep["tiempos"]
        self.g = float(t["gancho_fin_s"])
        self.r = float(t["rebobinado_fin_s"])
        self.A = float(t["accion_fin_s"])
        self.D = ep.duracion
        self.k = (self.A - self.r) / A_FIN  # segundos reales por unidad de acción
        self.ancho, self.alto = ep.tamano
        self.textos = ep["textos"]
        self.intentos = ep["perfeccionista"]["intentos"]
        h = ep["hacedor"]
        self.incl0 = float(h["inclinacion_inicial_grados"])
        self.incl1 = float(h["inclinacion_final_grados"])
        self._preparar_hacedor()
        self._preparar_perfeccionista()
        self._fondo = self._decorado()

    # ------------------------------------------------------------------ tiempo
    def accion(self, t: float) -> float:
        if t < self.g:
            return A_FIN
        if t < self.r:
            u = tramo(t, self.g, self.r)
            return A_FIN * (1 - (0.5 * u + 0.5 * suave(u)))
        if t < self.A:
            return (t - self.r) / self.k
        return A_FIN

    def real(self, a: float) -> float:
        """Convierte un instante de la acción a segundos del vídeo (para el audio)."""
        return self.r + a * self.k

    # --------------------------------------------------------------- decorado
    def _decorado(self) -> Image.Image:
        s = ESCALA
        img = Image.new("RGB", (self.ancho * s, self.alto * s), FONDO)
        arriba = Lienzo(img, 0, 0)
        abajo = Lienzo(img, 0, ALTO_PANEL)
        linea = tenue(0.72)
        suave_c = tenue(0.38)
        for i, lz in enumerate((arriba, abajo)):
            lz.boceto((36, SUELO), (1044, SUELO), 2.6, linea, semilla=10 + i)
            lz.boceto((36, SUELO - 22), (1044, SUELO - 22), 1.6, suave_c, semilla=20 + i, doble=False)
            for j, x in enumerate((120, 300, 520, 760, 960)):
                lz.boceto((x, SUELO + 26), (x - 40 + j * 20, SUELO + 120), 1.4, tenue(0.25), semilla=30 + i * 9 + j,
                          doble=False)
        # Arriba: ventana.
        v = (86, 236, 316, 470)
        arriba.boceto_poli(_rect(v), 2.4, linea, semilla=41, cerrado=True)
        arriba.boceto(((v[0] + v[2]) / 2, v[1]), ((v[0] + v[2]) / 2, v[3]), 1.8, linea, semilla=42)
        arriba.boceto((v[0], (v[1] + v[3]) / 2), (v[2], (v[1] + v[3]) / 2), 1.8, linea, semilla=43)
        arriba.boceto((v[0] - 14, v[3] + 8), (v[2] + 14, v[3] + 8), 2.2, linea, semilla=44)
        arriba.arco((250, 300), 26, 110, 330, 2.0, suave_c)  # luna
        # Abajo: lámpara colgante y el único cartel de la serie (la silla "perfecta").
        abajo.boceto((190, 0), (190, 120), 1.8, linea, semilla=50)
        abajo.boceto_poli([(150, 168), (230, 168), (210, 120), (170, 120)], 2.2, linea, semilla=51, cerrado=True)
        abajo.arco((190, 168), 10, 0, 180, 2.0, linea)
        c = (630, 210, 880, 440)
        abajo.boceto_poli(_rect(c), 2.4, linea, semilla=60, cerrado=True)
        abajo.circulo((755, 216), 5, relleno=linea)
        # Plano ideal dentro del cartel: silla recta con cotas.
        k0 = (690, 410)
        silla_ideal = [((700, 280), (700, 410)), ((700, 350), (800, 350)), ((800, 350), (800, 410)),
                       ((700, 380), (800, 380))]
        for j, (p0, p1) in enumerate(silla_ideal):
            abajo.boceto(p0, p1, 2.0, linea, semilla=70 + j, amp=0.6)
        for j, (p0, p1) in enumerate((((700, 424), (800, 424)), ((818, 350), (818, 410)), ((680, 280), (680, 410)))):
            abajo.linea([p0, p1], 1.2, suave_c)
            abajo.linea([(p0[0] - 4, p0[1] - 4), (p0[0] + 4, p0[1] + 4)], 1.2, suave_c)
            abajo.linea([(p1[0] - 4, p1[1] - 4), (p1[0] + 4, p1[1] + 4)], 1.2, suave_c)
        abajo.circulo(k0, 1, relleno=suave_c)
        # Pila intacta del Perfeccionista (no se toca en todo el episodio).
        return img

    # ------------------------------------------------------------- utilidades
    @staticmethod
    def _tabla(lz: Lienzo, centro, largo, grosor, angulo, semilla, color=BLANCO):
        hx, hy = largo / 2, grosor / 2
        pts = [rotar((centro[0] + dx, centro[1] + dy), centro, angulo)
               for dx, dy in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy))]
        lz.poligono(pts, relleno=FONDO, borde=color, ancho=3)
        rnd = random.Random(semilla)
        for _ in range(2):
            y = rnd.uniform(-hy * 0.4, hy * 0.4)
            x0, x1 = rnd.uniform(-hx * 0.8, -hx * 0.2), rnd.uniform(hx * 0.1, hx * 0.8)
            lz.linea([rotar((centro[0] + x0, centro[1] + y), centro, angulo),
                      rotar((centro[0] + x1, centro[1] + y), centro, angulo)], 1.4, mezcla(color, FONDO, 0.5))

    def _pila(self, lz: Lienzo, base, n, caida: float, quitar: int = 0):
        """Pila de tablas. `caida` 0 = en el suelo; >0 = desplazada hacia arriba."""
        for i in range(n):
            if i >= n - quitar:
                break
            off = (-8 if i % 2 else 6) + (i * 3 % 5)
            c = (base[0] + off, base[1] - 15 - i * 26 - caida)
            self._tabla(lz, c, 230, 24, (-1.5 if i % 2 else 1.2), semilla=200 + i)

    @staticmethod
    def _bola(lz: Lienzo, c, r=22, semilla=0):
        lz.circulo(c, r, relleno=FONDO, borde=BLANCO, ancho=3.5)
        rnd = random.Random(semilla)
        pts = [(c[0] + rnd.uniform(-0.6, 0.6) * r, c[1] + rnd.uniform(-0.6, 0.6) * r) for _ in range(5)]
        lz.linea(pts, 1.8, tenue(0.7), puntas=False)

    # ================================================================ HACEDOR
    def _preparar_hacedor(self):
        self.t_golpe = [1.30 + 0.72 * i for i in range(len(PIEZAS))]
        self.t_vuelo = [(t - 0.48, t - 0.10) for t in self.t_golpe]
        self.t_cuña = (8.15, 8.50)

    def _de_pie(self, x, mira=-1, agachado=0.0, **kw) -> Pose:
        y = SUELO - 186 + agachado
        return Pose(
            cadera=(x, y), inclinacion=8 + agachado * 0.35, mira=mira,
            pie_delante=(x + 24 * mira, SUELO - 2), pie_atras=(x - 18 * mira, SUELO - 2),
            mano_delante=(x + 38 * mira, y + 92), mano_atras=(x - 34 * mira, y + 96), **kw,
        )

    def _sentado(self, incl: float, variante: str = "normal") -> Pose:
        p = Pose(
            cadera=(548, 672), inclinacion=-6, mira=1,
            pie_delante=(676, SUELO - 2), pie_atras=(652, SUELO - 2),
            mano_delante=(640, 646), mano_atras=(520, 682), sonrisa=1.0,
        )
        if variante == "tambalea":
            p.mano_delante, p.mano_atras, p.sonrisa = (700, 520), (430, 548), 2.0
        elif variante == "feliz":
            p.mano_delante, p.sonrisa, p.cabeza = (652, 620), 1.15, 4
        # La postura gira con la silla.
        p.cadera = rotar(p.cadera, PIVOTE, incl)
        p.mano_atras = rotar(p.mano_atras, PIVOTE, incl)
        p.mano_delante = rotar(p.mano_delante, PIVOTE, incl)
        p.inclinacion += incl
        return p

    def _inclinacion(self, a):
        i0, i1 = self.incl0, self.incl1
        if a < 5.2:
            return 0.0
        if a < 6.35:
            return i0 * rebote(tramo(a, 5.2, 5.55), 2.4)
        if a < 7.5:
            u = a - 6.35
            return i0 + 3.2 * math.sin(2 * math.pi * 3.2 * u) * math.exp(-1.9 * u) * (1 - tramo(a, 7.2, 7.5))
        c0, c1 = self.t_cuña
        if a < c0:
            return i0
        if a < c1:
            return lerp(i0, (i0 + i1) / 2, sale(tramo(a, c0, c0 + 0.08)))
        return lerp((i0 + i1) / 2, i1, sale(tramo(a, c1, c1 + 0.08)))

    def _martillo_clave(self, golpe, fase):
        """Mano y ángulo del martillo para golpear `golpe` (el Hacedor mira a la izquierda)."""
        ang_g = -100.0
        d = (math.sin(math.radians(ang_g)), -math.cos(math.radians(ang_g)))
        mano = (golpe[0] - d[0] * 74, golpe[1] - d[1] * 74)
        if fase == "arriba":
            return (mano[0] + 30, mano[1] - 84), 25.0
        if fase == "rebote":
            return (mano[0] + 8, mano[1] - 22), -70.0
        return mano, ang_g

    def _hacedor(self, a: float):
        """Devuelve (pose, ángulo_martillo | None, en_mano: bool)."""
        incl = self._inclinacion(a)
        parp = max(pulso(a, 2.5, 0.16), pulso(a, 7.0, 0.16))
        # 1) Espera a la madera y saca el martillo.
        if a < 1.0:
            p = self._de_pie(760, mirada=(-0.4, -1.0 + tramo(a, 0.3, 0.5) * 1.0))
            u = rebote(tramo(a, 0.55, 0.85))
            p.mano_delante = lerp(p.mano_delante, (690, 470), u)
            golpe = PIEZAS[0][2]
            mano0, ang0 = self._martillo_clave(golpe, "arriba")
            p.mano_delante = lerp(p.mano_delante, mano0, suave(tramo(a, 0.85, 1.0)))
            p.parpado = parp
            return p, (lerp(-160, 10, u) if a >= 0.55 else None)
        # 2) Construcción: cada pieza vuela desde la pila y se clava de un martillazo.
        if a < 5.25:
            claves_mano, claves_ang, claves_x, claves_ag = [], [], [], []
            for i, (_, _, golpe, _) in enumerate(PIEZAS):
                tg = self.t_golpe[i]
                arriba, ang_a = self._martillo_clave(golpe, "arriba")
                abajo, ang_b = self._martillo_clave(golpe, "golpe")
                reb, ang_r = self._martillo_clave(golpe, "rebote")
                claves_mano += [(tg - 0.32, arriba), (tg - 0.08, arriba), (tg, abajo), (tg + 0.12, reb)]
                claves_ang += [(tg - 0.32, ang_a), (tg - 0.08, ang_a + 12), (tg, ang_b), (tg + 0.12, ang_r)]
                x = min(max(abajo[0] + 118, 700), 800)
                ag = limitar((golpe[1] - 600) * 0.55, 0, 70)
                claves_x += [(tg - 0.5, x), (tg - 0.3, x)]
                claves_ag += [(tg - 0.5, ag), (tg - 0.3, ag)]
            fin = self.t_golpe[-1] + 0.35
            claves_mano.append((fin, (700, 640)))
            claves_ang.append((fin, -20.0))
            claves_x.append((fin, 760))
            claves_ag.append((fin, 0))
            x = pista(a, claves_x)
            p = self._de_pie(x, agachado=pista(a, claves_ag), parpado=parp)
            mano = pista(a, claves_mano, curva=lambda u: u)
            p.mano_delante = mano
            p.mirada = (-0.6, 0.3)
            return p, pista(a, claves_ang, curva=lambda u: u)
        # 3) La silla cae torcida: sorpresa.
        if a < 5.8:
            p = self._de_pie(760, sonrisa=lerp(1.0, 2.0, pulso(a, 5.5, 0.5)), mirada=(-0.6, 0.4))
            p.mano_delante = (700, 640)
            return p, -20.0
        # 4) Se gira y se sienta.
        if a < 6.35:
            u = suave(tramo(a, 5.8, 6.35))
            de_pie = self._de_pie(700, mira=1)
            de_pie.mano_delante = (740, 640)
            p = pj.mezclar(de_pie, self._sentado(incl), u)
            return p, 15.0
        # 5) Se tambalea.
        if a < 7.5:
            mov = abs(math.sin(2 * math.pi * 3.2 * (a - 6.35))) * (1 - tramo(a, 7.0, 7.5))
            p = pj.mezclar(self._sentado(incl), self._sentado(incl, "tambalea"),
                           max(mov, 0.75 * (1 - tramo(a, 7.0, 7.5))))
            p.parpado = parp
            return p, lerp(15.0, 40.0, mov)
        # 6) Se levanta y calza la pata corta con una cuña (verde).
        c0, c1 = self.t_cuña
        if a < 8.9:
            pie_pata = rotar((648, SUELO - PATA_CORTA), PIVOTE, incl)
            golpe = (pie_pata[0] + 14, SUELO - 6)
            arriba, ang_a = self._martillo_clave(golpe, "arriba")
            abajo, ang_b = self._martillo_clave(golpe, "golpe")
            reb, ang_r = self._martillo_clave(golpe, "rebote")
            if a < 7.95:
                u = suave(tramo(a, 7.5, 7.95))
                base = self._de_pie(770, agachado=70)
                base.mano_delante = arriba
                p = pj.mezclar(self._sentado(incl), base, u)
                return p, lerp(15.0, ang_a, u)
            claves = [(7.95, arriba), (c0 - 0.1, arriba), (c0, abajo), (c0 + 0.1, reb), (c1 - 0.12, arriba),
                      (c1, abajo), (c1 + 0.12, reb), (8.9, (735, 650))]
            angs = [(7.95, ang_a), (c0 - 0.1, ang_a), (c0, ang_b), (c0 + 0.1, ang_r), (c1 - 0.12, ang_a),
                    (c1, ang_b), (c1 + 0.12, ang_r), (8.9, -20.0)]
            p = self._de_pie(770, agachado=lerp(70, 0, tramo(a, 8.6, 8.9)), mirada=(-0.7, 0.6))
            p.mano_delante = pista(a, claves, curva=lambda u: u)
            return p, pista(a, angs, curva=lambda u: u)
        # 7) Vuelve a sentarse: ahora aguanta. ¡Ding!
        if a < 9.5:
            u = suave(tramo(a, 8.9, 9.5))
            de_pie = self._de_pie(700, mira=1)
            de_pie.mano_delante = (740, 640)
            return pj.mezclar(de_pie, self._sentado(incl), u), 15.0
        # 8) Feliz (un par de botes de alegría y queda quieto).
        u = suave(tramo(a, 9.6, 10.0)) - suave(tramo(a, 10.15, 10.6)) * 0.0
        p = pj.mezclar(self._sentado(incl), self._sentado(incl, "feliz"), suave(tramo(a, 9.6, 10.0)))
        bote = abs(math.sin(math.pi * tramo(a, 9.62, 10.42) * 2)) * 10 * (1 - tramo(a, 9.62, 10.42))
        p.cadera = (p.cadera[0], p.cadera[1] - bote)
        p.mano_delante = (p.mano_delante[0], p.mano_delante[1] - bote * 1.5)
        del u
        return p, lerp(15.0, 22.0, suave(tramo(a, 9.6, 10.0)))

    def _silla(self, lz: Lienzo, a: float, incl: float):
        def R(p):
            return rotar(p, PIVOTE, incl)

        n_puestas = sum(1 for t in self.t_golpe if a >= t - 0.1)
        # Patas del fondo primero (más tenues, desplazadas en perspectiva).
        if n_puestas > 3:
            for r in ((516, 694, 530, SUELO - 14), (664, 694, 678, SUELO - PATA_CORTA - 14)):
                lz.poligono([R(p) for p in _rect(r)], relleno=FONDO, borde=tenue(0.6), ancho=3)
        for i, (nombre, r, _, fondo) in enumerate(PIEZAS):
            if fondo or i >= n_puestas:
                continue
            lz.poligono([R(p) for p in _rect(r)], relleno=FONDO, borde=BLANCO, ancho=3.4)
            if nombre == "respaldo":
                lz.linea([R((490, 500)), R((512, 500))], 2, tenue(0.6))
                lz.linea([R((490, 570)), R((512, 570))], 2, tenue(0.6))
        # Piezas en vuelo desde la pila.
        for i, (nombre, r, _, fondo) in enumerate(PIEZAS):
            t0, t1 = self.t_vuelo[i]
            if not (t0 <= a < t1):
                continue
            u = tramo(a, t0, t1)
            if r is None:
                r = (516, 694, 530, SUELO - 14)
            destino = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            largo, grosor = max(r[2] - r[0], r[3] - r[1]), min(r[2] - r[0], r[3] - r[1])
            vertical = (r[3] - r[1]) > (r[2] - r[0])
            origen = (PILA_H[0], PILA_H[1] - 15 - (N_TABLAS - 1 - i) * 26)
            c = lerp(origen, destino, sale(u))
            c = (c[0], c[1] - math.sin(math.pi * u) * 160)
            ang = lerp(0.0, 90.0 if vertical else 0.0, sale(u)) + math.sin(math.pi * u) * 30
            self._tabla(lz, c, lerp(230, largo, u), lerp(24, grosor, u), ang, semilla=300 + i)
        # Chispas del martillazo.
        for i, tg in enumerate(list(self.t_golpe) + list(self.t_cuña)):
            if tg <= a < tg + 0.16:
                golpe = PIEZAS[i][2] if i < len(PIEZAS) else (rotar((648, SUELO - PATA_CORTA), PIVOTE, incl)[0] + 14,
                                                              SUELO - 6)
                u = tramo(a, tg, tg + 0.16)
                for k in range(5):
                    ang = math.radians(-20 + k * 45)
                    r0, r1 = 18 + 30 * u, 34 + 40 * u
                    lz.linea([(golpe[0] + math.cos(ang) * r0, golpe[1] - math.sin(ang) * r0),
                              (golpe[0] + math.cos(ang) * r1, golpe[1] - math.sin(ang) * r1)], 4 * (1 - u) + 1)

    def _cuna(self, lz: Lienzo, a: float, incl: float):
        c0 = self.t_cuña[0]
        if a < c0 - 0.2:
            return
        u = sale(tramo(a, c0 - 0.2, c0 - 0.05))
        pie = rotar((648, SUELO - PATA_CORTA), PIVOTE, incl)
        h = max(14.0, SUELO - pie[1] + 2)
        dx = lerp(70, 0, u)
        x = pie[0] + dx
        lz.poligono([(x - 30, SUELO), (x + 40, SUELO), (x + 40, SUELO - h), (x - 30, SUELO - h * 0.4)],
                    relleno=mezcla(FONDO, VERDE, 0.35), borde=VERDE, ancho=3)

    def _check(self, lz: Lienzo, a: float):
        t0 = 9.6
        if a < t0:
            return
        s = rebote(tramo(a, t0, t0 + 0.3), 2.2)
        c = (770, 520)
        pts = [(-34, 0), (-10, 26), (38, -30)]
        lz.linea([(c[0] + x * s, c[1] + y * s) for x, y in pts], 12 * max(s, 0.1), VERDE)
        u = tramo(a, t0, t0 + 0.45)
        if u < 1:
            for k in range(8):
                ang = 2 * math.pi * k / 8
                r0, r1 = 50 + 40 * u, 62 + 52 * u
                lz.linea([(c[0] + math.cos(ang) * r0, c[1] + math.sin(ang) * r0),
                          (c[0] + math.cos(ang) * r1, c[1] + math.sin(ang) * r1)], 4 * (1 - u) + 0.5, VERDE)

    def _panel_hacedor(self, lz: Lienzo, a: float):
        caida = 0.0 if a >= 0.4 else 900 * (1 - entra(tramo(a, 0.0, 0.4)))
        aplasta = pulso(a, 0.47, 0.14) * 6
        quitar = sum(1 for (t0, _) in self.t_vuelo if a >= t0)
        self._pila(lz, (PILA_H[0], PILA_H[1] + aplasta), N_TABLAS, caida, quitar)
        incl = self._inclinacion(a)
        self._cuna(lz, a, incl)
        self._silla(lz, a, incl)
        pose, ang = self._hacedor(a)

        def en_mano(lz2, e):
            if ang is not None:
                pj.martillo(lz2, e["mano_d"], ang)

        pj.dibujar(lz, pose, perfeccionista=False, en_mano=en_mano)
        self._check(lz, a)

    # ========================================================= PERFECCIONISTA
    def _preparar_perfeccionista(self):
        n = self.intentos
        self.ciclo_ini = 0.9
        self.ciclo_len = 8.25 / n
        self.final_ini = self.ciclo_ini + n * self.ciclo_len  # 9.15 con 3 intentos
        rnd = random.Random(7)
        self.dibujos = []
        for k in range(n + 1):
            segs = [((0.18, 0.2), (0.18, 0.85)), ((0.18, 0.55), (0.62, 0.55)), ((0.62, 0.55), (0.62, 0.85)),
                    ((0.18, 0.7), (0.62, 0.7))]
            segs = [((a[0] + rnd.uniform(-0.04, 0.04), a[1] + rnd.uniform(-0.05, 0.05)),
                     (b[0] + rnd.uniform(-0.04, 0.04), b[1] + rnd.uniform(-0.05, 0.05))) for a, b in segs]
            segs += [((0.72, 0.2 + 0.1 * j), (0.9, 0.2 + 0.1 * j)) for j in range(3)]
            borrones = [(rnd.uniform(0.18, 0.65), rnd.uniform(0.3, 0.8)) for _ in range(2 + k)]
            self.dibujos.append((segs, borrones))
        self.borrones_final = [(0.24, 0.32), (0.5, 0.42), (0.36, 0.7), (0.62, 0.74), (0.8, 0.5), (0.2, 0.6)]

    def _fases(self, a: float):
        """('fase', progreso, índice_de_intento)."""
        if a < self.ciclo_ini:
            return ("espera", tramo(a, 0, self.ciclo_ini), 0)
        if a < self.final_ini:
            k = int((a - self.ciclo_ini) // self.ciclo_len)
            u = (a - self.ciclo_ini - k * self.ciclo_len) / self.ciclo_len
            for nombre, f0, f1 in (("dibuja", 0.0, 0.26), ("mide", 0.26, 0.46), ("borra", 0.46, 0.71),
                                   ("arruga", 0.71, 0.86), ("tira", 0.86, 0.97), ("pausa", 0.97, 1.0)):
                if u < f1:
                    return (nombre, (u - f0) / (f1 - f0), k)
        f = self.final_ini
        for nombre, f0, f1 in (("dibuja", f, f + 0.45), ("borra", f + 0.45, f + 1.05),
                               ("suspira", f + 1.1, f + 1.85)):
            if a < f1:
                return (nombre, tramo(a, f0, f1), self.intentos)
        return ("fin", 1.0, self.intentos)

    def tiempos_ciclo(self):
        """Instantes (en unidades de acción) de cada fase, para sincronizar el audio."""
        out = []
        for k in range(self.intentos):
            c = self.ciclo_ini + k * self.ciclo_len
            L = self.ciclo_len
            out.append(dict(inicio=c, dibuja=(c, c + 0.26 * L), mide=(c + 0.26 * L, c + 0.46 * L),
                            borra=(c + 0.46 * L, c + 0.71 * L), arruga=(c + 0.71 * L, c + 0.86 * L),
                            tira=(c + 0.86 * L, c + 0.97 * L)))
        f = self.final_ini
        final = dict(inicio=f, dibuja=(f, f + 0.45), borra=(f + 0.45, f + 1.05), suspira=(f + 1.1, f + 1.85))
        return out, final

    def _base_p(self) -> Pose:
        return Pose(cadera=(352, 786), inclinacion=34, mira=1, pie_delante=(462, SUELO - 2),
                    pie_atras=(440, SUELO - 2), mano_delante=(540, 826), mano_atras=(486, 842),
                    sonrisa=0.35, mirada=(0.4, 0.9))

    def _perfeccionista(self, a: float):
        """Devuelve (pose, punta_del_lápiz o None, plano_actual dict)."""
        fase, u, k = self._fases(a)
        p = self._base_p()
        p.parpado = max(pulso(a, 4.8, 0.16), pulso(a, 1.6, 0.16))
        lapiz = True
        if fase == "espera":
            p.mirada = (1.0, lerp(-0.9, 0.2, tramo(u, 0.3, 0.6)))
            p.inclinacion = 20
            p.mano_delante, p.mano_atras = (470, 760), (430, 770)
            lapiz = u > 0.8
        elif fase == "dibuja":
            segs, _ = self.dibujos[k]
            n = len(segs)
            idx = min(int(u * n), n - 1)
            f = u * n - idx
            s0, s1 = segs[idx]
            p.mano_delante = _uv(*lerp(s0, s1, f))
            p.inclinacion = 40
        elif fase == "mide":
            p.inclinacion = 44
            p.cabeza = -8 + 6 * oscila(u, 1.0)
            p.parpado = 0.45
            p.mano_delante = _uv(0.85, 0.62)
            p.mano_atras = _uv(0.12, 0.62)
            p.sonrisa = 0.0
            lapiz = False
        elif fase == "borra":
            _, borr = self.dibujos[min(k, len(self.dibujos) - 1)]
            lista = self.borrones_final if k >= self.intentos else borr
            j = min(int(u * len(lista)), len(lista) - 1)
            c = _uv(*lista[j])
            p.mano_delante = (c[0] + 16 * oscila(u * 9, 1.0), c[1] + 4 * oscila(u * 9, 1.0, 0.25))
            p.inclinacion = 42
            p.sonrisa = -0.2
            lapiz = False
        elif fase == "arruga":
            centro = _uv(0.5, 0.45)
            arriba = (560, 740)
            m = lerp(centro, arriba, suave(u))
            p.mano_delante = (m[0] + 22 * (1 - u), m[1])
            p.mano_atras = (m[0] - 22 * (1 - u), m[1] + 4)
            p.sonrisa = -0.5
            p.inclinacion = lerp(42, 26, u)
            lapiz = False
        elif fase == "tira":
            p.mano_delante = lerp((560, 740), (300, 560), sale(u))
            p.mano_atras = (470, 790)
            p.inclinacion = lerp(26, 10, sale(u))
            p.sonrisa = -0.4
            lapiz = False
        elif fase == "pausa":
            p.mano_delante = lerp((300, 560), (520, 826), suave(u))
            p.inclinacion = lerp(10, 34, suave(u))
        elif fase in ("suspira", "fin"):
            v = suave(u)
            p.inclinacion = lerp(34, 18, v)
            p.hombros = 16 * v
            p.cabeza = 14 * v
            p.sonrisa = lerp(0.3, -0.75, v)
            p.parpado = lerp(0.0, 0.5, v)
            p.mano_delante = lerp((540, 826), (470, 778), v)
            p.mano_atras = lerp((486, 842), (440, 786), v)
            p.mirada = (0.3, 1.0)
            lapiz = v < 0.5
        return p, lapiz, (fase, u, k)

    def _plano(self, lz: Lienzo, fase, u, k):
        """Dibuja la hoja actual con su contenido."""
        final = k >= self.intentos
        segs, borr = self.dibujos[k]
        if fase == "espera":
            return
        aparece = 1.0
        if fase == "dibuja":
            aparece = rebote(tramo(u, 0, 0.12 if not final else 0.2))
        if fase in ("tira", "pausa"):
            return
        centro = _uv(0.5, 0.5)
        plano = PLANO
        if fase == "arruga":
            q = suave(u)
            destino = lerp(centro, (560, 740), q)
            plano = [lerp(lerp(c, centro, q * 0.95), (c[0] - centro[0] + destino[0], c[1] - centro[1] + destino[1]), 0)
                     for c in PLANO]
            plano = [(destino[0] + (c[0] - centro[0]) * (1 - q * 0.92), destino[1] + (c[1] - centro[1]) * (1 - q * 0.92))
                     for c in PLANO]
            if q > 0.55:
                self._bola(lz, destino, 22 * (0.6 + 0.4 * tramo(q, 0.55, 1)), semilla=500 + k)
                return
        elif aparece < 1:
            plano = [(centro[0] + (c[0] - centro[0]) * aparece, centro[1] + (c[1] - centro[1]) * aparece) for c in PLANO]
        lz.poligono(plano, relleno=mezcla(FONDO, BLANCO, 0.06), borde=BLANCO, ancho=3)
        # Líneas del boceto.
        n = len(segs)
        if fase == "dibuja":
            hechas = u * n
        else:
            hechas = n
        for j, (s0, s1) in enumerate(segs):
            if j >= hechas:
                break
            f = min(1.0, hechas - j)
            lz.linea([_uv(*s0, plano), _uv(*lerp(s0, s1, f), plano)], 2.2, tenue(0.85), puntas=False)
        # Cotas al medir.
        if fase in ("mide", "borra", "arruga", "suspira", "fin") and not final:
            regla = [_uv(0.08, 0.62, plano), _uv(0.92, 0.62, plano)]
            if fase == "mide":
                lz.linea(regla, 9, tenue(0.9))
                for j in range(9):
                    x = 0.1 + j * 0.1
                    a0, a1 = _uv(x, 0.6, plano), _uv(x, 0.66, plano)
                    lz.linea([a0, a1], 1.6, FONDO)
        # Borrones (grises) y marcas rojas de "mal".
        if fase in ("borra", "arruga", "suspira", "fin"):
            lista = self.borrones_final if final else borr
            progreso = u if fase == "borra" else 1.0
            for j, (bu, bv) in enumerate(lista):
                inicio = j / len(lista)
                g = limitar((progreso - inicio) * len(lista))
                if g <= 0:
                    continue
                c = _uv(bu, bv, plano)
                rnd = random.Random(900 + k * 31 + j)
                lz.elipse(c, 26 * g, 12 * g, relleno=mezcla(FONDO, BLANCO, 0.3))
                pts = [(c[0] + rnd.uniform(-24, 24) * g, c[1] + rnd.uniform(-10, 10) * g) for _ in range(7)]
                lz.linea(pts, 1.6, tenue(0.55), puntas=False)
            rojas = 2 if final else 1
            for j in range(rojas):
                if progreso < 0.55 + j * 0.2:
                    continue
                bu, bv = lista[j * 2 % len(lista)]
                c = _uv(bu + 0.06, bv - 0.05, plano)
                r = 13 * rebote(tramo(progreso, 0.55 + j * 0.2, 0.7 + j * 0.2))
                lz.linea([(c[0] - r, c[1] - r * 0.6), (c[0] + r, c[1] + r * 0.6)], 5, ROJO)
                lz.linea([(c[0] + r, c[1] - r * 0.6), (c[0] - r, c[1] + r * 0.6)], 5, ROJO)

    def _bolas(self, lz: Lienzo, a: float):
        ciclos, _ = self.tiempos_ciclo()
        for k, c in enumerate(ciclos):
            t0, t1 = c["tira"]
            if a < t0:
                break
            destino = BOLAS[k % len(BOLAS)]
            if a < t1:
                u = tramo(a, t0, t1)
                inicio = (560, 740)
                pos = lerp(inicio, destino, u)
                pos = (pos[0], pos[1] - math.sin(math.pi * u) * 260)
                self._bola(lz, pos, semilla=500 + k)
            else:
                rebota = pulso(a, t1 + 0.06, 0.12) * 12
                self._bola(lz, (destino[0], destino[1] - rebota), semilla=500 + k)

    def _soplido(self, lz: Lienzo, a: float, e):
        """Líneas de aire del suspiro."""
        _, final = self.tiempos_ciclo()
        t0, t1 = final["suspira"]
        u = tramo(a, t0 + 0.1, t1)
        if not (0 < u < 1):
            return
        boca = pj._local(e, self._perfeccionista(a)[0], 0.3 * pj.R_CABEZA, 0.4 * pj.R_CABEZA)
        for j in range(3):
            d = 30 + 60 * u + j * 14
            y = boca[1] + (j - 1) * 14 + 20 * u
            col = tenue(0.8 * (1 - u))
            lz.linea([(boca[0] + d, y), (boca[0] + d + 34, y + 6)], 3, col)

    def _panel_perfeccionista(self, lz: Lienzo, a: float):
        caida = 0.0 if a >= 0.4 else 900 * (1 - entra(tramo(a, 0.0, 0.4)))
        aplasta = pulso(a, 0.47, 0.14) * 6
        self._pila(lz, (PILA_P[0], PILA_P[1] + aplasta), N_TABLAS, caida)
        self._bolas(lz, a)
        pose, lapiz, (fase, u, k) = self._perfeccionista(a)
        self._plano(lz, fase, u, k)

        def en_mano(lz2, e):
            if lapiz:
                m = e["mano_d"]
                lz2.linea([(m[0] - 6, m[1] - 34), (m[0] + 4, m[1] + 6)], 7, BLANCO)
            if fase == "borra":
                m = e["mano_d"]
                lz2.poligono([(m[0] - 14, m[1] - 4), (m[0] + 14, m[1] - 4), (m[0] + 14, m[1] + 10),
                              (m[0] - 14, m[1] + 10)], relleno=BLANCO)
            if fase == "arruga" and suave(u) <= 0.55:
                pass

        e = pj.dibujar(lz, pose, perfeccionista=True, en_mano=en_mano)
        self._soplido(lz, a, e)

    # ================================================================ TEXTOS
    def _alfas(self, t: float):
        D, A = self.D, self.A
        gancho = 1.0 - tramo(t, self.g - 0.18, self.g)
        if t > A:
            gancho = max(gancho, tramo(t, D - 0.45, D - 0.12))
        cierre_in = tramo(t, A + 0.45, A + 0.6)
        cierre_out = 1 - tramo(t, D - 0.75, D - 0.45)
        cierre = cierre_in * cierre_out if t > A else 0.0
        return gancho, cierre

    def _cierre(self, img: Image.Image, t: float, alfa: float):
        if alfa <= 0:
            return
        s = ESCALA
        escala = rebote(tramo(t, self.A + 0.45, self.A + 0.8), 2.0)
        escala = max(0.3, escala)
        cx, cy = self.ancho / 2, ALTO_PANEL
        partes = self.textos["cierre"].split(">")
        if len(partes) == 2:
            trozos = [(partes[0].rstrip() + " ", VERDE), (">", BLANCO), (" " + partes[1].lstrip(), ROJO)]
        else:
            trozos = [(self.textos["cierre"], BLANCO)]
        # Tamaño de letra para que el texto ocupe como mucho 860 px de ancho.
        cadena = "".join(c for c, _ in trozos)
        tam = min(130.0, 130.0 * 860 / (fuente(130 * s).getlength(cadena) / s))
        ancho_txt = fuente(int(tam * s)).getlength(cadena) / s
        w, h = (ancho_txt + 110) * escala, tam * 1.75 * escala

        def plato(d, x0, y0):
            d.rounded_rectangle(
                (cx * s - w * s / 2 - x0, cy * s - h * s / 2 - y0, cx * s + w * s / 2 - x0, cy * s + h * s / 2 - y0),
                radius=int(40 * s * escala), fill=FONDO + (255,), outline=BLANCO + (255,), width=int(4 * s))

        caja = (int((cx - w / 2) * s) - 8, int((cy - h / 2) * s) - 8, int((cx + w / 2) * s) + 8, int((cy + h / 2) * s) + 8)
        capa(img, caja, plato, alfa)
        texto(img, trozos, (cx, cy - 4), tam * escala, alfa)

    def _rebobinado(self, arr: np.ndarray, t: float):
        """Efecto de cinta rebobinando: líneas desplazadas, bandas de ruido y franjas."""
        u = tramo(t, self.g, self.r)
        fuerza = min(1.0, tramo(t, self.g, self.g + 0.12)) * (1 - tramo(t, self.r - 0.18, self.r))
        if fuerza <= 0:
            return arr
        rnd = np.random.default_rng(int(t * 1000))
        alto = arr.shape[0]
        for _ in range(5):
            y0 = int(rnd.integers(0, alto - 60))
            hh = int(rnd.integers(8, 50))
            arr[y0:y0 + hh] = np.roll(arr[y0:y0 + hh], int(rnd.integers(-40, 40) * fuerza), axis=1)
        banda = int((u * 3.3 % 1) * alto)
        hb = 34
        seg = arr[banda:banda + hb].astype(np.int16)
        ruido = rnd.integers(0, 200, size=seg.shape[:2], dtype=np.int16)[..., None]
        seg = np.clip(seg + (ruido * fuerza * (ruido > 170)).astype(np.int16), 0, 255)
        arr[banda:banda + hb] = seg.astype(np.uint8)
        arr[::4] = (arr[::4].astype(np.float32) * (1 - 0.22 * fuerza)
                    + np.array(FONDO, np.float32) * 0.22 * fuerza).astype(np.uint8)
        return arr

    def _icono_rebobinar(self, img: Image.Image, t: float):
        if not (self.g <= t < self.r):
            return
        alfa = tramo(t, self.g, self.g + 0.1) * (1 - tramo(t, self.r - 0.15, self.r))
        parpadeo = 0.75 + 0.25 * (1 if int(t * 6) % 2 else 0)
        cx, cy, s = self.ancho / 2, ALTO_PANEL, ESCALA

        def dib(d, x0, y0):
            d.ellipse(((cx - 70) * s - x0, (cy - 70) * s - y0, (cx + 70) * s - x0, (cy + 70) * s - y0),
                      fill=FONDO + (255,), outline=BLANCO + (255,), width=4 * s)
            for dx in (-34, 6):
                d.polygon([((cx + dx + 34) * s - x0, (cy - 30) * s - y0), ((cx + dx) * s - x0, cy * s - y0),
                           ((cx + dx + 34) * s - x0, (cy + 30) * s - y0)], fill=BLANCO + (255,))

        capa(img, (int((cx - 76) * s), int((cy - 76) * s), int((cx + 76) * s), int((cy + 76) * s)), dib,
             alfa * parpadeo)

    # ============================================================== FOTOGRAMA
    def fotograma(self, t: float) -> Image.Image:
        a = self.accion(t)
        img = self._fondo.copy()
        # Cada panel se dibuja recortado, para que nada invada la otra mitad.
        for i, dibujar_panel in enumerate((self._panel_hacedor, self._panel_perfeccionista)):
            caja = (0, i * ALTO_PANEL * ESCALA, self.ancho * ESCALA, (i + 1) * ALTO_PANEL * ESCALA)
            panel = img.crop(caja)
            dibujar_panel(Lienzo(panel, 0, 0), a)
            img.paste(panel, caja[:2])
        # Separación de la pantalla partida.
        Lienzo(img).boceto((0, ALTO_PANEL), (self.ancho, ALTO_PANEL), 3.2, tenue(0.85), semilla=999, amp=1.0)
        gancho, cierre = self._alfas(t)
        texto(img, [(self.textos["gancho"], BLANCO)], (self.ancho / 2, 150), 66, gancho)
        self._cierre(img, t, cierre)
        self._icono_rebobinar(img, t)
        texto(img, [(self.textos["marca"], tenue(0.75))], (44, 62), 26, 1.0, ancla="lm")
        img = img.reduce(ESCALA)
        if self.g <= t < self.r:
            arr = self._rebobinado(np.array(img), t)
            img = Image.fromarray(arr)
        return img

    # ================================================================== AUDIO
    def eventos_audio(self):
        """Lista de (segundo, efecto, ganancia, paneo, parámetros)."""
        R = self.real
        ev = [(self.g, "rebobinado", 0.8, 0.0, {"dur": self.r - self.g}), (R(0.4), "golpe_madera", 0.9, 0.0, {})]
        for i, tg in enumerate(self.t_golpe):
            ev.append((R(tg), "martillo", 0.85, -0.25, {"semilla": i}))
        ev.append((R(5.32), "crujido", 0.6, -0.25, {}))
        for tg in self.t_cuña:
            ev.append((R(tg), "martillo", 0.75, -0.25, {"semilla": 9}))
        ev.append((R(6.4), "crujido", 0.4, -0.25, {"semilla": 3}))
        ev.append((R(9.6), "ding", 0.9, -0.15, {}))
        ciclos, final = self.tiempos_ciclo()
        for k, c in enumerate(ciclos):
            ev.append((R(c["inicio"]), "hoja", 0.55, 0.25, {"semilla": k}))
            ev.append((R(c["dibuja"][0]), "lapiz", 0.5, 0.25, {"dur": (c["dibuja"][1] - c["dibuja"][0]) * self.k}))
            ev.append((R(c["borra"][0]), "borrador", 0.7, 0.25, {"dur": (c["borra"][1] - c["borra"][0]) * self.k}))
            ev.append((R(c["arruga"][0]), "papel", 0.85, 0.25, {"semilla": k,
                                                                 "dur": (c["arruga"][1] - c["arruga"][0]) * self.k}))
            ev.append((R(c["tira"][1]), "bola", 0.5, 0.35, {}))
        ev.append((R(final["inicio"]), "hoja", 0.55, 0.25, {"semilla": 9}))
        ev.append((R(final["dibuja"][0]), "lapiz", 0.5, 0.25, {"dur": 0.45 * self.k}))
        ev.append((R(final["borra"][0]), "borrador", 0.75, 0.25, {"dur": 0.6 * self.k}))
        ev.append((R(final["suspira"][0]), "suspiro", 0.9, 0.2, {"dur": 1.1}))
        ev.append((self.A + 0.45, "titulo", 0.8, 0.0, {}))
        return ev
