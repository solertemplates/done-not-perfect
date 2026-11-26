"""Base común de todos los episodios.

Pantalla partida durante todo el episodio: arriba el Hacedor, abajo el
Perfeccionista. Cada panel es una función pura del "tiempo de acción" `a`
(0..11 unidades), de modo que:

* el gancho (segundo 0) y el final muestran exactamente el estado a = 11,
* el rebobinado recorre `a` hacia atrás de 11 a 0,
* la acción recorre `a` hacia delante de 0 a 11.

El último fotograma es idéntico al primero, así el bucle no se nota. Lo que
se mueve siempre (estrellas que parpadean) tiene un periodo igual al del bucle.

Cada episodio define su decorado, el Hacedor y el boceto del plano del
Perfeccionista; el resto (rebobinado, textos, Perfeccionista, audio común)
está aquí.
"""
from __future__ import annotations

import math
import random

import numpy as np
from PIL import Image

from . import decorado as dec
from . import personajes as pj
from .config import Episodio
from .lienzo import (BLANCO, ESCALA, FONDOS, ROJO, VERDE, Lienzo, capa, fondo, fuente, mezcla, rotar, tenue,
                     texto, usar_fondo)
from .personajes import Pose
from .tiempo import entra, lerp, limitar, oscila, pulso, rebote, sale, suave, tramo

A_FIN = 11.0  # duración de la acción en unidades internas
ALTO_PANEL = 960
SUELO = dec.SUELO

PILA_H = (210, SUELO)  # pila de madera del Hacedor (lado izquierdo)
PILA_P = (880, SUELO)  # pila del Perfeccionista (lado derecho, intacta)

# --- Plano del Perfeccionista (trapecio sobre el suelo, en primer plano) ------
PLANO = [(470, 814), (722, 814), (752, 904), (448, 904)]  # sup-izq, sup-der, inf-der, inf-izq
BOLAS = [(262, 792), (212, 794), (238, 752), (168, 795)]


def rect(r):
    x0, y0, x1, y1 = r
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _uv(u, v, plano=PLANO):
    a, b, c, d = plano
    top = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
    bot = (d[0] + (c[0] - d[0]) * u, d[1] + (c[1] - d[1]) * u)
    return (top[0] + (bot[0] - top[0]) * v, top[1] + (bot[1] - top[1]) * v)


