"""Episodio 2: "La escalera".

Arriba, el Hacedor construye una escalera sencilla (algo torcida), sube, un
peldaño se tambalea, lo refuerza (detalle verde) y vuelve a subir hasta mirar
las estrellas por una ventana alta. Abajo, el Perfeccionista dibuja planos de
escaleras bajo la lámpara, los borra y los arruga.
"""
from __future__ import annotations

import math

from PIL import Image

from . import decorado as dec
from . import personajes as pj
from .base import ALTO_PANEL, PILA_H, SUELO, EpisodioBase
from .lienzo import VERDE, Lienzo, mezcla, fondo, rotar
from .personajes import Pose
from .tiempo import lerp, limitar, oscila, pista, pulso, rebote, sale, suave, tramo

# --- Escalera (vista de frente, coordenadas del panel superior) ---------------
BASE = (470, SUELO)  # la escalera se balancea sobre este punto
RIEL_I = ((404, SUELO), (420, 380))
RIEL_D = ((536, SUELO), (524, 380))
PELDANOS_Y = [736, 672, 608, 544, 480]
TORCIDO = 2  # el peldaño del medio es el que sale torcido
INCLINACION_FIJA = [1.2, -1.6, 0.0, 0.9, -1.1]  # ningún peldaño queda perfecto
VENTANA = (600, 50, 860, 262)
NIVEL_FINAL = 4  # se queda de pie en el 4.º peldaño

# Momentos clave (unidades de acción, 0..11)
T_GOLPES = [1.30 + 0.60 * i for i in range(7)]
T_TAMBALEO = (6.8, 7.5)
T_ARREGLO = (8.10, 8.40)
T_DING = 9.6
PASOS_1 = (6.15, 6.8)  # sube del suelo al peldaño torcido
PASOS_2 = (8.85, 9.45)  # sube hasta arriba


def _x_riel(riel, y):
    (x0, y0), (x1, y1) = riel
    return x0 + (x1 - x0) * (y - y0) / (y1 - y0)


def _y_nivel(nivel: float) -> float:
    """Altura de los pies: nivel 0 = suelo, nivel k = peldaño k-1."""
    alturas = [SUELO] + PELDANOS_Y
    k = int(limitar(math.floor(nivel), 0, len(alturas) - 2))
    f = limitar(nivel - k, 0, 1)
    return alturas[k] + (alturas[k + 1] - alturas[k]) * f


