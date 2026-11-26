"""Episodio 1: "La silla".

Arriba, el Hacedor construye una silla, le sale torcida, la calza con una cuña
y se sienta feliz. Abajo, el Perfeccionista mide, borra y arruga sus planos.
"""
from __future__ import annotations

import math

from PIL import Image

from . import decorado as dec
from . import personajes as pj
from .base import ALTO_PANEL, PILA_H, SUELO, EpisodioBase, rect
from .lienzo import BLANCO, VERDE, Lienzo, fondo, mezcla, rotar, tenue
from .personajes import Pose
from .tiempo import lerp, limitar, pista, pulso, rebote, sale, suave, tramo

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


class EpisodioSilla(EpisodioBase):
    POS_GANCHO = "arriba"
    N_TABLAS = len(PIEZAS)

    # --------------------------------------------------------------- decorado
    def _decorado(self) -> Image.Image:
        img, arriba, abajo = self.lienzo_fondo()
        # Abajo: lámpara con su luz (se pinta primero para que las líneas queden encima).
        abajo = dec.lampara(img, abajo, 190, 120, ALTO_PANEL, semilla=50)
        arriba = Lienzo(img, 0, 0)
        dec.suelo(arriba, 0)
        dec.suelo(abajo, 1)
        # Arriba: ventana con luna y estrellas.
        self.estrellas = dec.ventana(arriba, (86, 236, 316, 470), panel=0, semilla=41, luna=(250, 300, 26))
        # Abajo: el único cartel de la serie en este episodio (la silla "perfecta").
        dec.cartel(abajo, (630, 210, 880, 440),
                   [((700, 280), (700, 410)), ((700, 350), (800, 350)), ((800, 350), (800, 410)),
                    ((700, 380), (800, 380))],
                   [((700, 424), (800, 424)), ((818, 350), (818, 410)), ((680, 280), (680, 410))], semilla=60)
        return img

    def boceto_plano(self):
        return [((0.18, 0.2), (0.18, 0.85)), ((0.18, 0.55), (0.62, 0.55)), ((0.62, 0.55), (0.62, 0.85)),
                ((0.18, 0.7), (0.62, 0.7))]

    # ================================================================ HACEDOR
    def _preparar_hacedor(self):
        self.t_golpe = [1.30 + 0.72 * i for i in range(len(PIEZAS))]
        self.t_vuelo = [(t - 0.48, t - 0.10) for t in self.t_golpe]
        self.t_cuña = (8.15, 8.50)

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
                lz.poligono([R(p) for p in rect(r)], relleno=fondo(), borde=tenue(0.6), ancho=3)
        for i, (nombre, r, _, del_fondo) in enumerate(PIEZAS):
            if del_fondo or i >= n_puestas:
                continue
            lz.poligono([R(p) for p in rect(r)], relleno=fondo(), borde=BLANCO, ancho=3.4)
            if nombre == "respaldo":
                lz.linea([R((490, 500)), R((512, 500))], 2, tenue(0.6))
                lz.linea([R((490, 570)), R((512, 570))], 2, tenue(0.6))
        # Piezas en vuelo desde la pila.
        for i, (nombre, r, _, del_fondo) in enumerate(PIEZAS):
            t0, t1 = self.t_vuelo[i]
            if r is None:
                r = (516, 694, 530, SUELO - 14)
            destino = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            largo, grosor = max(r[2] - r[0], r[3] - r[1]), min(r[2] - r[0], r[3] - r[1])
            self._tabla_volando(lz, a, t0, t1, i, destino, largo, grosor, (r[3] - r[1]) > (r[2] - r[0]))
        # Chispas del martillazo.
        for i, tg in enumerate(list(self.t_golpe) + list(self.t_cuña)):
            if tg <= a < tg + 0.16:
                golpe = PIEZAS[i][2] if i < len(PIEZAS) else (rotar((648, SUELO - PATA_CORTA), PIVOTE, incl)[0] + 14,
                                                              SUELO - 6)
                self._chispas(lz, golpe, tramo(a, tg, tg + 0.16))

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
                    relleno=mezcla(fondo(), VERDE, 0.35), borde=VERDE, ancho=3)

    def _panel_hacedor(self, lz: Lienzo, a: float):
        caida, aplasta = self._caida_pila(a)
        quitar = sum(1 for (t0, _) in self.t_vuelo if a >= t0)
        self._pila(lz, (PILA_H[0], PILA_H[1] + aplasta), self.n_tablas, caida, quitar)
        incl = self._inclinacion(a)
        self._cuna(lz, a, incl)
        self._silla(lz, a, incl)
        pose, ang = self._hacedor(a)

        def en_mano(lz2, e):
            if ang is not None:
                pj.martillo(lz2, e["mano_d"], ang)

        pj.dibujar(lz, pose, perfeccionista=False, en_mano=en_mano)
        self._check(lz, a, (770, 520))

    def eventos_hacedor(self):
        R = self.real
        ev = []
        for i, tg in enumerate(self.t_golpe):
            ev.append((R(tg), "martillo", 0.85, -0.25, {"semilla": i}))
        ev.append((R(5.32), "crujido", 0.6, -0.25, {}))
        for tg in self.t_cuña:
            ev.append((R(tg), "martillo", 0.75, -0.25, {"semilla": 9}))
        ev.append((R(6.4), "crujido", 0.4, -0.25, {"semilla": 3}))
        ev.append((R(9.6), "ding", 0.9, -0.15, {}))
        return ev