class EpisodioBase:
    POS_GANCHO = "arriba"  # "arriba" (texto sobre la escena) o "centro" (tarjeta en la línea central)
    N_TABLAS = 6

    def __init__(self, ep: Episodio):
        self.ep = ep
        t = ep["tiempos"]
        self.g = float(t["gancho_fin_s"])
        self.r = float(t["rebobinado_fin_s"])
        self.A = float(t["accion_fin_s"])
        self.D = ep.duracion
        self.k = (self.A - self.r) / A_FIN  # segundos reales por unidad de acción
        # El último fotograma (D - 1/fps) debe ser idéntico al primero.
        self.periodo_bucle = self.D - 1.0 / ep.fps
        self.ancho, self.alto = ep.tamano
        self.textos = ep["textos"]
        self.intentos = ep["perfeccionista"]["intentos"]
        self.n_tablas = self.N_TABLAS
        h = ep["hacedor"]
        self.incl0 = float(h["inclinacion_inicial_grados"])
        self.incl1 = float(h["inclinacion_final_grados"])
        self.color_fondo = FONDOS[ep["fondo"]]
        usar_fondo(self.color_fondo)
        self.estrellas: list[dec.Estrella] = []
        self._preparar_hacedor()
        self._preparar_perfeccionista()
        self._fondo = self._decorado()

    # --- a definir en cada episodio ----------------------------------------------
    def _decorado(self) -> Image.Image:
        raise NotImplementedError

    def _preparar_hacedor(self):
        raise NotImplementedError

    def _panel_hacedor(self, lz: Lienzo, a: float):
        raise NotImplementedError

    def eventos_hacedor(self) -> list:
        raise NotImplementedError

    def boceto_plano(self) -> list:
        """Trazos (en coordenadas u,v de 0 a 1) de lo que dibuja el Perfeccionista."""
        raise NotImplementedError

    def lienzo_fondo(self) -> tuple[Image.Image, Lienzo, Lienzo]:
        img = Image.new("RGB", (self.ancho * ESCALA, self.alto * ESCALA), fondo())
        return img, Lienzo(img, 0, 0), Lienzo(img, 0, ALTO_PANEL)

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

    # ------------------------------------------------------------- utilidades
    @staticmethod
    def _tabla(lz: Lienzo, centro, largo, grosor, angulo, semilla, color=BLANCO):
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
        lz.circulo(c, r, relleno=fondo(), borde=BLANCO, ancho=3.5)
        rnd = random.Random(semilla)
        pts = [(c[0] + rnd.uniform(-0.6, 0.6) * r, c[1] + rnd.uniform(-0.6, 0.6) * r) for _ in range(5)]
        lz.linea(pts, 1.8, tenue(0.7), puntas=False)

    # ------------------------------------------------- ayudas para el Hacedor
    def _de_pie(self, x, mira=-1, agachado=0.0, **kw) -> Pose:
        y = SUELO - 186 + agachado
        return Pose(
            cadera=(x, y), inclinacion=8 + agachado * 0.35, mira=mira,
            pie_delante=(x + 24 * mira, SUELO - 2), pie_atras=(x - 18 * mira, SUELO - 2),
            mano_delante=(x + 38 * mira, y + 92), mano_atras=(x - 34 * mira, y + 96), **kw,
        )

    @staticmethod
    def _martillo_clave(golpe, fase):
        """Mano y ángulo del martillo para golpear `golpe` (el Hacedor mira a la izquierda)."""
        ang_g = -100.0
        d = (math.sin(math.radians(ang_g)), -math.cos(math.radians(ang_g)))
        mano = (golpe[0] - d[0] * 74, golpe[1] - d[1] * 74)
        if fase == "arriba":
            return (mano[0] + 30, mano[1] - 84), 25.0
        if fase == "rebote":
            return (mano[0] + 8, mano[1] - 22), -70.0
        return mano, ang_g

    @staticmethod
    def _chispas(lz: Lienzo, golpe, u: float):
        for k in range(5):
            ang = math.radians(-20 + k * 45)
            r0, r1 = 18 + 30 * u, 34 + 40 * u
            lz.linea([(golpe[0] + math.cos(ang) * r0, golpe[1] - math.sin(ang) * r0),
                      (golpe[0] + math.cos(ang) * r1, golpe[1] - math.sin(ang) * r1)], 4 * (1 - u) + 1)

    @staticmethod
    def _check(lz: Lienzo, a: float, c, t0: float = 9.6):
        """Marca verde de 'conseguido' que aparece con un pequeño estallido."""
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

    def _tabla_volando(self, lz: Lienzo, a: float, t0: float, t1: float, i: int, destino, largo, grosor,
                       vertical: bool):
        """Tabla que sale de la pila del Hacedor y vuela hasta su sitio."""
        if not (t0 <= a < t1):
            return
        u = tramo(a, t0, t1)
        origen = (PILA_H[0], PILA_H[1] - 15 - (self.n_tablas - 1 - i) * 26)
        c = lerp(origen, destino, sale(u))
        c = (c[0], c[1] - math.sin(math.pi * u) * 160)
        ang = lerp(0.0, 90.0 if vertical else 0.0, sale(u)) + math.sin(math.pi * u) * 30
        self._tabla(lz, c, lerp(230, largo, u), lerp(24, grosor, u), ang, semilla=300 + i)

    def _caida_pila(self, a: float):
        caida = 0.0 if a >= 0.4 else 900 * (1 - entra(tramo(a, 0.0, 0.4)))
        return caida, pulso(a, 0.47, 0.14) * 6

    # ========================================================= PERFECCIONISTA
    def _preparar_perfeccionista(self):
        n = self.intentos
        self.ciclo_ini = 0.9
        self.ciclo_len = 8.25 / n
        self.final_ini = self.ciclo_ini + n * self.ciclo_len  # 9.15 con 3 intentos
        rnd = random.Random(7)
        self.dibujos = []
        for k in range(n + 1):
            segs = self.boceto_plano()
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
        lz.poligono(plano, relleno=mezcla(fondo(), BLANCO, 0.06), borde=BLANCO, ancho=3)
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
                    lz.linea([a0, a1], 1.6, fondo())
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
                lz.elipse(c, 26 * g, 12 * g, relleno=mezcla(fondo(), BLANCO, 0.3))
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
        caida, aplasta = self._caida_pila(a)
        self._pila(lz, (PILA_P[0], PILA_P[1] + aplasta), self.n_tablas, caida)
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

    def _tarjeta(self, img: Image.Image, trozos, alfa: float, escala: float = 1.0, tam_max: float = 130.0,
                 ancho_max: float = 860.0):
        """Texto grande sobre un recuadro redondeado, centrado en la línea de la pantalla partida."""
        if alfa <= 0:
            return
        s = ESCALA
        cx, cy = self.ancho / 2, ALTO_PANEL
        cadena = "".join(c for c, _ in trozos)
        tam = min(tam_max, tam_max * ancho_max / (fuente(int(tam_max * s)).getlength(cadena) / s))
        ancho_txt = fuente(int(tam * s)).getlength(cadena) / s
        w, h = (ancho_txt + 110) * escala, tam * 1.75 * escala

        def plato(d, x0, y0):
            d.rounded_rectangle(
                (cx * s - w * s / 2 - x0, cy * s - h * s / 2 - y0, cx * s + w * s / 2 - x0, cy * s + h * s / 2 - y0),
                radius=int(40 * s * escala), fill=fondo() + (255,), outline=BLANCO + (255,), width=int(4 * s))

        caja = (int((cx - w / 2) * s) - 8, int((cy - h / 2) * s) - 8, int((cx + w / 2) * s) + 8, int((cy + h / 2) * s) + 8)
        capa(img, caja, plato, alfa)
        texto(img, trozos, (cx, cy - 4), tam * escala, alfa)

    def _cierre(self, img: Image.Image, t: float, alfa: float):
        if alfa <= 0:
            return
        escala = max(0.3, rebote(tramo(t, self.A + 0.45, self.A + 0.8), 2.0))
        partes = self.textos["cierre"].split(">")
        if len(partes) == 2:
            trozos = [(partes[0].rstrip() + " ", VERDE), (">", BLANCO), (" " + partes[1].lstrip(), ROJO)]
        else:
            trozos = [(self.textos["cierre"], BLANCO)]
        self._tarjeta(img, trozos, alfa, escala)

    def _gancho(self, img: Image.Image, alfa: float):
        if self.POS_GANCHO == "centro":
            self._tarjeta(img, [(self.textos["gancho"], BLANCO)], alfa, tam_max=74, ancho_max=820)
        else:
            texto(img, [(self.textos["gancho"], BLANCO)], (self.ancho / 2, 150), 66, alfa)

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
                    + np.array(fondo(), np.float32) * 0.22 * fuerza).astype(np.uint8)
        return arr

    def _icono_rebobinar(self, img: Image.Image, t: float):
        if not (self.g <= t < self.r):
            return
        alfa = tramo(t, self.g, self.g + 0.1) * (1 - tramo(t, self.r - 0.15, self.r))
        parpadeo = 0.75 + 0.25 * (1 if int(t * 6) % 2 else 0)
        cx, cy, s = self.ancho / 2, ALTO_PANEL, ESCALA

        def dib(d, x0, y0):
            d.ellipse(((cx - 70) * s - x0, (cy - 70) * s - y0, (cx + 70) * s - x0, (cy + 70) * s - y0),
                      fill=fondo() + (255,), outline=BLANCO + (255,), width=4 * s)
            for dx in (-34, 6):
                d.polygon([((cx + dx + 34) * s - x0, (cy - 30) * s - y0), ((cx + dx) * s - x0, cy * s - y0),
                           ((cx + dx + 34) * s - x0, (cy + 30) * s - y0)], fill=BLANCO + (255,))

        capa(img, (int((cx - 76) * s), int((cy - 76) * s), int((cx + 76) * s), int((cy + 76) * s)), dib,
             alfa * parpadeo)

    # ============================================================== FOTOGRAMA
    def fotograma(self, t: float) -> Image.Image:
        usar_fondo(self.color_fondo)
        a = self.accion(t)
        fase_bucle = (t / self.periodo_bucle) % 1.0
        img = self._fondo.copy()
        # Cada panel se dibuja recortado, para que nada invada la otra mitad.
        for i, dibujar_panel in enumerate((self._panel_hacedor, self._panel_perfeccionista)):
            caja = (0, i * ALTO_PANEL * ESCALA, self.ancho * ESCALA, (i + 1) * ALTO_PANEL * ESCALA)
            panel = img.crop(caja)
            lz = Lienzo(panel, 0, 0)
            dec.estrellas(lz, self.estrellas, i, fase_bucle)
            dibujar_panel(lz, a)
            img.paste(panel, caja[:2])
        # Separación de la pantalla partida.
        Lienzo(img).boceto((0, ALTO_PANEL), (self.ancho, ALTO_PANEL), 3.2, tenue(0.85), semilla=999, amp=1.0)
        gancho, cierre = self._alfas(t)
        self._gancho(img, gancho)
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
        ev += self.eventos_hacedor()
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
