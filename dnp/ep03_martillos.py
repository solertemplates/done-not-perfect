"""Episodio 3: "Los dos martillos".

Primer episodio con OBJETOS con vida como personajes (ver `objetos.py`).
Una sola escena: una mesa de taller bajo una lámpara. A la izquierda, el
martillo Hacedor clava rápido (toc toc toc), endereza un clavo torcido y
termina una caja. A la derecha, el martillo Perfeccionista (gafas y regla)
mide el clavo, lo saca, lo vuelve a medir y lo pone otra vez, duda con el
martillo en alto y acaba suspirando.
"""
from __future__ import annotations

import math

from PIL import Image

from . import decorado as dec
from .lienzo import BLANCO, ESCALA, ROJO, TINTA, Lienzo, fondo, rotar, tenue
from .motor import EpisodioMotor
from .objetos import (CARA_GOLPEO, Clave, EstadoObjeto, Expresion, PistaObjeto, martillo,
                      mezclar_expresion)
from .tiempo import lerp, limitar, oscila, pulso, rebote, sale, suave, tramo

MESA = 1250  # altura del tablero
TAM = 1.25  # tamaño de los martillos (son los protagonistas: que destaquen)
TECHO = 205
VENTANA = (96, 262, 266, 402)
LAMPARA_X = 540

# --- Caja del Hacedor (izquierda) ---------------------------------------------
TABLA_H = (130, MESA - 28, 410, MESA)  # tabla inicial: será la base de la caja
TABLA_P = (600, MESA - 28, 880, MESA)  # tabla del Perfeccionista (igual)
# Piezas en orden de montaje: (rectángulo, clavo)
PIEZAS = [
    ((118, 1112, 138, MESA), (128, 1112)),  # poste izquierdo
    ((402, 1112, 422, MESA), (412, 1112)),  # poste derecho
    ((130, 1190, 410, 1218), (392, 1190)),  # listón 2
    ((130, 1158, 410, 1186), (392, 1158)),  # listón 3 (el del clavo torcido)
    ((130, 1126, 410, 1154), (392, 1126)),  # listón 4 (tapa)
]
T_PIEZA = [0.6, 1.5, 2.4, 3.3, 5.1]
TOCS = [[0.85, 1.0, 1.15], [1.75, 1.9, 2.05], [2.65, 2.8, 2.95], [3.55, 3.7, 4.6, 4.75], [5.35, 5.5, 5.65]]
ALTURAS = [[27, 13, 0], [27, 13, 0], [27, 13, 0], [27, 27, 13, 0], [27, 13, 0]]  # clavo visible tras cada toc
TORCIDO = 3  # pieza cuyo clavo se tuerce
T_TUERCE, T_ENDEREZA = 3.7, 4.35
DOBLEZ = 55.0
T_DING = 6.8
CHECK = (262, 1056)
CLAVOS_H = [170, 215, 260, 305, 350]  # clavos tumbados sobre la tabla inicial
REPOSO_H = (478, MESA)

# --- Perfeccionista (derecha) ---------------------------------------------------
CLAVO_P = (740, MESA - 28)  # donde entra el clavo en su tabla
CLAVOS_P = [632, 668, 798, 832, 862]  # tumbados; el de 668 es el que usa
REPOSO_P = (905, MESA)
MANO_REGLA_REPOSO = (850, 1172)
MANO_CLAVO_REPOSO = (884, 1214)
REGLA_LARGO = 120
T_COLOCA = (0.3, 0.6)
CICLOS = (0.6, 7.2)
T_DUDA = (7.2, 8.6)
T_SUSPIRO = (8.8, 9.8)
T_MIRA_FINAL = (9.8, 10.4)
T_ROJO = 9.0


def _clavo(lz: Lienzo, base, alto, doblez=0.0, color=BLANCO):
    """Clavo clavado en `base` del que asoman `alto` px; la mitad de arriba puede estar doblada."""
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


def _punta_clavo(base, alto, doblez):
    mitad = (base[0], base[1] - alto / 2)
    return rotar((mitad[0], mitad[1] - alto / 2), mitad, -doblez)


def _clavo_tumbado(lz: Lienzo, x, y):
    lz.linea([(x - 17, y), (x + 15, y)], 4, BLANCO)
    lz.linea([(x - 17, y - 6), (x - 17, y + 6)], 4, BLANCO)


