"""Episodios descritos solo con JSON (bloque "guion").

El JSON dice qué escena se usa, qué personaje hay en cada panel, con qué
herramienta, contra qué objeto y qué acciones hace (en segundos del vídeo).
Este módulo valida ese bloque (errores en español) y lo anima.

Formatos:   "pantalla_partida" (arriba y abajo)
Personajes: "hacedor", "perfeccionista"
Acciones:   "golpear", "rendirse", "celebrar"

Ver GUIA_GUIONES.md para todos los campos.
"""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass, replace

from PIL import Image

from . import biblioteca as bib
from . import decorado as dec
from . import personajes as pj
from .config import _NUM, _validar_objeto
from .lienzo import ESCALA, Lienzo, fondo, tenue
from .motor import EpisodioMotor
from .personajes import Pose
from .tiempo import entra, lerp, limitar, sale, suave, tramo

ALTO_PANEL = 960
SUELO = bib.SUELO
FORMATOS = ["pantalla_partida"]
PERSONAJES = ["hacedor", "perfeccionista"]
ACCIONES = ["golpear", "rendirse", "celebrar"]
_COLORES = ["verde", "rojo", "amarillo", "azul"]

# --- Esquema del bloque "guion" ------------------------------------------------
_OBJETO = {
    "tipo": {"tipo": str, "opciones": list(bib.OBJETOS)},
    "golpes_para_partir": {"tipo": int, "min": 1, "max": 999},
    "brillo": {"tipo": str, "opciones": _COLORES, "opcional": True},
}
_CONTADOR = {"color_final": {"tipo": str, "opciones": _COLORES + ["blanco"], "opcional": True}}
_PANEL = {
    "personaje": {"tipo": str, "opciones": PERSONAJES},
    "herramienta": {"tipo": str, "opciones": list(bib.HERRAMIENTAS) + ["ninguna"], "opcional": True},
    "objeto": {"tipo": dict, "campos": _OBJETO, "opcional": True},
    "contador": {"tipo": dict, "campos": _CONTADOR, "opcional": True},
    "acciones": {"tipo": list},
}
_GUION = {
    "formato": {"tipo": str, "opciones": FORMATOS},
    "escena": {"tipo": str, "opciones": list(bib.ESCENAS)},
    "gancho": {"tipo": str, "opciones": ["arriba", "centro"], "opcional": True},
    "arriba": {"tipo": dict, "campos": _PANEL},
    "abajo": {"tipo": dict, "campos": _PANEL},
}
_ACCION_BASE = {
    "accion": {"tipo": str, "opciones": ACCIONES},
    "desde_s": {"tipo": _NUM, "min": 0, "max": 20},
    "hasta_s": {"tipo": _NUM, "min": 0, "max": 20},
}
_ACCION_EXTRA = {
    "golpear": {"golpes": {"tipo": int, "min": 1, "max": 999},
                "velocidad": {"tipo": str, "opciones": ["rapida", "lenta"]}},
    "rendirse": {},
    "celebrar": {},
}


