"""Objetos con vida: cualquier forma puede ser un personaje.

Un `ObjetoVivo` es una silueta BLANCA (polígonos y círculos en coordenadas
locales) con una cara simple de puntos y sonrisa, como la de los muñequitos.
Puede tener brazos finos opcionales para sujetar cosas.

Coordenadas locales: el origen es el punto de apoyo (por ejemplo, la punta del
mango de un martillo); el eje y apunta hacia abajo, como en la pantalla.

Para crear un personaje nuevo basta con definir su forma, dónde va la cara y,
si los tiene, dónde nacen los brazos (ver `martillo()` como ejemplo).

    obj = martillo(gafas=True)
    obj.dibujar(lz, EstadoObjeto(pos=(500, 1250), angulo=-8, expresion=Expresion(sonrisa=1)))
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from .lienzo import BLANCO, TINTA, Lienzo, rotar
from .personajes import _ik


@dataclass
class Expresion:
    sonrisa: float = 1.0  # 1 sonrisa, 0 recta, -1 triste, 2 boca abierta "¡O!"
    parpado: float = 0.0  # 0 ojos abiertos, 1 cerrados
    mirada: tuple[float, float] = (0.0, 0.0)  # pupilas, de -1 a 1
    cejas: float = 0.0  # +1 decidido (bajan hacia el centro), -1 preocupado, 0 sin cejas
    ojos_felices: float = 0.0  # 1 = ojos en arco "^^"


@dataclass
class EstadoObjeto:
    pos: tuple[float, float]  # dónde cae el origen local en el panel
    angulo: float = 0.0  # grados, positivo = giro en el sentido de las agujas del reloj
    escala: tuple[float, float] = (1.0, 1.0)  # estirar / aplastar (squash & stretch)
    espejo: bool = False  # mirar hacia el otro lado
    expresion: Expresion = field(default_factory=Expresion)
    manos: tuple = ()  # destino de cada brazo en coordenadas del panel (None = brazo colgando)


@dataclass
class Forma:
    tipo: str  # "poligono" | "circulo" | "linea"
    puntos: list  # polígono/línea: lista de puntos; círculo: [centro]
    radio: float = 0.0
    ancho: float = 0.0
    color: tuple = BLANCO


@dataclass
class ObjetoVivo:
    formas: list[Forma]
    cara: tuple[float, float]  # centro de la cara (local)
    tam_cara: float = 1.0  # 1 = ojos separados 36 px
    gafas: bool = False
    hombros: list = field(default_factory=list)  # origen local de cada brazo
    brazo: tuple[float, float] = (70.0, 66.0)
    tam: float = 1.0  # tamaño global del personaje (1 = como está definido)

    # ------------------------------------------------------------ transformación
    def a_panel(self, est: EstadoObjeto, p):
        sx, sy = est.escala
        x, y = p[0] * sx * self.tam, p[1] * sy * self.tam
        if est.espejo:
            x = -x
        x, y = rotar((x, y), (0, 0), est.angulo)
        return (est.pos[0] + x, est.pos[1] + y)

    def angulo_cara(self, est: EstadoObjeto) -> float:
        return est.angulo

    # -------------------------------------------------------------------- dibujo
    def dibujar(self, lz: Lienzo, est: EstadoObjeto, en_mano=None):
        """Dibuja brazo trasero, cuerpo, cara y brazo delantero.

        `en_mano(lz, i, mano)` dibuja lo que sujeta el brazo i (por ejemplo, una regla).
        """
        manos = self._brazos(est)
        for i, (hombro, codo, mano) in enumerate(manos):
            if i == 0:
                lz.linea([hombro, codo, mano], 6 * self.tam, BLANCO)
                if en_mano:
                    en_mano(lz, i, mano)
        for f in self.formas:
            pts = [self.a_panel(est, p) for p in f.puntos]
            if f.tipo == "poligono":
                lz.poligono(pts, relleno=f.color)
            elif f.tipo == "circulo":
                lz.circulo(pts[0], f.radio * max(est.escala) * self.tam, relleno=f.color)
            elif f.tipo == "linea":
                lz.linea(pts, f.ancho * self.tam, f.color)
        self._dibujar_cara(lz, est)
        for i, (hombro, codo, mano) in enumerate(manos):
            if i > 0:
                if en_mano:
                    en_mano(lz, i, mano)
                lz.linea([hombro, codo, mano], 6 * self.tam, BLANCO)
        return manos

    def _brazos(self, est: EstadoObjeto):
        out = []
        for i, h in enumerate(self.hombros):
            hombro = self.a_panel(est, h)
            destino = est.manos[i] if i < len(est.manos) and est.manos[i] is not None else None
            if destino is None:  # brazo relajado, colgando junto al cuerpo
                destino = self.a_panel(est, (h[0] + (14 if h[0] >= 0 else -14), h[1] + sum(self.brazo) * 0.9))
            lado = 1 if (destino[0] >= hombro[0]) != est.espejo else -1
            codo, mano = _ik(hombro, destino, self.brazo[0] * self.tam, self.brazo[1] * self.tam, lado)
            out.append((hombro, codo, mano))
        return out

    def _local_cara(self, est: EstadoObjeto, x, y):
        s = self.tam_cara  # a_panel ya aplica `tam`
        return self.a_panel(est, (self.cara[0] + x * s, self.cara[1] + y * s))

    def _dibujar_cara(self, lz: Lienzo, est: EstadoObjeto):
        ex = est.expresion
        s = self.tam_cara * self.tam  # grosor de los trazos
        L = lambda x, y: self._local_cara(est, x, y)  # noqa: E731
        mx, my = ex.mirada
        for lado in (-1, 1):
            ox, oy = 18 * lado, -6
            if ex.ojos_felices > 0.5:
                pts = [L(ox + 8 * math.cos(math.radians(a)), oy + 2 - 7 * math.sin(math.radians(a)))
                       for a in range(0, 181, 30)]
                lz.linea(pts, 4 * s, TINTA)
            elif ex.parpado > 0.6:
                lz.linea([L(ox - 7, oy), L(ox + 7, oy)], 4 * s, TINTA)
            else:
                lz.circulo(L(ox + 3 * mx, oy + 3 * my), 5.2 * s * (1 - ex.parpado * 0.5), relleno=TINTA)
            if self.gafas:
                lz.circulo(L(ox, oy), 12.5 * s, borde=TINTA, ancho=3.2 * s)
            if ex.cejas:
                # Decidido: cejas que bajan hacia el centro. Preocupado: suben hacia el centro.
                d = 5 * ex.cejas
                lz.linea([L(ox - 9 * lado * -1, oy - 15 - d), L(ox - 9 * lado, oy - 15 + d)], 3.6 * s, TINTA)
        if self.gafas:
            lz.linea([L(-5.5, -6), L(5.5, -6)], 3.2 * s, TINTA)
        sm = ex.sonrisa
        if sm > 1.2:
            lz.circulo(L(0, 16), 7 * s * min(1.0, sm - 1.0), relleno=TINTA)
            return
        pts = []
        for i in range(9):
            u = i / 8 * 2 - 1
            pts.append(L(u * 13, 13 + (1 - u * u) * 7 * sm))
        lz.linea(pts, 3.8 * s, TINTA)


def con_expresion(est: EstadoObjeto, **cambios) -> EstadoObjeto:
    return replace(est, expresion=replace(est.expresion, **cambios))


def _l(a, b, u):
    return a + (b - a) * u


def _p(a, b, u):
    return (_l(a[0], b[0], u), _l(a[1], b[1], u))


def mezclar_expresion(a: Expresion, b: Expresion, u: float) -> Expresion:
    return Expresion(sonrisa=_l(a.sonrisa, b.sonrisa, u), parpado=_l(a.parpado, b.parpado, u),
                     mirada=_p(a.mirada, b.mirada, u), cejas=_l(a.cejas, b.cejas, u),
                     ojos_felices=_l(a.ojos_felices, b.ojos_felices, u))


def mezclar_estado(a: EstadoObjeto, b: EstadoObjeto, u: float, salto: float = 0.0) -> EstadoObjeto:
    """Interpola dos estados. `salto` > 0 añade un arco hacia arriba (un saltito)."""
    pos = _p(a.pos, b.pos, u)
    if salto:
        pos = (pos[0], pos[1] - math.sin(math.pi * u) * salto)
    manos = tuple(
        (mb if ma is None else ma if mb is None else _p(ma, mb, u))
        for ma, mb in zip(a.manos, b.manos)
    ) if len(a.manos) == len(b.manos) else (a.manos if u < 0.5 else b.manos)
    return EstadoObjeto(pos=pos, angulo=_l(a.angulo, b.angulo, u), escala=_p(a.escala, b.escala, u),
                        espejo=a.espejo if u < 0.5 else b.espejo,
                        expresion=mezclar_expresion(a.expresion, b.expresion, u), manos=manos)


@dataclass
class Clave:
    t: float
    estado: EstadoObjeto
    curva: str = "suave"  # cómo se llega a esta clave: "suave", "lineal", "golpe" (acelera) o "sale"
    salto: float = 0.0  # arco del saltito al llegar a esta clave


_CURVAS = {
    "lineal": lambda u: u,
    "suave": lambda u: u * u * (3 - 2 * u),
    "golpe": lambda u: u * u,
    "sale": lambda u: 1 - (1 - u) ** 2,
}


class PistaObjeto:
    """Animación por claves de un objeto vivo: `pista.en(a)` devuelve su estado en el instante `a`."""

    def __init__(self, claves: list[Clave]):
        self.claves = sorted(claves, key=lambda c: c.t)

    def en(self, a: float) -> EstadoObjeto:
        c = self.claves
        if a <= c[0].t:
            return replace(c[0].estado)  # siempre una copia: quien la use puede modificarla sin estropear la pista
        for k0, k1 in zip(c, c[1:]):
            if a <= k1.t:
                u = 0.0 if k1.t == k0.t else (a - k0.t) / (k1.t - k0.t)
                return mezclar_estado(k0.estado, k1.estado, _CURVAS[k1.curva](min(1.0, max(0.0, u))), k1.salto)
        return replace(c[-1].estado)


# --- Catálogo de objetos -------------------------------------------------------

def martillo(gafas: bool = False, brazos: bool = False, tam: float = 1.0) -> ObjetoVivo:
    """Martillo de carpintero. Origen = punta del mango (apoyo en la mesa).

    La cabeza tiene la cara de golpeo a la derecha (x > 0) y la uña a la izquierda.
    """
    mango = Forma("poligono", [(-12, 0), (12, 0), (14, -212), (-14, -212)])
    pomo = Forma("circulo", [(0, -2)], radio=13)
    cuello = Forma("poligono", [(-20, -208), (20, -208), (24, -224), (-24, -224)])
    cabeza = Forma("poligono", [(-42, -222), (68, -222), (74, -228), (74, -278), (68, -284), (-42, -284)])
    # Uña curvada (lado izquierdo), en dos tramos.
    una = Forma("poligono", [(-42, -222), (-42, -284), (-70, -280), (-96, -262), (-86, -256), (-64, -266), (-48, -262)])
    hombros = [(-12, -150), (12, -150)] if brazos else []
    return ObjetoVivo([mango, pomo, cuello, una, cabeza], cara=(16, -252), tam_cara=1.0, gafas=gafas,
                      hombros=hombros, tam=tam)


CARA_GOLPEO = (74, -253)  # centro de la cara de golpeo del martillo (local)