def _regla(lz: Lienzo, centro, largo=REGLA_LARGO):
    x, y = centro
    lz.poligono([(x - 8, y - largo / 2), (x + 8, y - largo / 2), (x + 8, y + largo / 2), (x - 8, y + largo / 2)],
                relleno=BLANCO)
    for j in range(1, int(largo // 12)):
        yy = y - largo / 2 + j * 12
        lz.linea([(x - 8, yy), (x - (1 if j % 5 else -3), yy)], 1.6, TINTA, puntas=False)


class EpisodioMartillos(EpisodioMotor):
    POS_GANCHO = "arriba"
    Y_TARJETA = 1515  # el cartel final va sobre las patas de la mesa, sin tapar a los martillos

    # =============================================================== PREPARAR
    def _preparar(self):
        self.incl_tapa = float(self.ep["hacedor"]["inclinacion_tapa_grados"])
        self.intentos = self.ep["perfeccionista"]["intentos"]
        self.hacedor = martillo(tam=TAM)
        self.perfeccionista = martillo(gafas=True, brazos=True, tam=TAM)
        self.perfeccionista.brazo = (92.0, 88.0)
        self.pista_h = PistaObjeto(self._claves_hacedor())

    @staticmethod
    def _golpe(clavo, espejo, angulo, **kw) -> EstadoObjeto:
        """Estado en el que la cara de golpeo del martillo toca `clavo`."""
        sx, sy = kw.get("escala", (1.0, 1.0))
        f = ((-CARA_GOLPEO[0] if espejo else CARA_GOLPEO[0]) * TAM * sx, CARA_GOLPEO[1] * TAM * sy)
        rf = rotar(f, (0, 0), angulo)
        return EstadoObjeto(pos=(clavo[0] - rf[0], clavo[1] - rf[1]), angulo=angulo, espejo=espejo, **kw)

    def _claves_hacedor(self):
        reposo0 = EstadoObjeto(pos=REPOSO_H, angulo=0.0, espejo=True)
        claves = [Clave(0.0, reposo0), Clave(0.3, reposo0),
                  Clave(0.45, EstadoObjeto(pos=REPOSO_H, escala=(1.05, 0.93), espejo=True))]
        for i, ((_, clavo), tocs) in enumerate(zip(PIEZAS, TOCS)):
            espejo = clavo[0] < 300
            ang = -70.0 if espejo else 70.0
            atras = 55.0 if espejo else -55.0
            golpe = self._golpe(clavo, espejo, ang, escala=(1.03, 0.96))
            arriba = EstadoObjeto(pos=golpe.pos, angulo=ang + atras, espejo=espejo)
            rebote_ = EstadoObjeto(pos=golpe.pos, angulo=ang + atras * 0.3, espejo=espejo)
            claves.append(Clave(T_PIEZA[i] - 0.05, arriba, salto=60))
            for tau in tocs:
                if i == TORCIDO and tau > T_TUERCE:
                    continue
                claves += [Clave(tau - 0.07, arriba, "sale"), Clave(tau, golpe, "golpe"),
                           Clave(tau + 0.05, rebote_, "sale")]
            if i == TORCIDO:
                # El clavo se tuerce: retrocede sorprendido, luego lo endereza de un toque.
                sorpresa = EstadoObjeto(pos=golpe.pos, angulo=ang + atras * 1.05, espejo=espejo)
                claves += [Clave(3.8, sorpresa, "sale"), Clave(4.15, sorpresa)]
                punta = _punta_clavo(clavo, ALTURAS[i][1], DOBLEZ)
                g2 = self._golpe(punta, False, 85.0, escala=(1.03, 0.96))
                a2 = EstadoObjeto(pos=g2.pos, angulo=85.0 - 45.0, espejo=False)
                claves += [Clave(4.27, a2, salto=30), Clave(T_ENDEREZA, g2, "golpe"),
                           Clave(T_ENDEREZA + 0.07, a2, "sale")]
                for tau in tocs[2:]:
                    claves += [Clave(tau - 0.07, arriba, "sale"), Clave(tau, golpe, "golpe"),
                               Clave(tau + 0.05, rebote_, "sale")]
        final = EstadoObjeto(pos=REPOSO_H, angulo=-9.0, espejo=True)
        claves += [Clave(6.3, final, salto=70), Clave(11.0, final)]
        return claves

    # ============================================================== DECORADO
    def _decorado(self) -> Image.Image:
        img = Image.new("RGB", (self.ancho * ESCALA, self.alto * ESCALA), fondo())
        lz = Lienzo(img)
        lz = dec.lampara(img, lz, LAMPARA_X, 330, 0, semilla=120, techo=TECHO, y_suelo=MESA,
                         ancho_suelo=860, ancho_boca=70)
        linea, suave_c = tenue(0.72), tenue(0.38)
        lz.boceto((0, TECHO), (1080, TECHO), 2.0, suave_c, semilla=121, doble=False)
        self.estrellas = dec.ventana(lz, VENTANA, panel=0, semilla=130, densidad=1.8)
        # Mesa de taller: tablero, patas, balda y suelo.
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
        # Cosas en la balda: una caja de clavos y un trapo.
        lz.boceto_poli([(240, 1612), (240, 1560), (360, 1560), (360, 1612)], 1.8, suave_c, semilla=190)
        lz.boceto((700, 1600), (820, 1606), 1.6, suave_c, semilla=191, doble=False)
        return img

    # ================================================================ HACEDOR
    def _expresion_h(self, a: float) -> Expresion:
        trabajo = Expresion(cejas=1.0, sonrisa=0.5, mirada=(-0.6, 0.5))
        sorpresa = Expresion(cejas=-0.6, sonrisa=2.0, mirada=(0.0, 0.7))
        enfado = Expresion(cejas=1.3, sonrisa=0.1, mirada=(0.0, 0.7))
        feliz = Expresion(ojos_felices=1.0, sonrisa=1.2)
        mira_al_otro = Expresion(sonrisa=0.9, mirada=(1.0, 0.1))
        if a < T_TUERCE + 0.02:
            e = trabajo
        elif a < 4.15:
            e = sorpresa
        elif a < 4.5:
            e = mezclar_expresion(sorpresa, enfado, suave(tramo(a, 4.15, 4.25)))
        elif a < 6.3:
            e = trabajo
        elif a < 8.2:
            e = mezclar_expresion(trabajo, feliz, suave(tramo(a, 6.3, T_DING)))
        elif a < 9.4:
            e = mezclar_expresion(feliz, mira_al_otro, suave(tramo(a, 8.2, 8.5)))
        else:
            e = mezclar_expresion(mira_al_otro, feliz, suave(tramo(a, 9.4, 9.8)))
        e.parpado = max(pulso(a, 2.3, 0.16), pulso(a, 5.9, 0.16)) if e.ojos_felices < 0.5 else 0.0
        return e

    def _estado_h(self, a: float) -> EstadoObjeto:
        est = self.pista_h.en(a)
        est.expresion = self._expresion_h(a)
        # Dos saltitos de alegría tras el "ding".
        bote = abs(math.sin(math.pi * 2 * tramo(a, T_DING, T_DING + 0.7))) * 18 * (1 - tramo(a, T_DING, T_DING + 0.7))
        if bote:
            est.pos = (est.pos[0], est.pos[1] - bote)
        return est

    def _altura_clavo(self, i: int, a: float):
        """(alto visible, doblez) del clavo de la pieza i."""
        alto = 40.0
        for tau, h in zip(TOCS[i], ALTURAS[i]):
            if a >= tau:
                alto = h
        doblez = 0.0
        if i == TORCIDO:
            doblez = DOBLEZ * sale(tramo(a, T_TUERCE, T_TUERCE + 0.06)) * (1 - tramo(a, T_ENDEREZA, T_ENDEREZA + 0.05))
        return alto, doblez

    def _caja(self, lz: Lienzo, a: float):
        tabla_base = ((TABLA_H[0] + TABLA_H[2]) / 2, (TABLA_H[1] + TABLA_H[3]) / 2)
        dec.tabla(lz, tabla_base, TABLA_H[2] - TABLA_H[0], 28, 0, semilla=600)
        for i, x in enumerate(CLAVOS_H):
            if a < T_PIEZA[i]:
                _clavo_tumbado(lz, x, MESA - 34)
        orden = [2, 3, 4, 0, 1]  # listones detrás, postes delante
        for i in orden:
            if a < T_PIEZA[i]:
                continue
            (x0, y0, x1, y1), _ = PIEZAS[i]
            caida = -50 * (1 - rebote(tramo(a, T_PIEZA[i], T_PIEZA[i] + 0.18)))
            c = ((x0 + x1) / 2, (y0 + y1) / 2 + caida)
            vertical = (y1 - y0) > (x1 - x0)
            largo, grosor = (y1 - y0, x1 - x0) if vertical else (x1 - x0, y1 - y0)
            ang = 90.0 if vertical else (self.incl_tapa if i == 4 else 0.0)
            dec.tabla(lz, c, largo, grosor, ang, semilla=610 + i)
        for i, (_, clavo) in enumerate(PIEZAS):
            if a < T_PIEZA[i]:
                continue
            alto, doblez = self._altura_clavo(i, a)
            caida = -50 * (1 - rebote(tramo(a, T_PIEZA[i], T_PIEZA[i] + 0.18)))
            base = (clavo[0], clavo[1] + caida + (math.tan(math.radians(self.incl_tapa)) * (clavo[0] - 270)
                                                  if i == 4 else 0))
            _clavo(lz, base, alto, doblez)
        # Chispitas de cada toc.
        for i, tocs in enumerate(TOCS):
            for tau in tocs + ([T_ENDEREZA] if i == TORCIDO else []):
                if tau <= a < tau + 0.12:
                    u = tramo(a, tau, tau + 0.12)
                    c = PIEZAS[i][1]
                    for k in range(4):
                        ang = math.radians(20 + k * 47)
                        r0, r1 = 14 + 22 * u, 26 + 30 * u
                        lz.linea([(c[0] + math.cos(ang) * r0, c[1] - math.sin(ang) * r0),
                                  (c[0] + math.cos(ang) * r1, c[1] - math.sin(ang) * r1)], 3.5 * (1 - u) + 1)

    # ========================================================= PERFECCIONISTA
    def _fase_p(self, a: float):
        if a < T_COLOCA[0]:
            return "espera", tramo(a, 0, T_COLOCA[0]), 0
        if a < T_COLOCA[1]:
            return "coloca", tramo(a, *T_COLOCA), 0
        if a < CICLOS[1]:
            L = (CICLOS[1] - CICLOS[0]) / self.intentos
            k = min(int((a - CICLOS[0]) // L), self.intentos - 1)
            u = (a - CICLOS[0] - k * L) / L
            for nombre, f0, f1 in (("mide", 0.0, 0.28), ("saca", 0.28, 0.45), ("mide2", 0.45, 0.70),
                                   ("pone", 0.70, 0.86), ("pausa", 0.86, 1.0)):
                if u < f1:
                    return nombre, (u - f0) / (f1 - f0), k
        if a < T_DUDA[1]:
            return "duda", tramo(a, *T_DUDA), self.intentos
        if a < T_SUSPIRO[0]:
            return "quieto", 0.0, self.intentos
        if a < T_SUSPIRO[1]:
            return "suspira", tramo(a, *T_SUSPIRO), self.intentos
        return "final", tramo(a, *T_MIRA_FINAL), self.intentos

    def tiempos_p(self):
        """Instantes (unidades de acción) para el audio del Perfeccionista."""
        L = (CICLOS[1] - CICLOS[0]) / self.intentos
        ciclos = []
        for k in range(self.intentos):
            c = CICLOS[0] + k * L
            ciclos.append(dict(mide=c + 0.05 * L, saca=c + 0.34 * L, mide2=c + 0.48 * L, pone=c + 0.84 * L))
        return ciclos

    def _estado_p(self, a: float):
        """Devuelve (estado, posición del clavo: ('tabla', alto) o ('mano', punto), regla_centro)."""
        fase, u, k = self._fase_p(a)
        base_ang = -8.0
        expr = Expresion(cejas=-1.0, sonrisa=0.2, mirada=(-0.8, 0.5))
        expr.parpado = max(pulso(a, 2.0, 0.16), pulso(a, 6.4, 0.16))
        mano_regla, mano_clavo = MANO_REGLA_REPOSO, MANO_CLAVO_REPOSO
        regla_mide_tabla = (CLAVO_P[0] + 22, CLAVO_P[1] - REGLA_LARGO / 2)
        regla_mide_aire = (CLAVO_P[0] + 22, CLAVO_P[1] - 112)
        clavo_aire = (CLAVO_P[0], CLAVO_P[1] - 128)  # cabeza del clavo cuando lo sostiene en alto
        clavo = ("tabla", 20.0)
        ang, escala, elevacion = base_ang, (1.0, 1.0), 0.0
        if fase == "espera":
            clavo = ("tumbado", None)
            expr.mirada = (-0.6, 0.8)
        elif fase == "coloca":
            tumbado = (CLAVOS_P[1], MESA - 34)
            if u < 0.4:
                mano_clavo = lerp(MANO_CLAVO_REPOSO, tumbado, suave(u / 0.4))
                clavo = ("tumbado", None)
            elif u < 0.85:
                v = suave((u - 0.4) / 0.45)
                mano_clavo = lerp(tumbado, (CLAVO_P[0], CLAVO_P[1] - 60), v)
                clavo = ("mano", mano_clavo)
            else:
                mano_clavo = lerp((CLAVO_P[0], CLAVO_P[1] - 30), MANO_CLAVO_REPOSO, suave((u - 0.85) / 0.15))
                clavo = ("tabla", 20.0)
        elif fase == "mide":
            mano_regla = lerp(MANO_REGLA_REPOSO, regla_mide_tabla, suave(tramo(u, 0, 0.3)))
            expr.parpado = 0.45
            ang = base_ang - 4 * suave(tramo(u, 0, 0.3)) + 1.5 * oscila(u, 1.0)
        elif fase == "saca":
            mano_regla = lerp(regla_mide_tabla, MANO_REGLA_REPOSO, suave(tramo(u, 0, 0.45)))
            cabeza = (CLAVO_P[0], CLAVO_P[1] - 20)
            if u < 0.35:
                mano_clavo = lerp(MANO_CLAVO_REPOSO, cabeza, suave(u / 0.35))
            else:
                mano_clavo = lerp(cabeza, clavo_aire, sale((u - 0.35) / 0.65))
                clavo = ("mano", mano_clavo)
        elif fase == "mide2":
            mano_clavo = clavo_aire
            clavo = ("mano", clavo_aire)
            mano_regla = lerp(MANO_REGLA_REPOSO, regla_mide_aire, suave(tramo(u, 0, 0.3)))
            expr.parpado = 0.45
            expr.mirada = (-0.8, -0.2)
            ang = base_ang - 3 + 1.5 * oscila(u, 1.5)
        elif fase == "pone":
            mano_regla = lerp(regla_mide_aire, MANO_REGLA_REPOSO, suave(tramo(u, 0, 0.4)))
            mano_clavo = lerp(clavo_aire, (CLAVO_P[0], CLAVO_P[1] - 20), suave(u))
            clavo = ("mano", mano_clavo) if u < 0.98 else ("tabla", 20.0)
        elif fase == "pausa":
            mano_clavo = lerp((CLAVO_P[0], CLAVO_P[1] - 20), MANO_CLAVO_REPOSO, suave(u))
        elif fase == "duda":
            # Levanta el martillo, duda... y lo baja sin golpear.
            sube = suave(tramo(u, 0, 0.28))
            baja = suave(tramo(u, 0.72, 1.0))
            arriba = sube * (1 - baja)
            ang = base_ang + 12 * arriba
            elevacion = 50 * arriba  # se despega de la mesa: "levanta el martillo"
            if 0.28 <= u < 0.72:
                ang += 3 * oscila(tramo(u, 0.28, 0.72), 3.0)
            expr.cejas = -1.0
            expr.sonrisa = lerp(0.2, -0.3, sube)
            expr.mirada = (-1.0, 0.7)
        elif fase in ("quieto", "suspira", "final"):
            v = 1.0 if fase == "final" else (suave(u) if fase == "suspira" else 0.0)
            ang = base_ang - 5 * v
            escala = (1.0 + 0.02 * v, 1.0 - 0.05 * v)
            expr.sonrisa = lerp(0.2, -0.7, v)
            expr.parpado = lerp(0.0, 0.5, v)
            if fase == "final":
                mano_regla = lerp(MANO_REGLA_REPOSO, regla_mide_tabla, suave(u))
                expr.mirada = (-0.9, 0.6)
        est = EstadoObjeto(pos=(REPOSO_P[0], REPOSO_P[1] - elevacion), angulo=ang, escala=escala, espejo=True, expresion=expr,
                           manos=(mano_regla, mano_clavo))
        regla = mano_regla
        return est, clavo, regla

    def _panel_p(self, lz: Lienzo, a: float):
        c = ((TABLA_P[0] + TABLA_P[2]) / 2, (TABLA_P[1] + TABLA_P[3]) / 2)
        dec.tabla(lz, c, TABLA_P[2] - TABLA_P[0], 28, 0, semilla=600)
        est, clavo, _ = self._estado_p(a)
        for j, x in enumerate(CLAVOS_P):
            if j == 1 and clavo[0] != "tumbado":
                continue
            _clavo_tumbado(lz, x, MESA - 34)
        if clavo[0] == "tabla":
            _clavo(lz, CLAVO_P, clavo[1])
        # Detalle rojo: el clavo a medio poner.
        if a >= T_ROJO:
            s = rebote(tramo(a, T_ROJO, T_ROJO + 0.3), 2.0)
            centro = (CLAVO_P[0], CLAVO_P[1] - 14)
            for j in range(10):
                a0 = 2 * math.pi * j / 10
                a1 = a0 + 2 * math.pi / 20
                r = 30 * s
                lz.linea([(centro[0] + r * math.cos(a0), centro[1] + r * math.sin(a0)),
                          (centro[0] + r * math.cos(a1), centro[1] + r * math.sin(a1))], 3, ROJO)

        def en_mano(lz2, i, mano):
            if i == 0:
                _regla(lz2, mano)
            elif clavo[0] == "mano":
                p = clavo[1]
                _clavo(lz2, (p[0], p[1] + 40), 40)

        self.perfeccionista.dibujar(lz, est, en_mano=en_mano)
        # Soplido del suspiro.
        t0, t1 = T_SUSPIRO
        v = tramo(a, t0 + 0.1, t1 - 0.1)
        if 0 < v < 1:
            boca = self.perfeccionista._local_cara(est, 0, 16)
            for j in range(3):
                d = 26 + 50 * v + j * 12
                y = boca[1] + (j - 1) * 12 + 14 * v
                lz.linea([(boca[0] - d, y), (boca[0] - d - 28, y + 5)], 3, tenue(0.8 * (1 - v)))

    # ============================================================== FOTOGRAMA
    def _dibujar(self, img: Image.Image, a: float, fase_bucle: float):
        lz = Lienzo(img)
        dec.estrellas(lz, self.estrellas, 0, fase_bucle)
        self._caja(lz, a)
        self._panel_p(lz, a)
        self.hacedor.dibujar(lz, self._estado_h(a))
        dec.marca_ok(lz, a, CHECK, T_DING)

    # ================================================================== AUDIO
    def eventos_episodio(self):
        R = self.real
        ev = []
        for i, tocs in enumerate(TOCS):
            ev.append((R(T_PIEZA[i] + 0.1), "crujido", 0.2, -0.3, {"semilla": 10 + i}))
            for j, tau in enumerate(tocs):
                ev.append((R(tau), "martillo", 0.7, -0.3, {"semilla": i * 4 + j}))
        ev.append((R(T_TUERCE + 0.01), "clavo_torcido", 0.85, -0.3, {}))
        ev.append((R(T_ENDEREZA), "martillo", 0.55, -0.3, {"semilla": 30}))
        ev.append((R(T_DING), "ding", 0.9, -0.2, {}))
        ev.append((R(T_COLOCA[1] - 0.05), "bola", 0.35, 0.3, {}))
        for k, c in enumerate(self.tiempos_p()):
            ev.append((R(c["mide"]), "regla", 0.7, 0.3, {"semilla": k * 2}))
            ev.append((R(c["saca"]), "crujido", 0.25, 0.3, {"semilla": 20 + k}))
            ev.append((R(c["mide2"]), "regla", 0.7, 0.3, {"semilla": k * 2 + 1}))
            ev.append((R(c["pone"]), "bola", 0.35, 0.3, {}))
        ev.append((R(T_SUSPIRO[0]), "suspiro", 0.9, 0.25, {"dur": 1.1}))
        return ev

    # Útil para los tests.
    def estado_final_igual(self) -> bool:
        return self._fase_p(11.0)[0] == "final" and limitar(11.0, 0, 11) == 11.0