def validar_guion(datos: dict, errores: list[str]) -> None:
    """Valida el bloque "guion" (se llama desde config.validar)."""
    g = datos.get("guion")
    if not isinstance(g, dict):
        errores.append("'guion' debe ser un objeto { }.")
        return
    n0 = len(errores)
    _validar_objeto(g, _GUION, "guion.", errores)
    if len(errores) > n0:
        return
    t = datos.get("tiempos", {})
    r, A = t.get("rebobinado_fin_s"), t.get("accion_fin_s")
    for nombre in ("arriba", "abajo"):
        panel = g[nombre]
        ruta = f"guion.{nombre}"
        acciones = panel["acciones"]
        if not isinstance(acciones, list) or not acciones:
            errores.append(f"'{ruta}.acciones' debe ser una lista [ ] con al menos una acción.")
            continue
        fin_anterior = None
        for i, ac in enumerate(acciones):
            rac = f"{ruta}.acciones[{i}]"
            if not isinstance(ac, dict):
                errores.append(f"'{rac}' debe ser un objeto {{ }} con \"accion\", \"desde_s\" y \"hasta_s\".")
                continue
            tipo = ac.get("accion")
            esquema = dict(_ACCION_BASE)
            if tipo in _ACCION_EXTRA:
                esquema.update(_ACCION_EXTRA[tipo])
            m0 = len(errores)
            _validar_objeto(ac, esquema, f"{rac}.", errores)
            if len(errores) > m0:
                continue
            d, h = ac["desde_s"], ac["hasta_s"]
            if not d < h:
                errores.append(f"'{rac}': 'hasta_s' ({h}) debe ser mayor que 'desde_s' ({d}).")
            if isinstance(r, (int, float)) and isinstance(A, (int, float)) and not (r <= d and h <= A):
                errores.append(
                    f"'{rac}' va de {d} s a {h} s, pero las acciones tienen que ocurrir entre el final del "
                    f"rebobinado ({r} s) y el final de la acción ({A} s)."
                )
            if fin_anterior is not None and d < fin_anterior:
                errores.append(f"'{rac}' empieza ({d} s) antes de que termine la acción anterior ({fin_anterior} s).")
            fin_anterior = h
            if tipo == "golpear":
                if panel.get("herramienta", "ninguna") == "ninguna":
                    errores.append(f"'{rac}' es \"golpear\", pero '{ruta}.herramienta' no tiene herramienta.")
                if "objeto" not in panel:
                    errores.append(f"'{rac}' es \"golpear\", pero '{ruta}' no tiene 'objeto' al que golpear.")


# --- Animación -------------------------------------------------------------------

@dataclass
class Cuerpo:
    """Estado completo de un personaje en un instante."""
    pose: Pose
    agarre: tuple | None = None  # mano que sujeta la herramienta (None = no la lleva)
    angulo: float = 0.0  # ángulo de la herramienta (0 = arriba, 90 = derecha)
    suelo: tuple | None = None  # herramienta tirada en el suelo: (agarre, ángulo)
    escala: float = 1.0  # más pequeño = más lejos
    subida: float = 0.0  # px hacia arriba (alejarse hacia el horizonte)


def mezclar_cuerpo(a: Cuerpo, b: Cuerpo, u: float) -> Cuerpo:
    agarre = a.agarre if b.agarre is None else b.agarre if a.agarre is None else lerp(a.agarre, b.agarre, u)
    return Cuerpo(pose=pj.mezclar(a.pose, b.pose, u), agarre=agarre, angulo=lerp(a.angulo, b.angulo, u),
                  suelo=a.suelo if u < 0.5 else b.suelo, escala=lerp(a.escala, b.escala, u),
                  subida=lerp(a.subida, b.subida, u))