class EpisodioEscalera(EpisodioBase):
    POS_GANCHO = "centro"
    N_TABLAS = 7

    # --------------------------------------------------------------- decorado
    def _decorado(self) -> Image.Image:
        img, arriba, abajo = self.lienzo_fondo()
        abajo = dec.lampara(img, abajo, 560, 150, ALTO_PANEL, semilla=80)
        arriba = Lienzo(img, 0, 0)
        dec.suelo(arriba, 0)
        dec.suelo(abajo, 1)
        # Arriba: ventana alta con estrellas (sin luna: hoy manda el cielo estrellado).
        self.estrellas = dec.ventana(arriba, VENTANA, panel=0, semilla=91, densidad=1.3)
        # Abajo: el único cartel, con la escalera "perfecta".
        trazos = [((790, 250), (790, 420)), ((880, 250), (880, 420))]
        trazos += [((790, y), (880, y)) for y in (290, 330, 370, 410)]
        cotas = [((770, 290), (770, 330)), ((790, 436), (880, 436))]
        dec.cartel(abajo, (740, 216, 930, 456), trazos, cotas, semilla=100)
        return img

    def boceto_plano(self):
        segs = [((0.2, 0.15), (0.24, 0.9)), ((0.56, 0.15), (0.52, 0.9))]
        segs += [((0.22, v), (0.54, v)) for v in (0.3, 0.45, 0.6, 0.75)]
        return segs

    # ================================================================ HACEDOR
    def _preparar_hacedor(self):
        self.t_golpe = T_GOLPES
        self.t_vuelo = [(t - 0.45, t - 0.10) for t in self.t_golpe]

    def _piezas(self):
        """(centro, largo, grosor, vertical, punto_de_golpe) de cada pieza, en orden de montaje."""
        out = []
        for riel in (RIEL_I, RIEL_D):
            (x0, y0), (x1, y1) = riel
            c = ((x0 + x1) / 2, (y0 + y1) / 2)
            golpe_y = 560 if riel is RIEL_I else 600
            out.append((c, math.dist(riel[0], riel[1]), 16, True, (_x_riel(riel, golpe_y) + 9, golpe_y)))
        for y in PELDANOS_Y:
            xi, xd = _x_riel(RIEL_I, y), _x_riel(RIEL_D, y)
            out.append((((xi + xd) / 2, y), xd - xi + 18, 13, False, (xd + 8, y)))
        return out

    def _torcido(self, a: float) -> float:
        """Inclinación del peldaño torcido."""
        i0, i1 = self.incl0, self.incl1
        t0, t1 = T_TAMBALEO
        if t0 <= a < t1:
            u = a - t0
            return i0 + 4.0 * abs(math.sin(2 * math.pi * 3.0 * u)) * (1 - tramo(a, t1 - 0.25, t1))
        c0, c1 = T_ARREGLO
        if a < c0:
            return i0
        if a < c1:
            return lerp(i0, (i0 + i1) / 2, sale(tramo(a, c0, c0 + 0.08)))
        return lerp((i0 + i1) / 2, i1, sale(tramo(a, c1, c1 + 0.08)))

    def _balanceo(self, a: float) -> float:
        """La escalera entera se balancea un poco cuando el peldaño cede."""
        t0, t1 = T_TAMBALEO
        if not (t0 <= a < t1):
            return 0.0
        return 3.2 * math.sin(2 * math.pi * 3.0 * (a - t0)) * math.exp(-1.6 * (a - t0)) * (1 - tramo(a, t1 - 0.2, t1))

    def _nivel(self, a: float) -> float:
        if a < PASOS_1[0]:
            return 0.0
        if a < PASOS_1[1]:
            return self._escalones(a, PASOS_1, 0, 3)
        if a < T_TAMBALEO[1]:
            return 3.0
        if a < 7.75:
            return 3.0 * (1 - suave(tramo(a, T_TAMBALEO[1], 7.75)))
        if a < PASOS_2[0]:
            return 0.0
        return self._escalones(a, PASOS_2, 0, NIVEL_FINAL)

    @staticmethod
    def _escalones(a, tramo_t, desde, hasta):
        """Sube peldaño a peldaño (cada paso con su pequeña pausa)."""
        n = hasta - desde
        u = tramo(a, *tramo_t) * n
        k = min(int(u), n - 1)
        return desde + k + suave(min(1.0, (u - k) * 1.3))

    def _trepando(self, nivel: float) -> Pose:
        k = math.floor(nivel)
        f = nivel - k
        delante = _y_nivel(k + min(1.0, f * 2))
        atras = _y_nivel(k + max(0.0, f * 2 - 1))
        if k % 2:
            delante, atras = atras, delante
        y_pies = _y_nivel(nivel)
        y_manos = max(_y_nivel(nivel) - 300, 392)
        return Pose(
            cadera=(462, y_pies - 182), inclinacion=6, mira=1,
            pie_delante=(480, delante - 6), pie_atras=(460, atras - 6),
            mano_delante=(_x_riel(RIEL_D, y_manos) + 2, y_manos),
            mano_atras=(_x_riel(RIEL_I, y_manos) - 2, y_manos + 26),
            mirada=(0.6, -0.6), sonrisa=1.0,
        )

    def _rotar_pose(self, p: Pose, ang: float) -> Pose:
        if not ang:
            return p
        for campo in ("cadera", "mano_delante", "mano_atras", "pie_delante", "pie_atras"):
            setattr(p, campo, rotar(getattr(p, campo), BASE, ang))
        p.inclinacion += ang * p.mira
        return p

    def _construyendo(self, a: float):
        claves_mano, claves_ang, claves_x, claves_ag = [], [], [], []
        for i, (_, _, _, _, golpe) in enumerate(self._piezas()):
            tg = self.t_golpe[i]
            arriba, ang_a = self._martillo_clave(golpe, "arriba")
            abajo, ang_b = self._martillo_clave(golpe, "golpe")
            reb, ang_r = self._martillo_clave(golpe, "rebote")
            claves_mano += [(tg - 0.30, arriba), (tg - 0.08, arriba), (tg, abajo), (tg + 0.11, reb)]
            claves_ang += [(tg - 0.30, ang_a), (tg - 0.08, ang_a + 12), (tg, ang_b), (tg + 0.11, ang_r)]
            x = min(max(abajo[0] + 118, 640), 760)
            ag = limitar((golpe[1] - 600) * 0.55, 0, 70)
            claves_x += [(tg - 0.45, x), (tg - 0.28, x)]
            claves_ag += [(tg - 0.45, ag), (tg - 0.28, ag)]
        fin = self.t_golpe[-1] + 0.35
        claves_mano.append((fin, (650, 650)))
        claves_ang.append((fin, -20.0))
        claves_x.append((fin, 720))
        claves_ag.append((fin, 0))
        p = self._de_pie(pista(a, claves_x), agachado=pista(a, claves_ag))
        p.mano_delante = pista(a, claves_mano, curva=lambda u: u)
        p.mirada = (-0.6, 0.0)
        return p, pista(a, claves_ang, curva=lambda u: u)

    def _hacedor(self, a: float):
        """Devuelve (pose, ángulo del martillo en la mano o None)."""
        parp = max(pulso(a, 2.6, 0.16), pulso(a, 5.5, 0.16))
        balanceo = self._balanceo(a)
        # 1) Espera la madera y saca el martillo.
        if a < 1.0:
            p = self._de_pie(720, mirada=(-0.4, -1.0 + tramo(a, 0.3, 0.5)), parpado=parp)
            u = rebote(tramo(a, 0.55, 0.85))
            p.mano_delante = lerp(p.mano_delante, (650, 470), u)
            mano0, _ = self._martillo_clave(self._piezas()[0][4], "arriba")
            p.mano_delante = lerp(p.mano_delante, mano0, suave(tramo(a, 0.85, 1.0)))
            return p, (lerp(-160, 10, u) if a >= 0.55 else None)
        # 2) Construye: largueros y peldaños, de martillazo en martillazo.
        if a < 5.25:
            p, ang = self._construyendo(a)
            p.parpado = parp
            return p, ang
        # 3) Da un paso atrás y la mira satisfecho.
        if a < 5.8:
            p = self._de_pie(720, mirada=(-0.7, -0.5))
            p.cabeza = 6 * oscila(tramo(a, 5.3, 5.75), 2.0)
            p.mano_delante = (650, 650)
            return p, -20.0
        # 4) Deja el martillo, va a la escalera y sube hasta el peldaño torcido.
        if a < PASOS_1[0]:
            u = suave(tramo(a, 5.8, PASOS_1[0]))
            de_pie = self._de_pie(700, mira=1)
            return pj.mezclar(de_pie, self._trepando(0.0), u), None
        if a < T_TAMBALEO[0]:
            p = self._trepando(self._nivel(a))
            p.parpado = parp
            return p, None
        # 5) ¡El peldaño cede! Se tambalea con los brazos abiertos.
        if a < T_TAMBALEO[1]:
            p = self._trepando(3.0)
            mov = abs(math.sin(2 * math.pi * 3.0 * (a - T_TAMBALEO[0]))) * (1 - tramo(a, 7.25, 7.5))
            p.mano_delante = lerp(p.mano_delante, (620, 260), max(mov, 0.6 * (1 - tramo(a, 7.25, 7.5))))
            p.mano_atras = lerp(p.mano_atras, (330, 300), max(mov, 0.6 * (1 - tramo(a, 7.25, 7.5))))
            p.sonrisa, p.mirada = 2.0, (0.0, 0.4)
            return self._rotar_pose(p, balanceo), None
        # 6) Baja, coge el martillo y refuerza el peldaño (refuerzo verde).
        golpe = (_x_riel(RIEL_D, PELDANOS_Y[TORCIDO]) + 8, PELDANOS_Y[TORCIDO] + 4)
        arriba, ang_a = self._martillo_clave(golpe, "arriba")
        abajo, ang_b = self._martillo_clave(golpe, "golpe")
        reb, ang_r = self._martillo_clave(golpe, "rebote")
        if a < 7.75:
            p = self._trepando(self._nivel(a))
            p.sonrisa = 0.6
            return p, None
        if a < 7.95:
            u = suave(tramo(a, 7.75, 7.95))
            base = self._de_pie(650, agachado=36)
            base.mano_delante = arriba
            return pj.mezclar(self._trepando(0.0), base, u), (ang_a if u > 0.5 else None)
        c0, c1 = T_ARREGLO
        if a < 8.6:
            claves = [(7.95, arriba), (c0 - 0.1, arriba), (c0, abajo), (c0 + 0.1, reb), (c1 - 0.12, arriba),
                      (c1, abajo), (c1 + 0.12, reb), (8.6, (620, 660))]
            angs = [(7.95, ang_a), (c0 - 0.1, ang_a), (c0, ang_b), (c0 + 0.1, ang_r), (c1 - 0.12, ang_a),
                    (c1, ang_b), (c1 + 0.12, ang_r), (8.6, -20.0)]
            p = self._de_pie(650, agachado=lerp(36, 0, tramo(a, 8.45, 8.6)), mirada=(-0.7, 0.2))
            p.mano_delante = pista(a, claves, curva=lambda u: u)
            return p, pista(a, angs, curva=lambda u: u)
        # 7) Vuelve a subir, ahora hasta arriba del todo.
        if a < PASOS_2[0]:
            u = suave(tramo(a, 8.6, PASOS_2[0]))
            return pj.mezclar(self._de_pie(650, mira=1), self._trepando(0.0), u), None
        if a < T_DING:
            return self._trepando(self._nivel(a)), None
        # 8) Arriba: señala las estrellas, feliz. Queda quieto desde a = 10.2.
        p = self._trepando(float(NIVEL_FINAL))
        u = suave(tramo(a, T_DING, 10.2))
        p.mano_delante = lerp(p.mano_delante, (650, 170), u)
        p.mirada = lerp((0.6, -0.6), (1.0, -0.5), u)
        p.sonrisa = lerp(1.0, 1.15, u)
        p.cabeza = lerp(0.0, -8.0, u)
        return p, None

    def _martillo_suelo(self, lz: Lienzo, a: float, en_mano: bool):
        if en_mano or a < 5.8:
            return
        pj.martillo(lz, (668, SUELO - 14), 90, largo=66)

    def _escalera(self, lz: Lienzo, a: float):
        balanceo = self._balanceo(a)

        def R(p):
            return rotar(p, BASE, balanceo)

        puestas = sum(1 for t in self.t_golpe if a >= t - 0.1)
        piezas = self._piezas()
        for i, (c, largo, grosor, vertical, _) in enumerate(piezas):
            if i >= puestas:
                continue
            if vertical:
                riel = RIEL_I if i == 0 else RIEL_D
                ang = math.degrees(math.atan2(riel[1][1] - riel[0][1], riel[1][0] - riel[0][0]))
            else:
                j = i - 2
                ang = self._torcido(a) if j == TORCIDO else INCLINACION_FIJA[j]
            self._tabla(lz, R(c), largo, grosor, ang + balanceo, semilla=400 + i)
        self._refuerzo(lz, a, R)
        for i, (c, largo, grosor, vertical, _) in enumerate(piezas):
            t0, t1 = self.t_vuelo[i]
            self._tabla_volando(lz, a, t0, t1, i, c, largo, grosor, vertical)
        for i, tg in enumerate(list(self.t_golpe) + list(T_ARREGLO)):
            if tg <= a < tg + 0.16:
                golpe = piezas[i][4] if i < len(piezas) else (_x_riel(RIEL_D, PELDANOS_Y[TORCIDO]) + 8,
                                                               PELDANOS_Y[TORCIDO] + 4)
                self._chispas(lz, golpe, tramo(a, tg, tg + 0.16))

    def _refuerzo(self, lz: Lienzo, a: float, R):
        """Pequeño refuerzo verde bajo el peldaño torcido (el arreglo imperfecto)."""
        c0 = T_ARREGLO[0]
        if a < c0 - 0.2:
            return
        u = sale(tramo(a, c0 - 0.2, c0 - 0.05))
        y = PELDANOS_Y[TORCIDO]
        xd = _x_riel(RIEL_D, y)
        p0, p1 = (xd - 44, y + 9), (xd - 3, y + 46)
        dx = lerp(80, 0, u)
        pts = [(p0[0] + dx, p0[1]), (p1[0] + dx, p1[1]), (p1[0] + dx - 9, p1[1] + 7), (p0[0] + dx - 9, p0[1] + 7)]
        lz.poligono([R(p) for p in pts], relleno=mezcla(fondo(), VERDE, 0.35), borde=VERDE, ancho=3)

    def _panel_hacedor(self, lz: Lienzo, a: float):
        caida, aplasta = self._caida_pila(a)
        quitar = sum(1 for (t0, _) in self.t_vuelo if a >= t0)
        self._pila(lz, (PILA_H[0], PILA_H[1] + aplasta), self.n_tablas, caida, quitar)
        pose, ang = self._hacedor(a)
        self._martillo_suelo(lz, a, ang is not None)
        self._escalera(lz, a)

        def en_mano(lz2, e):
            if ang is not None:
                pj.martillo(lz2, e["mano_d"], ang)

        pj.dibujar(lz, pose, perfeccionista=False, en_mano=en_mano)
        self._check(lz, a, (960, 330), T_DING)

    # ================================================================== AUDIO
    def eventos_hacedor(self):
        R = self.real
        ev = [(R(tg), "martillo", 0.85, -0.25, {"semilla": i}) for i, tg in enumerate(self.t_golpe)]
        pasos = [PASOS_1[0] + (PASOS_1[1] - PASOS_1[0]) * (k + 0.4) / 3 for k in range(3)]
        pasos += [PASOS_2[0] + (PASOS_2[1] - PASOS_2[0]) * (k + 0.4) / NIVEL_FINAL for k in range(NIVEL_FINAL)]
        ev += [(R(t), "crujido", 0.25, -0.2, {"semilla": 5 + k}) for k, t in enumerate(pasos)]
        ev.append((R(T_TAMBALEO[0]), "crujido", 0.75, -0.25, {"semilla": 1}))
        ev.append((R(T_TAMBALEO[0] + 0.3), "crujido", 0.45, -0.25, {"semilla": 2}))
        ev += [(R(t), "martillo", 0.75, -0.25, {"semilla": 9}) for t in T_ARREGLO]
        ev.append((R(T_DING), "ding", 0.9, -0.15, {}))
        return ev
