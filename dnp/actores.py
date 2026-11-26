"""Personajes y sus acciones, para usarlos desde el JSON ("personajes": [...]).

Dos clases de personaje:
* Muñecos de palo: "hacedor" y "perfeccionista" (gafas y lápiz en la oreja).
* Objetos con vida: "martillo_hacedor" y "martillo_perfeccionista".

Cada personaje tiene una lista de acciones con "desde_s" y "hasta_s" (segundos
del vídeo). Entre dos acciones el personaje ya está en la postura con la que
empieza la siguiente; después de la última se queda como acabó.
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, replace

from . import biblioteca as bib
from . import personajes as pj
from . import piezas as pz
from .lienzo import BLANCO, Lienzo, rotar, tenue
from .objetos import (CARA_GOLPEO, Clave, EstadoObjeto, Expresion, PistaObjeto, martillo,
                      mezclar_expresion)
from .personajes import Pose
from .tiempo import entra, lerp, limitar, oscila, pista, pulso, rebote, sale, suave, tramo

SUELO = pz.SUELO


@dataclass
class Cuerpo:
    """Estado de un muñeco en un instante."""
    pose: Pose
    martillo: float | None = None  # ángulo del martillo en la mano (None = no lo lleva)
    martillo_suelo: tuple | None = None  # martillo tirado en el suelo
    agarre: tuple | None = None  # mandarria en las manos
    angulo: float = 0.0
    suelo: tuple | None = None  # mandarria tirada: (agarre, ángulo)
    escala: float = 1.0
    subida: float = 0.0
    lapiz: bool = False
    goma: bool = False


def mezclar_cuerpo(a: Cuerpo, b: Cuerpo, u: float) -> Cuerpo:
    agarre = a.agarre if b.agarre is None else b.agarre if a.agarre is None else lerp(a.agarre, b.agarre, u)
    return replace(b, pose=pj.mezclar(a.pose, b.pose, u), agarre=agarre, angulo=lerp(a.angulo, b.angulo, u),
                   suelo=a.suelo if u < 0.5 else b.suelo, escala=lerp(a.escala, b.escala, u),
                   subida=lerp(a.subida, b.subida, u))


def martillo_clave(golpe, fase):
    """Mano y ángulo del martillo para golpear `golpe` (el muñeco mira a la izquierda)."""
    ang_g = -100.0
    d = (math.sin(math.radians(ang_g)), -math.cos(math.radians(ang_g)))
    mano = (golpe[0] - d[0] * 74, golpe[1] - d[1] * 74)
    if fase == "arriba":
        return (mano[0] + 30, mano[1] - 84), 25.0
    if fase == "rebote":
        return (mano[0] + 8, mano[1] - 22), -70.0
    return mano, ang_g


class Actor:
    """Línea de tiempo de acciones común a muñecos y objetos."""

    def __init__(self, conf: dict, indice: int, objetos: dict):
        self.conf = conf
        self.id = conf.get("id", conf["tipo"])
        self.indice = indice
        self.objetos = objetos
        self.acciones = conf["acciones"]
        self.parpadeos = conf.get("parpadeos_s", [])
        self.dx = conf.get("dx", 0)  # desplazamiento horizontal de todo el dibujo
        self._fin = {}

    def obj(self, ac, clave="objeto"):
        return self.objetos[ac[clave]]

    def parpado(self, ts):
        return max([0.0] + [pulso(ts, t, 0.16) for t in self.parpadeos])

    def _situacion(self, ts):
        """(índice de la acción, instante a evaluar)."""
        for i, ac in enumerate(self.acciones):
            if ts < ac["desde_s"]:
                return i, ac["desde_s"]
            if ts < ac["hasta_s"]:
                return i, ts
        return len(self.acciones) - 1, self.acciones[-1]["hasta_s"]

    def inicio(self, i):
        """Estado con el que acaba la acción anterior a la i (o el inicial)."""
        if i == 0:
            return self.estado_inicial()
        if i - 1 not in self._fin:
            ac = self.acciones[i - 1]
            self._fin[i - 1] = self._hacer(i - 1, ac["hasta_s"], ac["hasta_s"])
        return self._fin[i - 1]

    def estado(self, ts):
        i, t = self._situacion(ts)
        return self._hacer(i, t, ts)

    def accion_en(self, ts):
        return self.acciones[self._situacion(ts)[0]]

    def golpes_hasta(self, ts):
        return 0


# ================================================================== MUÑECOS
class Muneco(Actor):
    def __init__(self, conf, indice, objetos):
        super().__init__(conf, indice, objetos)
        self.perfeccionista = conf["tipo"] == "perfeccionista"
        self.herramienta = conf.get("herramienta", "ninguna")
        self.sentado_suelo = conf.get("postura", "de_pie") == "sentado_suelo"
        self.paneo = conf.get("paneo", 0.2 if self.perfeccionista else -0.2)
        self.golpes: list[float] = []
        roca = next((self.obj(ac) for ac in self.acciones if ac["accion"] == "golpear"), None)
        self.roca = roca
        if "x" in conf:
            self.x = conf["x"]
        elif roca is not None:
            self.x = roca.roca.arriba[0] - 274
        else:
            self.x = 400
        self._preparar_objetos()

    # ------------------------------------------------------------ preparación
    def _preparar_objetos(self):
        hojas = 0
        self.plano = None
        for ac in self.acciones:
            a = ac["accion"]
            if a == "construir":
                obra = self.obj(ac)
                obra.t_golpe = [ac["primer_golpe_s"] + ac["cada_s"] * i for i in range(len(obra.partes()))]
                obra.vuelo_s = ac.get("vuelo_s", obra.vuelo_s)
                if ac.get("madera"):
                    obra.pila = self.objetos[ac["madera"]]
                    obra.pila.vuelos = [t - obra.vuelo_s for t in obra.t_golpe]
            elif a == "tambalearse":
                self.obj(ac).tambaleo = (ac["desde_s"], ac["hasta_s"])
            elif a == "martillear" and ac.get("arregla"):
                self.obj(ac, "arregla").arreglo = tuple(ac["golpes_s"])
            elif a == "golpear":
                instantes = self.instantes_golpe(ac)
                self.golpes += instantes
                self.obj(ac).golpes += instantes
                self.obj(ac).paneo = self.paneo
            elif a in ("dibujar", "medir", "borrar", "arrugar"):
                self.plano = self.obj(ac, "plano")
                self.plano.usuario = self
                if a == "arrugar":
                    hojas += 1
        if self.plano is not None:
            self.plano.preparar(hojas)
        self.hoja = []
        k = 0
        for ac in self.acciones:
            self.hoja.append(k)
            if ac["accion"] == "arrugar":
                k += 1
        for o in self.objetos.values():
            if isinstance(o, pz.Contador) and o.conf.get("de") == self.id:
                o.de = self

    @staticmethod
    def instantes_golpe(ac):
        d, h, n = ac["desde_s"], ac["hasta_s"], ac["golpes"]
        if ac["velocidad"] == "lenta":
            return [d + (h - d) * (i + 1) / n for i in range(n)]
        return [d + (h - d) * (1 - (1 - (i + 1) / n) ** 1.8) for i in range(n)]

    def golpes_hasta(self, ts):
        return bisect.bisect_right(self.golpes, ts + 1e-9)

    # ----------------------------------------------------------- posturas base
    def de_pie(self, x, mira=-1, agachado=0.0, **kw) -> Pose:
        """De pie, trabajando (formato de obra: mira a la izquierda por defecto)."""
        y = SUELO - 186 + agachado
        return Pose(cadera=(x, y), inclinacion=8 + agachado * 0.35, mira=mira,
                    pie_delante=(x + 24 * mira, SUELO - 2), pie_atras=(x - 18 * mira, SUELO - 2),
                    mano_delante=(x + 38 * mira, y + 92), mano_atras=(x - 34 * mira, y + 96), **kw)

    def de_pie_herramienta(self, x=None, **kw) -> Pose:
        x = self.x if x is None else x
        y = SUELO - 186
        return Pose(cadera=(x, y), inclinacion=6, mira=1, pie_delante=(x + 26, SUELO - 2),
                    pie_atras=(x - 18, SUELO - 2), mano_delante=(x + 40, y + 92), mano_atras=(x - 30, y + 96),
                    sonrisa=0.2 if self.perfeccionista else 0.7, **kw)

    def con_mandarria(self, agarre, angulo, inclinacion=6.0, agachado=0.0, **kw) -> Pose:
        p = self.de_pie_herramienta(**kw)
        p.cadera = (p.cadera[0], p.cadera[1] + agachado)
        p.inclinacion = inclinacion
        d = bib.direccion(angulo)
        p.mano_delante = (agarre[0] + d[0] * 16, agarre[1] + d[1] * 16)
        p.mano_atras = (agarre[0] - d[0] * 14, agarre[1] - d[1] * 14)
        return p

    def sentado_suelo_base(self) -> Pose:
        return Pose(cadera=(352, 786), inclinacion=34, mira=1, pie_delante=(462, SUELO - 2),
                    pie_atras=(440, SUELO - 2), mano_delante=(540, 826), mano_atras=(486, 842),
                    sonrisa=0.35, mirada=(0.4, 0.9))

    def trepando(self, nivel: float) -> Pose:
        k = math.floor(nivel)
        f = nivel - k
        delante = pz.y_nivel(k + min(1.0, f * 2))
        atras = pz.y_nivel(k + max(0.0, f * 2 - 1))
        if k % 2:
            delante, atras = atras, delante
        y_pies = pz.y_nivel(nivel)
        y_manos = max(pz.y_nivel(nivel) - 300, 392)
        return Pose(cadera=(462, y_pies - 182), inclinacion=6, mira=1,
                    pie_delante=(480, delante - 6), pie_atras=(460, atras - 6),
                    mano_delante=(pz.x_riel(pz.RIEL_D, y_manos) + 2, y_manos),
                    mano_atras=(pz.x_riel(pz.RIEL_I, y_manos) - 2, y_manos + 26),
                    mirada=(0.6, -0.6), sonrisa=1.0)

    def estado_inicial(self) -> Cuerpo:
        if self.herramienta == "mandarria":
            agarre, ang = (self.x + 80, SUELO - 190), 160.0
            return Cuerpo(self.con_mandarria(agarre, ang, inclinacion=10), agarre=agarre, angulo=ang)
        if self.sentado_suelo:
            return Cuerpo(self.sentado_suelo_base())
        return Cuerpo(self.de_pie(self.x))

    # ---------------------------------------------------------------- acciones
    def _hacer(self, i, t, ts_real) -> Cuerpo:
        ac = self.acciones[i]
        metodo = getattr(self, "_" + ac["accion"])
        return metodo(i, ac, t, self.parpado(ts_real))

    def _u(self, ac, t):
        return tramo(t, ac["desde_s"], ac["hasta_s"])

    def _siguiente(self, i):
        return self.acciones[i + 1] if i + 1 < len(self.acciones) else None

    # Esperar -------------------------------------------------------------------
    def _esperar(self, i, ac, t, parp):
        u = self._u(ac, t)
        if self.sentado_suelo:
            p = self.sentado_suelo_base()
            p.parpado = parp
            p.mirada = (1.0, lerp(-0.9, 0.2, tramo(u, 0.3, 0.6)))
            p.inclinacion = 20
            p.mano_delante, p.mano_atras = (470, 760), (430, 770)
            return Cuerpo(p, lapiz=u > 0.8)
        c = self.inicio(i)
        c = replace(c, pose=replace(c.pose, parpado=parp))
        return c

    # Preparar: mira cómo llega la madera y saca el martillo -----------------------
    def _preparar(self, i, ac, t, parp):
        f = t - ac["desde_s"]
        dur = ac["hasta_s"] - ac["desde_s"]
        f = f / dur if dur != 1.0 else f
        x = ac.get("x", self.x)
        p = self.de_pie(x, mirada=(-0.4, -1.0 + tramo(f, 0.3, 0.5) * 1.0))
        u = rebote(tramo(f, 0.55, 0.85))
        p.mano_delante = lerp(p.mano_delante, (x - 70, 470), u)
        sig = self._siguiente(i)
        if sig is not None and sig["accion"] == "construir":
            golpe = self.obj(sig).partes()[0][4]
            mano0, _ = martillo_clave(golpe, "arriba")
            p.mano_delante = lerp(p.mano_delante, mano0, suave(tramo(f, 0.85, 1.0)))
        p.parpado = parp
        return Cuerpo(p, martillo=(lerp(-160, 10, u) if f >= 0.55 else None))

    # Construir por partes ------------------------------------------------------
    def _construir(self, i, ac, t, parp):
        obra = self.obj(ac)
        subida, reb = ac.get("subida_s", 0.32), ac.get("rebote_s", 0.12)
        paso0, paso1 = ac.get("paso_s", [0.5, 0.3])
        xmin, xmax = ac.get("x_min", 700), ac.get("x_max", 800)
        claves_mano, claves_ang, claves_x, claves_ag = [], [], [], []
        for k, (_, _, _, _, golpe) in enumerate(obra.partes()):
            tg = obra.t_golpe[k]
            arriba, ang_a = martillo_clave(golpe, "arriba")
            abajo, ang_b = martillo_clave(golpe, "golpe")
            rb, ang_r = martillo_clave(golpe, "rebote")
            claves_mano += [(tg - subida, arriba), (tg - 0.08, arriba), (tg, abajo), (tg + reb, rb)]
            claves_ang += [(tg - subida, ang_a), (tg - 0.08, ang_a + 12), (tg, ang_b), (tg + reb, ang_r)]
            x = min(max(abajo[0] + 118, xmin), xmax)
            ag = limitar((golpe[1] - 600) * 0.55, 0, 70)
            claves_x += [(tg - paso0, x), (tg - paso1, x)]
            claves_ag += [(tg - paso0, ag), (tg - paso1, ag)]
        fin = obra.t_golpe[-1] + 0.35
        claves_mano.append((fin, tuple(ac.get("mano_final", [700, 640]))))
        claves_ang.append((fin, -20.0))
        claves_x.append((fin, ac.get("x_final", 760)))
        claves_ag.append((fin, 0))
        p = self.de_pie(pista(t, claves_x), agachado=pista(t, claves_ag), parpado=parp)
        p.mano_delante = pista(t, claves_mano, curva=lambda u: u)
        p.mirada = tuple(ac.get("mirada", [-0.6, 0.3]))
        return Cuerpo(p, martillo=pista(t, claves_ang, curva=lambda u: u))

    # Sorprenderse --------------------------------------------------------------
    def _sorprenderse(self, i, ac, t, parp):
        x = ac.get("x", self.x)
        p = self.de_pie(x, sonrisa=lerp(1.0, 2.0, pulso(t, ac["desde_s"] + 0.25, 0.5)), mirada=(-0.6, 0.4))
        p.mano_delante = (x - 60, 640)
        p.parpado = parp
        return Cuerpo(p, martillo=-20.0)

    # Mirar el resultado (y asentir) ------------------------------------------
    def _mirar(self, i, ac, t, parp):
        x = ac.get("x", self.x)
        p = self.de_pie(x, mirada=(-0.7, -0.5))
        p.cabeza = 6 * oscila(tramo(t, ac["desde_s"] + 0.05, ac["desde_s"] + 0.5), 2.0)
        p.mano_delante = (x - 70, 650)
        p.parpado = parp
        return Cuerpo(p, martillo=-20.0)

    # Sentarse en la silla -----------------------------------------------------
    def _sentarse(self, i, ac, t, parp):
        silla = self.obj(ac)
        u = suave(self._u(ac, t))
        x0 = ac.get("x_inicio", 700)
        de_pie = self.de_pie(x0, mira=1)
        de_pie.mano_delante = (x0 + 40, 640)
        p = pj.mezclar(de_pie, silla.sentado(silla.inclinacion(t)), u)
        p.parpado = parp
        return Cuerpo(p, martillo=15.0)

    # Tambalearse (en la silla o en la escalera) --------------------------------
    def _tambalearse(self, i, ac, t, parp):
        obra = self.obj(ac)
        d, h = ac["desde_s"], ac["hasta_s"]
        if isinstance(obra, pz.Silla):
            incl = obra.inclinacion(t)
            mov = abs(math.sin(2 * math.pi * 3.2 * (t - d))) * (1 - tramo(t, h - 0.5, h))
            p = pj.mezclar(obra.sentado(incl), obra.sentado(incl, "tambalea"), max(mov, 0.75 * (1 - tramo(t, h - 0.5, h))))
            p.parpado = parp
            return Cuerpo(p, martillo=lerp(15.0, 40.0, mov))
        nivel = self._nivel_previo(i)
        p = self.trepando(nivel)
        mov = abs(math.sin(2 * math.pi * 3.0 * (t - d))) * (1 - tramo(t, h - 0.25, h))
        p.mano_delante = lerp(p.mano_delante, (620, 260), max(mov, 0.6 * (1 - tramo(t, h - 0.25, h))))
        p.mano_atras = lerp(p.mano_atras, (330, 300), max(mov, 0.6 * (1 - tramo(t, h - 0.25, h))))
        p.sonrisa, p.mirada = 2.0, (0.0, 0.4)
        p.parpado = parp
        c = Cuerpo(self._rotar(p, obra.balanceo(t)), martillo_suelo=self._martillo_en_suelo(i))
        return c

    def _rotar(self, p: Pose, ang: float) -> Pose:
        if not ang:
            return p
        for campo in ("cadera", "mano_delante", "mano_atras", "pie_delante", "pie_atras"):
            setattr(p, campo, rotar(getattr(p, campo), pz.BASE_ESCALERA, ang))
        p.inclinacion += ang * p.mira
        return p

    def _nivel_previo(self, i):
        for ac in reversed(self.acciones[:i]):
            if ac["accion"] == "subir":
                return float(ac["nivel"])
        return 0.0

    def _martillo_en_suelo(self, i):
        """Dónde quedó el martillo si lo dejó al subir (y no lo ha vuelto a coger)."""
        pos = None
        for ac in self.acciones[:i + 1]:
            if ac["accion"] == "subir" and ac.get("deja_herramienta"):
                pos = tuple(ac.get("herramienta_en", [668, SUELO - 14]))
            elif ac["accion"] == "martillear":
                pos = None
        return pos

    # Martillear un punto (y arreglar algo, si se indica) --------------------------
    def _martillear(self, i, ac, t, parp):
        obra = self.objetos.get(ac.get("arregla")) if ac.get("arregla") else None
        golpe = obra.punto_arreglo(t) if obra is not None else tuple(ac["punto"])
        arriba, ang_a = martillo_clave(golpe, "arriba")
        abajo, ang_b = martillo_clave(golpe, "golpe")
        rb, ang_r = martillo_clave(golpe, "rebote")
        d, h = ac["desde_s"], ac["hasta_s"]
        x, agachado = ac.get("x", 770), ac.get("agachado", 70)
        listo = d + ac.get("preparar_s", 0.45)
        if t < listo:
            u = suave(tramo(t, d, listo))
            base = self.de_pie(x, agachado=agachado)
            base.mano_delante = arriba
            previo = self.inicio(i)
            if i > 0 and self.acciones[i - 1]["accion"] == "subir":  # baja de la escalera
                previo = replace(previo, pose=self.trepando(self._nivel_previo(i)))
            p = pj.mezclar(previo.pose, base, u)
            if previo.martillo is not None:
                return Cuerpo(p, martillo=lerp(previo.martillo, ang_a, u))
            return Cuerpo(p, martillo=(ang_a if u > 0.5 else None),
                          martillo_suelo=(None if u > 0.5 else previo.martillo_suelo))
        golpes = ac["golpes_s"]
        claves, angs = [(listo, arriba)], [(listo, ang_a)]
        for j, g in enumerate(golpes):
            m = 0.1 if j == 0 else 0.12
            claves += [(g - m, arriba), (g, abajo), (g + m, rb)]
            angs += [(g - m, ang_a), (g, ang_b), (g + m, ang_r)]
        claves.append((h, tuple(ac.get("mano_final", [735, 650]))))
        angs.append((h, -20.0))
        p = self.de_pie(x, agachado=lerp(agachado, 0, tramo(t, h - ac.get("levantarse_s", 0.3), h)),
                        mirada=tuple(ac.get("mirada", [-0.7, 0.6])))
        p.mano_delante = pista(t, claves, curva=lambda u: u)
        p.parpado = parp
        return Cuerpo(p, martillo=pista(t, angs, curva=lambda u: u))

    # Subir (o bajar) por la escalera --------------------------------------------
    def _subir(self, i, ac, t, parp):
        d, h = ac["desde_s"], ac["hasta_s"]
        destino = float(ac["nivel"])
        previo = self._nivel_previo(i)
        suelo = self._martillo_en_suelo(i)
        if destino < previo:  # bajar
            s_ = suave(tramo(t, d, h))
            nivel = previo * (1 - s_) + destino * s_
            p = self.trepando(nivel)
            p.sonrisa = 0.6
            return Cuerpo(p, martillo_suelo=suelo)
        acercarse = ac.get("acercarse_s", 0.0)
        if acercarse and t < d + acercarse:
            u = suave(tramo(t, d, d + acercarse))
            de_pie = self.de_pie(ac.get("x_inicio", 700), mira=1)
            return Cuerpo(pj.mezclar(de_pie, self.trepando(previo), u), martillo_suelo=suelo)
        nivel = self._escalones(t, (d + acercarse, h), previo, destino)
        p = self.trepando(nivel)
        p.parpado = parp
        return Cuerpo(p, martillo_suelo=suelo)

    @staticmethod
    def _escalones(t, tramo_t, desde, hasta):
        n = int(round(hasta - desde))
        u = tramo(t, *tramo_t) * n
        k = min(int(u), n - 1)
        return desde + k + suave(min(1.0, (u - k) * 1.3))

    def pasos(self, ac, i):
        """Instantes de cada paso al subir (para el audio)."""
        n = int(round(float(ac["nivel"]) - self._nivel_previo(i)))
        if n <= 0:
            return []
        d0 = ac["desde_s"] + ac.get("acercarse_s", 0.0)
        return [d0 + (ac["hasta_s"] - d0) * (k + 0.4) / n for k in range(n)]

    # Celebrar ------------------------------------------------------------------
    def _celebrar(self, i, ac, t, parp):
        d = ac["desde_s"]
        estilo = ac.get("estilo", "herramienta" if self.herramienta == "mandarria" else "brazos")
        if estilo == "sentado":
            silla = self.obj(ac)
            incl = silla.inclinacion(t)
            p = pj.mezclar(silla.sentado(incl), silla.sentado(incl, "feliz"), suave(tramo(t, d, d + 0.4)))
            bote = abs(math.sin(math.pi * tramo(t, d + 0.02, d + 0.82) * 2)) * 10 * (1 - tramo(t, d + 0.02, d + 0.82))
            p.cadera = (p.cadera[0], p.cadera[1] - bote)
            p.mano_delante = (p.mano_delante[0], p.mano_delante[1] - bote * 1.5)
            p.parpado = parp
            return Cuerpo(p, martillo=lerp(15.0, 22.0, suave(tramo(t, d, d + 0.4))))
        if estilo == "señalar":
            p = self.trepando(self._nivel_previo(i))
            u = suave(tramo(t, d, d + 0.6))
            p.mano_delante = lerp(p.mano_delante, tuple(ac.get("punto", [650, 170])), u)
            p.mirada = lerp((0.6, -0.6), (1.0, -0.5), u)
            p.sonrisa = lerp(1.0, 1.15, u)
            p.cabeza = lerp(0.0, -8.0, u)
            return Cuerpo(p, martillo_suelo=self._martillo_en_suelo(i))
        # Con la herramienta en alto (o los brazos), dos saltitos, y feliz.
        inicio = self.inicio(i)
        u = self._u(ac, t)
        x = self.x
        arriba_g, arriba_a = (x + 8, SUELO - 520), 0.0
        hombro_g, hombro_a = (x + 34, SUELO - 300), -58.0
        bote = abs(math.sin(math.pi * 2 * tramo(u, 0.15, 0.7))) * 34 * (1 - tramo(u, 0.15, 0.7))
        if u < 0.6:
            g, a = arriba_g, arriba_a
        else:
            v = suave(tramo(u, 0.6, 1.0))
            g, a = lerp(arriba_g, hombro_g, v), lerp(arriba_a, hombro_a, v)
        if self.herramienta != "mandarria":
            p = self.de_pie_herramienta(x)
            p.mano_delante, p.mano_atras = (x + 70, SUELO - 520), (x - 70, SUELO - 510)
            meta = Cuerpo(p)
        else:
            p = self.con_mandarria(g, a, inclinacion=0)
            meta = Cuerpo(p, agarre=g, angulo=a)
        p.sonrisa, p.mirada, p.cabeza = 1.2, (0.4, -0.4), -6
        p.cadera = (p.cadera[0], p.cadera[1] - bote)
        p.pie_delante = (p.pie_delante[0], p.pie_delante[1] - bote)
        p.pie_atras = (p.pie_atras[0], p.pie_atras[1] - bote)
        p.mano_delante = (p.mano_delante[0], p.mano_delante[1] - bote)
        p.mano_atras = (p.mano_atras[0], p.mano_atras[1] - bote)
        if meta.agarre:
            meta.agarre = (meta.agarre[0], meta.agarre[1] - bote)
        return mezclar_cuerpo(inicio, meta, suave(limitar(u / 0.25)))

    # Golpear con la mandarria ---------------------------------------------------
    def _golpe_en(self, s: float, cansancio: float) -> Cuerpo:
        destino = self.roca.roca.punto_golpe if self.roca else (self.x + 300, SUELO - 200)
        ang_imp, ang_arr = 122.0, -32.0
        d = bib.direccion(ang_imp)
        g_imp = (destino[0] - d[0] * (bib.LARGO_MANDARRIA + 24), destino[1] - d[1] * (bib.LARGO_MANDARRIA + 24))
        g_arr = (self.x - 22, SUELO - 470)
        se = entra(s) if s < 1 else 1.0
        agarre = lerp(g_arr, g_imp, se)
        agarre = (agarre[0] - math.sin(math.pi * se) * 40, agarre[1] - math.sin(math.pi * se) * 30)
        ang = lerp(ang_arr, ang_imp, se)
        p = self.con_mandarria(agarre, ang, inclinacion=lerp(0, 18, se), agachado=24 * se)
        if self.perfeccionista:
            p.sonrisa = lerp(0.1, -0.45, cansancio)
            p.hombros = 8 * cansancio
        else:
            p.sonrisa = 0.55
        p.mirada = (0.9, 0.5)
        return Cuerpo(p, agarre=agarre, angulo=ang)

    def _golpear(self, i, ac, t, parp):
        golpes = self.instantes_golpe(ac)
        partir = self.roca.golpes_partir if self.roca else len(golpes)
        cansancio = limitar(self.golpes_hasta(t) / max(1, partir or len(golpes)))
        if t < golpes[0]:
            u = tramo(t, ac["desde_s"], golpes[0])
            if u < 0.55:
                return mezclar_cuerpo(self.inicio(i), self._golpe_en(0.0, cansancio), suave(u / 0.55))
            return self._golpe_en((u - 0.55) / 0.45, cansancio)
        j = bisect.bisect_right(golpes, t) - 1
        if j >= len(golpes) - 1:
            return self._golpe_en(1.0, cansancio)
        t0, t1 = golpes[j], golpes[j + 1]
        amp = limitar((t1 - t0) / 0.5, 0.12, 1.0)
        return self._golpe_en(1 - amp * math.sin(math.pi * ((t - t0) / (t1 - t0)) ** 0.8), cansancio)

    # Rendirse: suelta la herramienta, suspira y se va de espaldas ------------------
    def _rendirse(self, i, ac, t, parp):
        inicio = self.inicio(i)
        u = self._u(ac, t)
        x0 = self.x
        suelo = None
        if inicio.agarre is not None:
            caida = entra(limitar(u / 0.18))
            agarre_suelo, ang_suelo = (x0 + 150, SUELO - 8), -92.0
            suelo = ((lerp(inicio.agarre, agarre_suelo, caida), lerp(inicio.angulo, ang_suelo, caida)) if caida < 1
                     else (agarre_suelo, ang_suelo))
        v = suave(tramo(u, 0.12, 0.45))
        p = self.de_pie_herramienta(x0)
        p.hombros, p.cabeza = 16 * v, 16 * v
        p.sonrisa, p.parpado = lerp(0.0, -0.75, v), lerp(0.0, 0.5, v)
        p.mano_delante = (x0 + 22, SUELO - 96)
        p.mano_atras = (x0 - 16, SUELO - 92)
        base = mezclar_cuerpo(Cuerpo(inicio.pose, agarre=inicio.agarre, angulo=inicio.angulo), Cuerpo(p),
                              suave(limitar(u / 0.2)))
        base.agarre = None
        base.suelo = suelo
        if u < 0.47:
            return base
        w = suave(tramo(u, 0.5, 1.0))
        x = x0 - 230 * w
        fase = 2 * math.pi * 2.25 * tramo(u, 0.5, 1.0)
        paso = 30 * math.sin(fase)
        q = self.de_pie_herramienta(x)
        q.mira, q.espalda = -1, True
        q.hombros, q.cabeza, q.sonrisa = 16.0, 18.0, -0.75
        q.pie_delante = (x - paso, SUELO - 2 - max(0, math.sin(fase)) * 10)
        q.pie_atras = (x + paso, SUELO - 2 - max(0, -math.sin(fase)) * 10)
        q.mano_delante = (x - 10 - paso * 0.6, SUELO - 94)
        q.mano_atras = (x + 14 + paso * 0.6, SUELO - 92)
        giro = Cuerpo(q, suelo=suelo, escala=lerp(1.0, 0.8, w), subida=60 * w)
        if u < 0.55:
            return mezclar_cuerpo(base, giro, (u - 0.47) / 0.08)
        return giro

    # Caminar hasta una x ---------------------------------------------------------
    def _caminar(self, i, ac, t, parp):
        inicio = self.inicio(i)
        x0 = inicio.pose.cadera[0]
        x1 = ac["x"]
        u = suave(self._u(ac, t))
        x = lerp(x0, x1, u)
        mira = 1 if x1 >= x0 else -1
        fase = 2 * math.pi * abs(x1 - x0) / 110 * self._u(ac, t)
        paso = 26 * math.sin(fase) * (1 - tramo(self._u(ac, t), 0.85, 1.0))
        p = self.de_pie(x, mira=mira, parpado=parp)
        p.pie_delante = (x + mira * 12 + paso, SUELO - 2 - max(0, math.sin(fase)) * 8)
        p.pie_atras = (x - mira * 12 - paso, SUELO - 2 - max(0, -math.sin(fase)) * 8)
        p.mano_delante = (x + mira * 20 - paso * 0.7, SUELO - 96)
        p.mano_atras = (x - mira * 20 + paso * 0.7, SUELO - 96)
        p.espalda = bool(ac.get("de_espaldas", False))
        # Conserva la cara y el ánimo con el que empezó a andar.
        q = inicio.pose
        p.sonrisa, p.hombros, p.cabeza, p.mirada = q.sonrisa, q.hombros, q.cabeza, q.mirada
        p.parpado = max(parp, q.parpado)
        if inicio.agarre is not None:  # se lleva la herramienta en las manos
            dx = x - x0
            agarre = (inicio.agarre[0] + dx, inicio.agarre[1])
            d = bib.direccion(inicio.angulo)
            p.mano_delante = (agarre[0] + d[0] * 16, agarre[1] + d[1] * 16)
            p.mano_atras = (agarre[0] - d[0] * 14, agarre[1] - d[1] * 14)
            return replace(inicio, pose=p, agarre=agarre)
        return replace(inicio, pose=p, martillo=inicio.martillo)

    # Dudar: levanta la herramienta (o las manos), duda... y la baja ----------------
    def _dudar(self, i, ac, t, parp):
        inicio = self.inicio(i)
        u = self._u(ac, t)
        sube = suave(tramo(u, 0, 0.28))
        baja = suave(tramo(u, 0.72, 1.0))
        arriba = sube * (1 - baja)
        tiembla = 3 * oscila(tramo(u, 0.28, 0.72), 3.0) if 0.28 <= u < 0.72 else 0.0
        p = replace(inicio.pose)
        p.sonrisa = lerp(inicio.pose.sonrisa, -0.3, sube)
        p.parpado = parp
        if inicio.agarre is not None:
            arr = (self.x - 22, SUELO - 470)
            g = lerp(inicio.agarre, arr, arriba * 0.8)
            a = lerp(inicio.angulo, -32.0, arriba * 0.8) + tiembla
            q = self.con_mandarria(g, a)
            q.sonrisa, q.parpado = p.sonrisa, parp
            return replace(inicio, pose=q, agarre=g, angulo=a)
        if inicio.martillo is not None:
            return replace(inicio, pose=p, martillo=inicio.martillo + 60 * arriba + tiembla)
        y = p.cadera[1]
        p.mano_delante = lerp(p.mano_delante, (p.cadera[0] + 50 * p.mira, y - 120 + tiembla), arriba)
        return replace(inicio, pose=p)

    # Plano: dibujar, medir, borrar, arrugar (sentado en el suelo) --------------------
    def _dibujar(self, i, ac, t, parp):
        u = self._u(ac, t)
        p = self.sentado_suelo_base()
        p.parpado = parp
        segs, _ = self.plano.dibujos[self.hoja[i]]
        n = len(segs)
        idx = min(int(u * n), n - 1)
        f = u * n - idx
        s0, s1 = segs[idx]
        p.mano_delante = pz.uv(*lerp(s0, s1, f))
        p.inclinacion = 40
        return Cuerpo(p, lapiz=True)

    def _medir(self, i, ac, t, parp):
        u = self._u(ac, t)
        p = self.sentado_suelo_base()
        p.inclinacion = 44
        p.cabeza = -8 + 6 * oscila(u, 1.0)
        p.parpado = 0.45
        p.mano_delante = pz.uv(0.85, 0.62)
        p.mano_atras = pz.uv(0.12, 0.62)
        p.sonrisa = 0.0
        return Cuerpo(p)

    def _borrar(self, i, ac, t, parp):
        u = self._u(ac, t)
        k = self.hoja[i]
        p = self.sentado_suelo_base()
        p.parpado = parp
        _, borr = self.plano.dibujos[min(k, len(self.plano.dibujos) - 1)]
        lista = self.plano.borrones_final if k >= self.plano.n_arrugadas else borr
        j = min(int(u * len(lista)), len(lista) - 1)
        c = pz.uv(*lista[j])
        p.mano_delante = (c[0] + 16 * oscila(u * 9, 1.0), c[1] + 4 * oscila(u * 9, 1.0, 0.25))
        p.inclinacion = 42
        p.sonrisa = -0.2
        return Cuerpo(p, goma=True)

    _ARRUGA, _TIRA = 0.15 / 0.29, 0.26 / 0.29

    def _sub_arrugar(self, ac, t):
        u = self._u(ac, t)
        if u < self._ARRUGA:
            return "arruga", u / self._ARRUGA
        if u < self._TIRA:
            return "tira", (u - self._ARRUGA) / (self._TIRA - self._ARRUGA)
        return "pausa", (u - self._TIRA) / (1 - self._TIRA)

    def _arrugar(self, i, ac, t, parp):
        fase, u = self._sub_arrugar(ac, t)
        p = self.sentado_suelo_base()
        p.parpado = parp
        if fase == "arruga":
            centro = pz.uv(0.5, 0.45)
            m = lerp(centro, (560, 740), suave(u))
            p.mano_delante = (m[0] + 22 * (1 - u), m[1])
            p.mano_atras = (m[0] - 22 * (1 - u), m[1] + 4)
            p.sonrisa = -0.5
            p.inclinacion = lerp(42, 26, u)
            return Cuerpo(p)
        if fase == "tira":
            p.mano_delante = lerp((560, 740), (300, 560), sale(u))
            p.mano_atras = (470, 790)
            p.inclinacion = lerp(26, 10, sale(u))
            p.sonrisa = -0.4
            return Cuerpo(p)
        p.mano_delante = lerp((300, 560), (520, 826), suave(u))
        p.inclinacion = lerp(10, 34, suave(u))
        return Cuerpo(p, lapiz=True)

    def lanzamientos(self):
        """Ventanas (inicio, fin) en que vuela cada bola de papel."""
        out = []
        for ac in self.acciones:
            if ac["accion"] == "arrugar":
                d, h = ac["desde_s"], ac["hasta_s"]
                out.append((d + (h - d) * self._ARRUGA, d + (h - d) * self._TIRA))
        return out

    def fase_plano(self, ts):
        """Lo que pasa con la hoja en este instante: (fase, progreso, hoja)."""
        i, t = self._situacion(ts)
        ac = self.acciones[i]
        a = ac["accion"]
        k = self.hoja[i]
        u = self._u(ac, t)
        if a == "esperar":
            return "espera", u, k
        if a == "dibujar":
            return "dibuja", u, k
        if a == "medir":
            return "mide", u, k
        if a == "borrar":
            return "borra", u, k
        if a == "arrugar":
            f, v = self._sub_arrugar(ac, t)
            return f, v, k
        if a == "suspirar":
            return ("fin", 1.0, k) if ts >= ac["hasta_s"] else ("suspira", u, k)
        return "fin", 1.0, k

    # Suspirar -------------------------------------------------------------------
    def _suspirar(self, i, ac, t, parp):
        u = self._u(ac, t)
        v = suave(u)
        if self.sentado_suelo:
            p = self.sentado_suelo_base()
            p.parpado = parp
            p.inclinacion = lerp(34, 18, v)
            p.hombros = 16 * v
            p.cabeza = 14 * v
            p.sonrisa = lerp(0.3, -0.75, v)
            p.parpado = lerp(0.0, 0.5, v)
            p.mano_delante = lerp((540, 826), (470, 778), v)
            p.mano_atras = lerp((486, 842), (440, 786), v)
            p.mirada = (0.3, 1.0)
            return Cuerpo(p, lapiz=v < 0.5)
        inicio = self.inicio(i)
        p = replace(inicio.pose)
        p.hombros = lerp(inicio.pose.hombros, 16, v)
        p.cabeza = lerp(inicio.pose.cabeza, 14, v)
        p.sonrisa = lerp(inicio.pose.sonrisa, -0.7, v)
        p.parpado = lerp(parp, 0.5, v)
        return replace(inicio, pose=p)

    def soplido(self, lz, ts, e):
        for ac in self.acciones:
            if ac["accion"] != "suspirar":
                continue
            u = tramo(ts, ac["desde_s"] + 0.1, ac["hasta_s"])
            if not (0 < u < 1):
                continue
            p = self.estado(ts).pose
            boca = pj._local(e, p, 0.3 * pj.R_CABEZA, 0.4 * pj.R_CABEZA)
            for j in range(3):
                d = 30 + 60 * u + j * 14
                y = boca[1] + (j - 1) * 14 + 20 * u
                lz.linea([(boca[0] + d * p.mira, y), (boca[0] + (d + 34) * p.mira, y + 6)], 3, tenue(0.8 * (1 - u)))

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, lz: Lienzo, ts: float):
        c = self.estado(ts)
        if c.martillo_suelo is not None and c.martillo is None:
            pj.martillo(lz, c.martillo_suelo, 90, largo=66)
        if c.suelo is not None:
            bib.mandarria(lz, *c.suelo)
        pose = c.pose
        lz2 = pj.a_escala(lz, c.escala, (pose.cadera[0], SUELO))
        if c.subida:
            dy = -c.subida / c.escala
            pose = replace(pose, cadera=(pose.cadera[0], pose.cadera[1] + dy),
                           mano_delante=(pose.mano_delante[0], pose.mano_delante[1] + dy),
                           mano_atras=(pose.mano_atras[0], pose.mano_atras[1] + dy),
                           pie_delante=(pose.pie_delante[0], pose.pie_delante[1] + dy),
                           pie_atras=(pose.pie_atras[0], pose.pie_atras[1] + dy))

        def en_mano(lz3, e):
            m = e["mano_d"]
            if c.martillo is not None:
                pj.martillo(lz3, m, c.martillo)
            if c.agarre is not None and self.herramienta == "mandarria":
                bib.mandarria(lz3, c.agarre, c.angulo)
            if c.lapiz:
                lz3.linea([(m[0] - 6, m[1] - 34), (m[0] + 4, m[1] + 6)], 7, BLANCO)
            if c.goma:
                lz3.poligono([(m[0] - 14, m[1] - 4), (m[0] + 14, m[1] - 4), (m[0] + 14, m[1] + 10),
                              (m[0] - 14, m[1] + 10)], relleno=BLANCO)

        e = pj.dibujar(lz2, pose, perfeccionista=self.perfeccionista, en_mano=en_mano)
        if self.sentado_suelo:
            self.soplido(lz, ts, e)

    # ------------------------------------------------------------------- audio
    def eventos(self):
        pan = self.paneo
        ev = []
        pasos = 0
        for i, ac in enumerate(self.acciones):
            a, d, h = ac["accion"], ac["desde_s"], ac["hasta_s"]
            if a == "construir":
                for k, tg in enumerate(self.obj(ac).t_golpe):
                    ev.append((tg, "martillo", 0.85, pan, {"semilla": k}))
            elif a == "martillear":
                ev += [(g, "martillo", 0.75, pan, {"semilla": 9}) for g in ac["golpes_s"]]
            elif a == "subir":
                for t in self.pasos(ac, i):
                    ev.append((t, "crujido", 0.25, pan + 0.05, {"semilla": 5 + pasos}))
                    pasos += 1
            elif a == "rendirse":
                ev.append((d + (h - d) * 0.18, "crujido", 0.6, pan, {"semilla": 4}))
                ev.append((d + (h - d) * 0.14, "suspiro", 0.9, pan, {"dur": 1.1}))
                for k in range(4):
                    ev.append((d + (h - d) * (0.55 + k * 0.1), "crujido", 0.16, pan, {"semilla": 20 + k}))
            elif a == "dibujar":
                final = self.hoja[i] >= self.plano.n_arrugadas
                ev.append((d, "hoja", 0.55, pan, {"semilla": 9 if final else self.hoja[i]}))
                ev.append((d, "lapiz", 0.5, pan, {"dur": h - d}))
            elif a == "borrar":
                final = self.hoja[i] >= self.plano.n_arrugadas
                ev.append((d, "borrador", 0.75 if final else 0.7, pan, {"dur": h - d}))
            elif a == "arrugar":
                t0, t1 = d, d + (h - d) * self._ARRUGA
                ev.append((t0, "papel", 0.85, pan, {"semilla": self.hoja[i], "dur": t1 - t0}))
                ev.append((d + (h - d) * self._TIRA, "bola", 0.5, pan + 0.1, {}))
            elif a == "suspirar":
                ev.append((d, "suspiro", 0.9, pan - 0.05, {"dur": 1.1}))
            elif a == "dudar":
                pass
        return ev


# ============================================================ OBJETOS VIVOS
TAM_MARTILLO = 1.25


class MartilloVivo(Actor):
    """Martillo con cara. El "martillo_perfeccionista" lleva gafas pequeñas y brazos (regla y clavo)."""

    def __init__(self, conf, indice, objetos):
        super().__init__(conf, indice, objetos)
        self.perfeccionista = conf["tipo"] == "martillo_perfeccionista"
        self.tam = conf.get("tamano", TAM_MARTILLO)
        self.forma = martillo(gafas=self.perfeccionista, brazos=self.perfeccionista, tam=self.tam)
        if self.perfeccionista:
            self.forma.brazo = (92.0, 88.0)
        self.x, self.y = conf.get("x", 478), conf.get("y", pz.MESA)
        self.espejo = conf.get("espejo", True)
        self.paneo = conf.get("paneo", 0.3 if self.perfeccionista else -0.3)
        self.tabla = None
        self._preparar_objetos()
        self.pista = PistaObjeto(self._claves()) if not self.perfeccionista else None

    def _preparar_objetos(self):
        for ac in self.acciones:
            if ac["accion"] == "construir":
                caja = self.obj(ac)
                caja.t_pieza = [p["aparece_s"] for p in ac["partes"]]
                caja.tocs = [list(p["tocs_s"]) for p in ac["partes"]]
                caja.alturas = []
                tor = ac.get("clavo_torcido")
                for k, p in enumerate(ac["partes"]):
                    n = len(p["tocs_s"])
                    if tor and tor["parte"] == k:
                        efectivos = n - 1
                        alt = [round(40 * (1 - (j + 1) / efectivos)) for j in range(efectivos)]
                        alt.insert(tor["toc"] - 1, alt[tor["toc"] - 2] if tor["toc"] >= 2 else 40)
                        caja.alturas.append(alt)
                    else:
                        caja.alturas.append([round(40 * (1 - (j + 1) / n)) for j in range(n)])
                if tor:
                    caja.torcido = (tor["parte"], p_toc(ac, tor), tor["endereza_s"])
            if ac["accion"] in ("colocar_clavo", "sacar_clavo", "poner_clavo", "medir"):
                self.tabla = self.obj(ac)
                self.tabla.usuario = self

    def estado_inicial(self):
        return EstadoObjeto(pos=(self.x, self.y), angulo=0.0, espejo=self.espejo)

    # --------------------------------------------------- hacedor: claves de animación
    def _golpe(self, clavo, espejo, angulo, **kw) -> EstadoObjeto:
        sx, sy = kw.get("escala", (1.0, 1.0))
        f = ((-CARA_GOLPEO[0] if espejo else CARA_GOLPEO[0]) * self.tam * sx, CARA_GOLPEO[1] * self.tam * sy)
        rf = rotar(f, (0, 0), angulo)
        return EstadoObjeto(pos=(clavo[0] - rf[0], clavo[1] - rf[1]), angulo=angulo, espejo=espejo, **kw)

    def _claves(self):
        claves = []
        pos = (self.x, self.y)
        for ac in self.acciones:
            a, d, h = ac["accion"], ac["desde_s"], ac["hasta_s"]
            if a == "preparar":
                reposo = EstadoObjeto(pos=pos, angulo=0.0, espejo=self.espejo)
                claves += [Clave(d, reposo), Clave(d + (h - d) * 2 / 3, reposo),
                           Clave(h, EstadoObjeto(pos=pos, escala=(1.05, 0.93), espejo=self.espejo))]
            elif a == "construir":
                claves += self._claves_construir(ac)
            elif a == "caminar":
                final = EstadoObjeto(pos=(ac["x"], ac.get("y", self.y)), angulo=ac.get("angulo", 0.0),
                                     espejo=ac.get("espejo", self.espejo))
                claves.append(Clave(h, final, salto=ac.get("salto", 70)))
                pos = final.pos
        return claves or [Clave(0.0, self.estado_inicial())]

    def _claves_construir(self, ac):
        caja = self.obj(ac)
        claves = []
        tor = ac.get("clavo_torcido")
        for i, ((_, clavo), parte) in enumerate(zip(pz.PIEZAS_CAJA, ac["partes"])):
            tocs = parte["tocs_s"]
            espejo = clavo[0] < 300
            ang = -70.0 if espejo else 70.0
            atras = 55.0 if espejo else -55.0
            golpe = self._golpe(clavo, espejo, ang, escala=(1.03, 0.96))
            arriba = EstadoObjeto(pos=golpe.pos, angulo=ang + atras, espejo=espejo)
            reb = EstadoObjeto(pos=golpe.pos, angulo=ang + atras * 0.3, espejo=espejo)
            claves.append(Clave(parte["aparece_s"] - 0.05, arriba, salto=60))
            t_tuerce = p_toc(ac, tor) if tor and tor["parte"] == i else None
            for tau in tocs:
                if t_tuerce is not None and tau > t_tuerce:
                    continue
                claves += [Clave(tau - 0.07, arriba, "sale"), Clave(tau, golpe, "golpe"), Clave(tau + 0.05, reb, "sale")]
            if t_tuerce is not None:
                sorpresa = EstadoObjeto(pos=golpe.pos, angulo=ang + atras * 1.05, espejo=espejo)
                claves += [Clave(t_tuerce + 0.1, sorpresa, "sale"), Clave(tor["sorpresa_hasta_s"], sorpresa)]
                idx = tocs.index(t_tuerce)
                alto = caja.alturas[i][idx]
                punta = pz.punta_clavo(clavo, alto, pz.DOBLEZ)
                g2 = self._golpe(punta, False, 85.0, escala=(1.03, 0.96))
                a2 = EstadoObjeto(pos=g2.pos, angulo=85.0 - 45.0, espejo=False)
                te = tor["endereza_s"]
                claves += [Clave(te - 0.08, a2, salto=30), Clave(te, g2, "golpe"), Clave(te + 0.07, a2, "sale")]
                for tau in tocs[idx + 1:]:
                    claves += [Clave(tau - 0.07, arriba, "sale"), Clave(tau, golpe, "golpe"),
                               Clave(tau + 0.05, reb, "sale")]
        return claves

    # ---------------------------------------------------------------- expresión
    def _expresion_hacedor(self, ts):
        trabajo = Expresion(cejas=1.0, sonrisa=0.5, mirada=(-0.6, 0.5))
        sorpresa = Expresion(cejas=-0.6, sonrisa=2.0, mirada=(0.0, 0.7))
        enfado = Expresion(cejas=1.3, sonrisa=0.1, mirada=(0.0, 0.7))
        feliz = Expresion(ojos_felices=1.0, sonrisa=1.2)
        mira = Expresion(sonrisa=0.9, mirada=(1.0, 0.1))
        e = trabajo
        for ac in self.acciones:
            a, d, h = ac["accion"], ac["desde_s"], ac["hasta_s"]
            if ts < d:
                break
            if a == "construir" and ac.get("clavo_torcido"):
                tor = ac["clavo_torcido"]
                tt, ts_ = p_toc(ac, tor), tor["sorpresa_hasta_s"]
                fin_enfado = tor["endereza_s"] + 0.15
                if tt + 0.02 <= ts < ts_:
                    e = sorpresa
                elif ts_ <= ts < fin_enfado:
                    e = mezclar_expresion(sorpresa, enfado, suave(tramo(ts, ts_, ts_ + 0.1)))
                else:
                    e = trabajo
            elif a == "celebrar":
                e = mezclar_expresion(trabajo, feliz, suave(tramo(ts, d, d + 0.5)))
            elif a == "mirar":
                if ts < h - 0.4:
                    e = mezclar_expresion(feliz, mira, suave(tramo(ts, d, d + 0.3)))
                else:
                    e = mezclar_expresion(mira, feliz, suave(tramo(ts, h - 0.4, h)))
        e.parpado = self.parpado(ts) if e.ojos_felices < 0.5 else 0.0
        return e

    def _hacer(self, i, t, ts_real):
        raise NotImplementedError  # los martillos se evalúan con `estado` directamente

    def estado(self, ts):
        if not self.perfeccionista:
            est = self.pista.en(ts)
            est.expresion = self._expresion_hacedor(ts)
            for ac in self.acciones:
                if ac["accion"] == "celebrar":
                    d = ac["desde_s"] + 0.5
                    bote = abs(math.sin(math.pi * 2 * tramo(ts, d, d + 0.7))) * 18 * (1 - tramo(ts, d, d + 0.7))
                    if bote:
                        est.pos = (est.pos[0], est.pos[1] - bote)
            return est
        return self._estado_perfeccionista(ts)[0]

    # ------------------------------------------------------ perfeccionista
    def _fase(self, ts):
        i, t = self._situacion(ts)
        ac = self.acciones[i]
        a = ac["accion"]
        u = tramo(t, ac["desde_s"], ac["hasta_s"])
        if a == "esperar":
            return "espera", u, i
        if a == "colocar_clavo":
            return "coloca", u, i
        if a == "medir":
            if any(x["accion"] == "suspirar" and x["hasta_s"] <= ac["desde_s"] for x in self.acciones):
                return "final", u, i
            previa = self.acciones[i - 1]["accion"] if i > 0 else ""
            return ("mide2" if previa == "sacar_clavo" else "mide"), u, i
        if a == "sacar_clavo":
            return "saca", u, i
        if a == "poner_clavo":
            if u < 0.16 / 0.30:
                return "pone", u / (0.16 / 0.30), i
            return "pausa", (u - 0.16 / 0.30) / (1 - 0.16 / 0.30), i
        if a == "dudar":
            return "duda", u, i
        if a == "suspirar":
            return "suspira", u, i
        return "quieto", 0.0, i

    def _estado_perfeccionista(self, ts):
        fase, u, _ = self._fase(ts)
        base_ang = -8.0
        expr = Expresion(cejas=-1.0, sonrisa=0.2, mirada=(-0.8, 0.5))
        expr.parpado = self.parpado(ts)
        x, y = self.x, self.y
        reposo_regla = (x - 55, y - 78)
        reposo_clavo = (x - 21, y - 36)
        mano_regla, mano_clavo = reposo_regla, reposo_clavo
        cp = self.tabla.punto_clavo
        largo_regla = 120
        regla_tabla = (cp[0] + 22, cp[1] - largo_regla / 2)
        regla_aire = (cp[0] + 22, cp[1] - 112)
        clavo_aire = (cp[0], cp[1] - 128)
        clavo = ("tabla", 20.0)
        ang, escala, elevacion = base_ang, (1.0, 1.0), 0.0
        if fase == "espera":
            clavo = ("tumbado", None)
            expr.mirada = (-0.6, 0.8)
        elif fase == "coloca":
            tumbado = (self.tabla.clavos[1], self.tabla.y - 34)
            if u < 0.4:
                mano_clavo = lerp(reposo_clavo, tumbado, suave(u / 0.4))
                clavo = ("tumbado", None)
            elif u < 0.85:
                mano_clavo = lerp(tumbado, (cp[0], cp[1] - 60), suave((u - 0.4) / 0.45))
                clavo = ("mano", mano_clavo)
            else:
                mano_clavo = lerp((cp[0], cp[1] - 30), reposo_clavo, suave((u - 0.85) / 0.15))
        elif fase == "mide":
            mano_regla = lerp(reposo_regla, regla_tabla, suave(tramo(u, 0, 0.3)))
            expr.parpado = 0.45
            ang = base_ang - 4 * suave(tramo(u, 0, 0.3)) + 1.5 * oscila(u, 1.0)
        elif fase == "saca":
            mano_regla = lerp(regla_tabla, reposo_regla, suave(tramo(u, 0, 0.45)))
            cabeza = (cp[0], cp[1] - 20)
            if u < 0.35:
                mano_clavo = lerp(reposo_clavo, cabeza, suave(u / 0.35))
            else:
                mano_clavo = lerp(cabeza, clavo_aire, sale((u - 0.35) / 0.65))
                clavo = ("mano", mano_clavo)
        elif fase == "mide2":
            mano_clavo = clavo_aire
            clavo = ("mano", clavo_aire)
            mano_regla = lerp(reposo_regla, regla_aire, suave(tramo(u, 0, 0.3)))
            expr.parpado = 0.45
            expr.mirada = (-0.8, -0.2)
            ang = base_ang - 3 + 1.5 * oscila(u, 1.5)
        elif fase == "pone":
            mano_regla = lerp(regla_aire, reposo_regla, suave(tramo(u, 0, 0.4)))
            mano_clavo = lerp(clavo_aire, (cp[0], cp[1] - 20), suave(u))
            clavo = ("mano", mano_clavo) if u < 0.98 else ("tabla", 20.0)
        elif fase == "pausa":
            mano_clavo = lerp((cp[0], cp[1] - 20), reposo_clavo, suave(u))
        elif fase == "duda":
            sube = suave(tramo(u, 0, 0.28))
            baja = suave(tramo(u, 0.72, 1.0))
            arriba = sube * (1 - baja)
            ang = base_ang + 12 * arriba
            elevacion = 50 * arriba
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
                mano_regla = lerp(reposo_regla, regla_tabla, suave(u))
                expr.mirada = (-0.9, 0.6)
        est = EstadoObjeto(pos=(x, y - elevacion), angulo=ang, escala=escala, espejo=self.espejo, expresion=expr,
                           manos=(mano_regla, mano_clavo))
        return est, clavo

    def clavo_en(self, ts):
        return self._estado_perfeccionista(ts)[1]

    # ------------------------------------------------------------------ dibujo
    def dibujar(self, lz: Lienzo, ts: float):
        if not self.perfeccionista:
            self.forma.dibujar(lz, self.estado(ts))
            return
        est, clavo = self._estado_perfeccionista(ts)

        def en_mano(lz2, i, mano):
            if i == 0:
                regla(lz2, mano)
            elif clavo[0] == "mano":
                p = clavo[1]
                pz.clavo(lz2, (p[0], p[1] + 40), 40)

        self.forma.dibujar(lz, est, en_mano=en_mano)
        for ac in self.acciones:
            if ac["accion"] != "suspirar":
                continue
            v = tramo(ts, ac["desde_s"] + 0.1, ac["hasta_s"] - 0.1)
            if 0 < v < 1:
                boca = self.forma._local_cara(est, 0, 16)
                for j in range(3):
                    d = 26 + 50 * v + j * 12
                    yy = boca[1] + (j - 1) * 12 + 14 * v
                    lz.linea([(boca[0] - d, yy), (boca[0] - d - 28, yy + 5)], 3, tenue(0.8 * (1 - v)))

    # ------------------------------------------------------------------- audio
    def eventos(self):
        pan = self.paneo
        ev = []
        reglas = 0
        for i, ac in enumerate(self.acciones):
            a, d, h = ac["accion"], ac["desde_s"], ac["hasta_s"]
            if a == "construir":
                tor = ac.get("clavo_torcido")
                for k, parte in enumerate(ac["partes"]):
                    ev.append((parte["aparece_s"] + 0.1, "crujido", 0.2, pan, {"semilla": 10 + k}))
                    for j, tau in enumerate(parte["tocs_s"]):
                        ev.append((tau, "martillo", 0.7, pan, {"semilla": k * 4 + j}))
                if tor:
                    ev.append((p_toc(ac, tor) + 0.01, "clavo_torcido", 0.85, pan, {}))
                    ev.append((tor["endereza_s"], "martillo", 0.55, pan, {"semilla": 30}))
            elif a == "colocar_clavo":
                ev.append((h - 0.05, "bola", 0.35, pan, {}))
            elif a == "medir":
                fase = self._fase((d + h) / 2)[0]
                if fase == "mide":
                    ev.append((d + (h - d) * (0.05 / 0.28), "regla", 0.7, pan, {"semilla": reglas}))
                    reglas += 1
                elif fase == "mide2":
                    ev.append((d + (h - d) * (0.03 / 0.25), "regla", 0.7, pan, {"semilla": reglas}))
                    reglas += 1
            elif a == "sacar_clavo":
                ev.append((d + (h - d) * (0.06 / 0.17), "crujido", 0.25, pan, {"semilla": 20 + reglas // 2}))
            elif a == "poner_clavo":
                ev.append((d + (h - d) * (0.14 / 0.30), "bola", 0.35, pan, {}))
            elif a == "suspirar":
                ev.append((d, "suspiro", 0.9, pan - 0.05, {"dur": 1.1}))
        return ev


def p_toc(ac, tor):
    """Instante del toc en el que se tuerce el clavo."""
    return ac["partes"][tor["parte"]]["tocs_s"][tor["toc"] - 1]


def regla(lz: Lienzo, centro, largo=120):
    from .lienzo import TINTA

    x, y = centro
    lz.poligono([(x - 8, y - largo / 2), (x + 8, y - largo / 2), (x + 8, y + largo / 2), (x - 8, y + largo / 2)],
                relleno=BLANCO)
    for j in range(1, int(largo // 12)):
        yy = y - largo / 2 + j * 12
        lz.linea([(x - 8, yy), (x - (1 if j % 5 else -3), yy)], 1.6, TINTA, puntas=False)


TIPOS = {"hacedor": Muneco, "perfeccionista": Muneco, "martillo_hacedor": MartilloVivo,
         "martillo_perfeccionista": MartilloVivo}