class Panel:
    """Un panel: personaje + herramienta + objeto + acciones, todo en segundos del vídeo."""

    def __init__(self, conf: dict, indice: int):
        self.conf = conf
        self.indice = indice
        self.perfeccionista = conf["personaje"] == "perfeccionista"
        self.herramienta = conf.get("herramienta", "ninguna")
        obj = conf.get("objeto")
        self.roca = bib.Roca() if obj and obj["tipo"] == "roca" else None
        self.golpes_partir = obj["golpes_para_partir"] if obj else 0
        self.brillo = bib.COLORES[obj["brillo"]] if obj and obj.get("brillo") else None
        cont = conf.get("contador")
        self.contador = cont is not None
        self.color_final = bib.COLORES.get(cont.get("color_final")) if cont else None
        self.acciones = conf["acciones"]
        self.x = (self.roca.arriba[0] - 274) if self.roca else 400  # cadera del personaje
        self.golpes = []  # instantes de todos los golpes del panel
        for ac in self.acciones:
            if ac["accion"] == "golpear":
                self.golpes += self._instantes(ac)
        self.t_partida = self.golpes[self.golpes_partir - 1] if self.roca and len(self.golpes) >= self.golpes_partir \
            else None

    @staticmethod
    def _instantes(ac):
        d, h, n = ac["desde_s"], ac["hasta_s"], ac["golpes"]
        if ac["velocidad"] == "lenta":
            return [d + (h - d) * (i + 1) / n for i in range(n)]
        # Rápida: los primeros golpes se ven uno a uno y luego el contador se dispara.
        return [d + (h - d) * (1 - (1 - (i + 1) / n) ** 1.8) for i in range(n)]

    def golpes_hasta(self, ts: float) -> int:
        return bisect.bisect_right(self.golpes, ts + 1e-9)

    # ---------------------------------------------------------------- posturas
    def _de_pie(self, x=None, **kw) -> Pose:
        x = self.x if x is None else x
        y = SUELO - 186
        return Pose(cadera=(x, y), inclinacion=6, mira=1, pie_delante=(x + 26, SUELO - 2),
                    pie_atras=(x - 18, SUELO - 2), mano_delante=(x + 40, y + 92), mano_atras=(x - 30, y + 96),
                    sonrisa=0.2 if self.perfeccionista else 0.7, **kw)

    def _con_herramienta(self, agarre, angulo, inclinacion=6.0, agachado=0.0, **kw) -> Pose:
        p = self._de_pie(**kw)
        p.cadera = (p.cadera[0], p.cadera[1] + agachado)
        p.inclinacion = inclinacion
        d = bib.direccion(angulo)
        p.mano_delante = (agarre[0] + d[0] * 16, agarre[1] + d[1] * 16)
        p.mano_atras = (agarre[0] - d[0] * 14, agarre[1] - d[1] * 14)
        return p

    def preparado(self) -> Cuerpo:
        if self.herramienta == "ninguna":
            return Cuerpo(self._de_pie())
        agarre, ang = (self.x + 80, SUELO - 190), 160.0
        return Cuerpo(self._con_herramienta(agarre, ang, inclinacion=10), agarre, ang)

    def _golpe_en(self, s: float, cansancio: float) -> Cuerpo:
        """Fase del golpe: s=0 mandarria arriba, s=1 impacto en la roca."""
        destino = self.roca.punto_golpe if self.roca else (self.x + 300, SUELO - 200)
        ang_imp, ang_arr = 122.0, -32.0
        d = bib.direccion(ang_imp)
        g_imp = (destino[0] - d[0] * (bib.LARGO_MANDARRIA + 24), destino[1] - d[1] * (bib.LARGO_MANDARRIA + 24))
        g_arr = (self.x - 22, SUELO - 470)
        se = entra(s) if s < 1 else 1.0
        agarre = lerp(g_arr, g_imp, se)
        agarre = (agarre[0] - math.sin(math.pi * se) * 40, agarre[1] - math.sin(math.pi * se) * 30)
        ang = lerp(ang_arr, ang_imp, se)
        p = self._con_herramienta(agarre, ang, inclinacion=lerp(0, 18, se), agachado=24 * se)
        if self.perfeccionista:
            p.sonrisa = lerp(0.1, -0.45, cansancio)
            p.hombros = 8 * cansancio
        else:
            p.sonrisa = 0.55
        p.mirada = (0.9, 0.5)
        return Cuerpo(p, agarre, ang)

    def _golpear(self, ts: float, ac, inicio: Cuerpo) -> Cuerpo:
        golpes = self._instantes(ac)
        cansancio = limitar(self.golpes_hasta(ts) / max(1, self.golpes_partir or len(golpes)))
        if ts < golpes[0]:
            u = tramo(ts, ac["desde_s"], golpes[0])
            if u < 0.55:
                return mezclar_cuerpo(inicio, self._golpe_en(0.0, cansancio), suave(u / 0.55))
            return self._golpe_en((u - 0.55) / 0.45, cansancio)
        j = bisect.bisect_right(golpes, ts) - 1
        if j >= len(golpes) - 1:
            return self._golpe_en(1.0, cansancio)
        t0, t1 = golpes[j], golpes[j + 1]
        amp = limitar((t1 - t0) / 0.5, 0.12, 1.0)
        u = (ts - t0) / (t1 - t0)
        return self._golpe_en(1 - amp * math.sin(math.pi * u ** 0.8), cansancio)

    def _rendirse(self, ts: float, ac, inicio: Cuerpo) -> Cuerpo:
        d0, d1 = ac["desde_s"], ac["hasta_s"]
        u = tramo(ts, d0, d1)
        x0 = self.x
        # 1) Suelta la herramienta: cae al suelo.
        suelo = None
        if inicio.agarre is not None:
            caida = entra(limitar(u / 0.18))
            agarre_suelo, ang_suelo = (x0 + 150, SUELO - 8), -92.0
            if caida < 1:
                tirada = (lerp(inicio.agarre, agarre_suelo, caida), lerp(inicio.angulo, ang_suelo, caida))
            else:
                tirada = (agarre_suelo, ang_suelo)
            suelo = tirada
        # 2) Suspira: hombros abajo, cabeza gacha.
        v = suave(tramo(u, 0.12, 0.45))
        p = self._de_pie(x0)
        p.hombros, p.cabeza = 16 * v, 16 * v
        p.sonrisa, p.parpado = lerp(0.0, -0.75, v), lerp(0.0, 0.5, v)
        p.mano_delante = (x0 + 22, SUELO - 96)
        p.mano_atras = (x0 - 16, SUELO - 92)
        base = mezclar_cuerpo(Cuerpo(inicio.pose, inicio.agarre, inicio.angulo), Cuerpo(p), suave(limitar(u / 0.2)))
        base.agarre = None
        base.suelo = suelo
        if u < 0.47:
            return base
        # 3) Se da la vuelta y se aleja de espaldas, cabizbajo, hacia el fondo.
        w = suave(tramo(u, 0.5, 1.0))
        x = x0 - 230 * w
        fase = 2 * math.pi * 2.25 * tramo(u, 0.5, 1.0)
        paso = 30 * math.sin(fase)
        q = self._de_pie(x)
        q.mira, q.espalda = -1, True
        q.hombros, q.cabeza, q.sonrisa = 16.0, 18.0, -0.75
        q.pie_delante = (x - paso, SUELO - 2 - max(0, math.sin(fase)) * 10)
        q.pie_atras = (x + paso, SUELO - 2 - max(0, -math.sin(fase)) * 10)
        q.mano_delante = (x - 10 - paso * 0.6, SUELO - 94)
        q.mano_atras = (x + 14 + paso * 0.6, SUELO - 92)
        giro = Cuerpo(q, None, 0.0, suelo, escala=lerp(1.0, 0.8, w), subida=60 * w)
        if u < 0.55:
            return mezclar_cuerpo(base, giro, (u - 0.47) / 0.08)
        return giro

    def _celebrar(self, ts: float, ac, inicio: Cuerpo) -> Cuerpo:
        u = tramo(ts, ac["desde_s"], ac["hasta_s"])
        x = self.x
        arriba_g, arriba_a = (x + 8, SUELO - 520), 0.0
        hombro_g, hombro_a = (x + 34, SUELO - 300), -58.0
        bote = abs(math.sin(math.pi * 2 * tramo(u, 0.15, 0.7))) * 34 * (1 - tramo(u, 0.15, 0.7))
        if u < 0.6:
            g, a = arriba_g, arriba_a
        else:
            v = suave(tramo(u, 0.6, 1.0))
            g, a = lerp(arriba_g, hombro_g, v), lerp(arriba_a, hombro_a, v)
        if self.herramienta == "ninguna":
            p = self._de_pie(x)
            p.mano_delante, p.mano_atras = (x + 70, SUELO - 520), (x - 70, SUELO - 510)
            meta = Cuerpo(p)
        else:
            p = self._con_herramienta(g, a, inclinacion=0)
            meta = Cuerpo(p, g, a)
        p.sonrisa, p.mirada, p.cabeza = 1.2, (0.4, -0.4), -6
        p.cadera = (p.cadera[0], p.cadera[1] - bote)
        p.pie_delante = (p.pie_delante[0], p.pie_delante[1] - bote)
        p.pie_atras = (p.pie_atras[0], p.pie_atras[1] - bote)
        p.mano_delante = (p.mano_delante[0], p.mano_delante[1] - bote)
        p.mano_atras = (p.mano_atras[0], p.mano_atras[1] - bote)
        if meta.agarre:
            meta.agarre = (meta.agarre[0], meta.agarre[1] - bote)
        return mezclar_cuerpo(inicio, meta, suave(limitar(u / 0.25)))

    _HACER = {"golpear": _golpear, "rendirse": _rendirse, "celebrar": _celebrar}

    def cuerpo(self, ts: float) -> Cuerpo:
        estado = self.preparado()
        for ac in self.acciones:
            if ts < ac["desde_s"]:
                break
            fin = min(ts, ac["hasta_s"])
            estado = self._HACER[ac["accion"]](self, fin, ac, estado)
        return estado

    # ------------------------------------------------------------------ dibujo
    def separacion(self, ts: float) -> float:
        if self.t_partida is None or ts < self.t_partida:
            return 0.0
        return sale(tramo(ts, self.t_partida, self.t_partida + 0.35))

    def dibujar(self, lz: Lienzo, ts: float):
        c = self.cuerpo(ts)
        if self.roca:
            prog = limitar(self.golpes_hasta(ts) / self.golpes_partir)
            self.roca.dibujar(lz, prog, self.separacion(ts), self.brillo)
            if self.t_partida is not None:
                bib.esquirlas(lz, self.roca.punto_golpe, tramo(ts, self.t_partida, self.t_partida + 0.6),
                              semilla=self.indice)
        if c.suelo is not None:
            bib.mandarria(lz, *c.suelo)
        ancla = (c.pose.cadera[0], SUELO)
        lz2 = pj.a_escala(lz, c.escala, ancla)
        pose = c.pose
        if c.subida:
            dy = -c.subida / c.escala
            pose = replace(pose, cadera=(pose.cadera[0], pose.cadera[1] + dy),
                           mano_delante=(pose.mano_delante[0], pose.mano_delante[1] + dy),
                           mano_atras=(pose.mano_atras[0], pose.mano_atras[1] + dy),
                           pie_delante=(pose.pie_delante[0], pose.pie_delante[1] + dy),
                           pie_atras=(pose.pie_atras[0], pose.pie_atras[1] + dy))

        def en_mano(lz3, e):
            if c.agarre is not None and self.herramienta != "ninguna":
                bib.HERRAMIENTAS[self.herramienta](lz3, c.agarre, c.angulo)

        pj.dibujar(lz2, pose, perfeccionista=self.perfeccionista, en_mano=en_mano)
        # Destello al partirse.
        if self.t_partida is not None and self.brillo is not None:
            u = tramo(ts, self.t_partida, self.t_partida + 0.4)
            if 0 < u < 1:
                cx, cy = self.roca.punto_golpe
                for k in range(10):
                    ang = 2 * math.pi * k / 10
                    r0, r1 = 30 + 80 * u, 50 + 110 * u
                    lz.linea([(cx + math.cos(ang) * r0, cy + math.sin(ang) * r0),
                              (cx + math.cos(ang) * r1, cy + math.sin(ang) * r1)], 5 * (1 - u) + 0.5, self.brillo)

    def color_contador(self, ts: float):
        """Barrita de color bajo el contador cuando el panel ha terminado (o se ha rendido)."""
        if self.color_final is None:
            return None, 0.0
        inicio = self.acciones[-1]["desde_s"] if self.acciones[-1]["accion"] != "golpear" else None
        if inicio is None or ts < inicio:
            return None, 0.0
        return self.color_final, sale(tramo(ts, inicio, inicio + 0.3))

    # ------------------------------------------------------------------- audio
    def eventos(self):
        pan = -0.2 if self.indice == 0 else 0.2
        ev = []
        ultimo = -1.0
        for i, t in enumerate(self.golpes):
            if i + 1 == self.golpes_partir and self.roca:
                ev += [(t, "mandarria", 0.9, pan, {"semilla": i}), (t + 0.02, "crac", 0.95, pan, {}),
                       (t + 0.18, "ding", 0.9, pan, {})]
                ultimo = t
                continue
            if t - ultimo >= 0.06:  # con golpes muy seguidos no se amontonan los sonidos
                ev.append((t, "mandarria", 0.55, pan, {"semilla": i % 7}))
                ultimo = t
            if self.roca and (i + 1) % 20 == 0 and i + 1 < self.golpes_partir:
                ev.append((t + 0.03, "grieta", 0.6, pan, {"semilla": i}))
        for ac in self.acciones:
            d, h = ac["desde_s"], ac["hasta_s"]
            if ac["accion"] == "rendirse":
                ev.append((d + (h - d) * 0.18, "crujido", 0.6, pan, {"semilla": 4}))
                ev.append((d + (h - d) * 0.14, "suspiro", 0.9, pan, {"dur": 1.1}))
                for k in range(4):
                    ev.append((d + (h - d) * (0.55 + k * 0.1), "crujido", 0.16, pan, {"semilla": 20 + k}))
        return ev


class EpisodioGuion(EpisodioMotor):
    """Episodio construido solo a partir del bloque "guion" del JSON."""

    def _preparar(self):
        g = self.ep["guion"]
        self.POS_GANCHO = g.get("gancho", "centro")
        self.paneles = [Panel(g["arriba"], 0), Panel(g["abajo"], 1)]

    def ts(self, a: float) -> float:
        """Tiempo de acción (0..11) a segundos del vídeo."""
        return self.real(a)

    def _decorado(self) -> Image.Image:
        img = Image.new("RGB", (self.ancho * ESCALA, self.alto * ESCALA), fondo())
        escena = bib.ESCENAS[self.ep["guion"]["escena"]]
        self.estrellas = []
        for i in range(2):
            lz = Lienzo(img, 0, i * ALTO_PANEL)
            self.estrellas += escena(lz, i, luna=(i == 0), semilla=i)
        return img

    def _dibujar(self, img: Image.Image, a: float, fase_bucle: float):
        ts = self.ts(a)
        for i, panel in enumerate(self.paneles):
            caja = (0, i * ALTO_PANEL * ESCALA, self.ancho * ESCALA, (i + 1) * ALTO_PANEL * ESCALA)
            sub = img.crop(caja)
            lz = Lienzo(sub, 0, 0)
            dec.estrellas(lz, self.estrellas, i, fase_bucle)
            panel.dibujar(lz, ts)
            if panel.contador:
                color, alfa = panel.color_contador(ts)
                bib.barrita(lz, (1030, 150), color, alfa=alfa)
            img.paste(sub, caja[:2])
            if panel.contador:
                bib.contador(img, panel.golpes_hasta(ts), (1030, 150 + i * ALTO_PANEL))
        Lienzo(img).boceto((0, ALTO_PANEL), (self.ancho, ALTO_PANEL), 3.2, tenue(0.85), semilla=999, amp=1.0)

    def eventos_episodio(self):
        ev = []
        for p in self.paneles:
            ev += p.eventos()
        return ev

    # Para los tests
    def panel(self, nombre: str) -> Panel:
        return self.paneles[0 if nombre == "arriba" else 1]

