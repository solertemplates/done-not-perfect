"""Episodios descritos solo con JSON (bloque "guion").

Formatos:
* "pantalla_partida": dos zonas, "arriba" y "abajo" (1080x960 cada una).
* "escena_unica": una sola zona con los dos personajes juntos.

Cada zona tiene una "escena" (fondo y ambiente), "objetos" y "personajes"
(cada uno con sus "acciones" en segundos del vídeo). Este módulo valida el
bloque (errores en español sencillo) y monta el episodio.

Todas las piezas y sus campos están en GUIA_GUIONES.md.
"""
from __future__ import annotations

from PIL import Image

from . import actores as act
from . import decorado as dec
from . import escena as esc
from . import piezas as pz
from .config import _NUM, _validar_objeto
from .lienzo import ESCALA, Lienzo, fondo, tenue
from .motor import EpisodioMotor

ALTO_PANEL = 960
FORMATOS = ["pantalla_partida", "escena_unica"]
COLORES = ["verde", "rojo", "amarillo", "azul"]
_PUNTO = {"tipo": list, "elemento": _NUM, "largo": 2}

# ------------------------------------------------------------------ ESCENA
_VENTANA = {
    "x": {"tipo": _NUM}, "y": {"tipo": _NUM}, "ancho": {"tipo": _NUM, "min": 40}, "alto": {"tipo": _NUM, "min": 40},
    "estrellas": {"tipo": _NUM, "min": 0, "max": 4, "opcional": True},
    "luna": {"tipo": dict, "opcional": True,
             "campos": {"x": {"tipo": _NUM}, "y": {"tipo": _NUM}, "radio": {"tipo": _NUM, "min": 5, "max": 120}}},
    "semilla": {"tipo": int, "opcional": True},
}
_LAMPARA = {
    "x": {"tipo": _NUM}, "cable": {"tipo": _NUM, "min": 20, "max": 900},
    "luz": {"tipo": bool, "opcional": True}, "techo": {"tipo": _NUM, "opcional": True},
    "luz_hasta_y": {"tipo": _NUM, "opcional": True}, "ancho_luz": {"tipo": _NUM, "min": 60, "opcional": True},
    "semilla": {"tipo": int, "opcional": True},
}
_CARTEL = {
    "dibujo": {"tipo": str, "opciones": esc.CARTELES},
    "x": {"tipo": _NUM}, "y": {"tipo": _NUM}, "ancho": {"tipo": _NUM, "min": 60}, "alto": {"tipo": _NUM, "min": 60},
    "semilla": {"tipo": int, "opcional": True},
}
_ESCENA = {
    "tipo": {"tipo": str, "opciones": esc.ESCENAS},
    "ventana": {"tipo": dict, "campos": _VENTANA, "opcional": True},
    "lampara": {"tipo": dict, "campos": _LAMPARA, "opcional": True},
    "cartel": {"tipo": dict, "campos": _CARTEL, "opcional": True},
    "luna": {"tipo": bool, "opcional": True},
    "siluetas": {"tipo": str, "opciones": esc.SILUETAS, "opcional": True},
    "siluetas_y": {"tipo": _NUM, "opcional": True},
    "semilla": {"tipo": int, "opcional": True},
}

# ----------------------------------------------------------------- OBJETOS
_OBJETOS = {
    "pila_madera": {"x": {"tipo": _NUM}, "tablas": {"tipo": int, "min": 1, "max": 12, "opcional": True},
                    "cae_desde_s": {"tipo": _NUM, "opcional": True}, "cae_hasta_s": {"tipo": _NUM, "opcional": True},
                    "sonido": {"tipo": bool, "opcional": True}},
    "silla": {"inclinacion_inicial_grados": {"tipo": _NUM, "min": 2, "max": 15, "opcional": True},
              "inclinacion_final_grados": {"tipo": _NUM, "min": 0, "max": 10, "opcional": True},
              "se_tuerce_s": {"tipo": _NUM, "opcional": True}},
    "escalera": {"inclinacion_inicial_grados": {"tipo": _NUM, "min": 2, "max": 15, "opcional": True},
                 "inclinacion_final_grados": {"tipo": _NUM, "min": 0, "max": 10, "opcional": True}},
    "caja": {"inclinacion_tapa_grados": {"tipo": _NUM, "min": 0, "max": 8, "opcional": True}},
    "tabla": {"x": {"tipo": _NUM, "opcional": True}, "y": {"tipo": _NUM, "opcional": True},
              "ancho": {"tipo": _NUM, "min": 60, "opcional": True},
              "clavos_tumbados": {"tipo": list, "elemento": _NUM, "opcional": True},
              "clavo_x": {"tipo": _NUM, "opcional": True}},
    "plano": {"boceto": {"tipo": str, "opciones": list(pz.BOCETOS), "opcional": True}},
    "roca": {"golpes_para_partir": {"tipo": int, "min": 1, "max": 999},
             "brillo": {"tipo": str, "opciones": COLORES, "opcional": True}},
    "contador": {"de": {"tipo": str}, "x": {"tipo": _NUM, "opcional": True}, "y": {"tipo": _NUM, "opcional": True},
                 "color_final": {"tipo": str, "opciones": COLORES + ["blanco"], "opcional": True}},
    "marca_ok": {"x": {"tipo": _NUM}, "y": {"tipo": _NUM}, "aparece_s": {"tipo": _NUM},
                 "sonido": {"tipo": bool, "opcional": True}, "paneo": {"tipo": _NUM, "min": -1, "max": 1, "opcional": True}},
    "aro_rojo": {"x": {"tipo": _NUM}, "y": {"tipo": _NUM}, "aparece_s": {"tipo": _NUM},
                 "radio": {"tipo": _NUM, "min": 8, "max": 120, "opcional": True}},
}

# -------------------------------------------------------------- PERSONAJES
MUNECOS = ["hacedor", "perfeccionista"]
OBJETOS_VIVOS = ["martillo_hacedor", "martillo_perfeccionista"]
_PERSONAJE = {
    "tipo": {"tipo": str, "opciones": MUNECOS + OBJETOS_VIVOS},
    "id": {"tipo": str, "opcional": True},
    "herramienta": {"tipo": str, "opciones": ["martillo", "mandarria", "ninguna"], "opcional": True},
    "postura": {"tipo": str, "opciones": ["de_pie", "sentado_suelo"], "opcional": True},
    "x": {"tipo": _NUM, "opcional": True}, "y": {"tipo": _NUM, "opcional": True},
    "espejo": {"tipo": bool, "opcional": True}, "tamano": {"tipo": _NUM, "min": 0.5, "max": 2, "opcional": True},
    "parpadeos_s": {"tipo": list, "elemento": _NUM, "opcional": True},
    "paneo": {"tipo": _NUM, "min": -1, "max": 1, "opcional": True},
    "dx": {"tipo": _NUM, "min": -1000, "max": 1000, "opcional": True},
    "acciones": {"tipo": list},
}

_REF = {"tipo": str}
_OPC = {"opcional": True}


def _o(regla):
    return {**regla, **_OPC}


# Acciones de los muñecos: campos de cada una (además de accion, desde_s y hasta_s).
ACCIONES_MUNECO = {
    "esperar": {},
    "preparar": {"x": _o({"tipo": _NUM})},
    "construir": {"objeto": _REF, "madera": _o(_REF), "primer_golpe_s": {"tipo": _NUM}, "cada_s": {"tipo": _NUM, "min": 0.1},
                  "subida_s": _o({"tipo": _NUM}), "rebote_s": _o({"tipo": _NUM}),
                  "paso_s": _o({"tipo": list, "elemento": _NUM, "largo": 2}), "x_min": _o({"tipo": _NUM}),
                  "x_max": _o({"tipo": _NUM}), "mano_final": _o(_PUNTO), "x_final": _o({"tipo": _NUM}),
                  "mirada": _o(_PUNTO), "vuelo_s": _o({"tipo": _NUM})},
    "sorprenderse": {"x": _o({"tipo": _NUM})},
    "mirar": {"x": _o({"tipo": _NUM})},
    "sentarse": {"objeto": _REF, "x_inicio": _o({"tipo": _NUM})},
    "tambalearse": {"objeto": _REF},
    "martillear": {"golpes_s": {"tipo": list, "elemento": _NUM}, "arregla": _o(_REF), "punto": _o(_PUNTO),
                   "x": _o({"tipo": _NUM}), "agachado": _o({"tipo": _NUM, "min": 0, "max": 90}),
                   "preparar_s": _o({"tipo": _NUM, "min": 0.05}), "levantarse_s": _o({"tipo": _NUM, "min": 0.05}),
                   "mano_final": _o(_PUNTO), "mirada": _o(_PUNTO)},
    "subir": {"objeto": _REF, "nivel": {"tipo": int, "min": 0, "max": 5}, "acercarse_s": _o({"tipo": _NUM, "min": 0}),
              "x_inicio": _o({"tipo": _NUM}), "deja_herramienta": _o({"tipo": bool}), "herramienta_en": _o(_PUNTO)},
    "celebrar": {"estilo": _o({"tipo": str, "opciones": ["sentado", "señalar", "herramienta", "brazos"]}),
                 "objeto": _o(_REF), "punto": _o(_PUNTO)},
    "golpear": {"objeto": _REF, "golpes": {"tipo": int, "min": 1, "max": 999},
                "velocidad": {"tipo": str, "opciones": ["rapida", "lenta"]}},
    "rendirse": {},
    "caminar": {"x": {"tipo": _NUM}, "de_espaldas": _o({"tipo": bool})},
    "dudar": {},
    "suspirar": {},
    "dibujar": {"plano": _REF},
    "medir": {"plano": _REF},
    "borrar": {"plano": _REF},
    "arrugar": {"plano": _REF},
}
_PARTE = {"aparece_s": {"tipo": _NUM}, "tocs_s": {"tipo": list, "elemento": _NUM}}
_TORCIDO = {"parte": {"tipo": int, "min": 0, "max": 9}, "toc": {"tipo": int, "min": 1, "max": 9},
            "sorpresa_hasta_s": {"tipo": _NUM}, "endereza_s": {"tipo": _NUM}}
ACCIONES_OBJETO = {
    "esperar": {},
    "preparar": {},
    "construir": {"objeto": _REF, "partes": {"tipo": list}, "clavo_torcido": _o({"tipo": dict, "campos": _TORCIDO})},
    "caminar": {"x": {"tipo": _NUM}, "y": _o({"tipo": _NUM}), "angulo": _o({"tipo": _NUM}),
                "espejo": _o({"tipo": bool}), "salto": _o({"tipo": _NUM, "min": 0, "max": 300})},
    "celebrar": {},
    "mirar": {},
    "colocar_clavo": {"objeto": _REF},
    "medir": {"objeto": _REF},
    "sacar_clavo": {"objeto": _REF},
    "poner_clavo": {"objeto": _REF},
    "dudar": {},
    "suspirar": {},
}
# Qué tipo de objeto espera cada referencia.
_REFS = {
    ("construir", "objeto"): ("silla", "escalera", "caja"), ("construir", "madera"): ("pila_madera",),
    ("sentarse", "objeto"): ("silla",), ("tambalearse", "objeto"): ("silla", "escalera"),
    ("martillear", "arregla"): ("silla", "escalera"), ("subir", "objeto"): ("escalera",),
    ("celebrar", "objeto"): ("silla",), ("golpear", "objeto"): ("roca",),
    ("dibujar", "plano"): ("plano",), ("medir", "plano"): ("plano",), ("borrar", "plano"): ("plano",),
    ("arrugar", "plano"): ("plano",), ("colocar_clavo", "objeto"): ("tabla",), ("medir", "objeto"): ("tabla",),
    ("sacar_clavo", "objeto"): ("tabla",), ("poner_clavo", "objeto"): ("tabla",),
}

_ZONA = {
    "escena": {"tipo": dict, "campos": _ESCENA},
    "objetos": {"tipo": list, "opcional": True},
    "personajes": {"tipo": list},
}
_GUION = {
    "formato": {"tipo": str, "opciones": FORMATOS},
    "gancho": {"tipo": str, "opciones": ["arriba", "centro"], "opcional": True},
    "cierre_y": {"tipo": _NUM, "min": 200, "max": 1800, "opcional": True},
}


# ============================================================ VALIDACIÓN
def validar_guion(datos: dict, errores: list[str]) -> None:
    g = datos.get("guion")
    if not isinstance(g, dict):
        errores.append("'guion' debe ser un objeto { }.")
        return
    formato = g.get("formato")
    if formato not in FORMATOS:  # sin formato válido no se puede saber qué más debe haber
        _validar_objeto({"formato": formato}, {"formato": _GUION["formato"]}, "guion.", errores)
        return
    esquema = dict(_GUION)
    if formato == "pantalla_partida":
        esquema["arriba"] = {"tipo": dict, "campos": None}
        esquema["abajo"] = {"tipo": dict, "campos": None}
    elif formato == "escena_unica":
        esquema.update(_ZONA)
    n0 = len(errores)
    _validar_objeto(g, esquema, "guion.", errores)
    if len(errores) > n0:
        return
    t = datos.get("tiempos", {})
    limites = (t.get("rebobinado_fin_s"), t.get("accion_fin_s"))
    if formato == "pantalla_partida":
        zonas = [("guion.arriba", g["arriba"]), ("guion.abajo", g["abajo"])]
        for ruta, z in zonas:
            m0 = len(errores)
            _validar_objeto(z, _ZONA, ruta + ".", errores)
            if len(errores) == m0:
                _validar_zona(z, ruta, limites, errores, pantalla_partida=True)
    else:
        zonas = [("guion", g)]
        _validar_zona(g, "guion", limites, errores, pantalla_partida=False)
    carteles = sum(1 for _, z in zonas if isinstance(z.get("escena"), dict) and "cartel" in z["escena"])
    if carteles > 1:
        errores.append("Solo puede haber 1 cartel en todo el episodio (regla de la serie), y hay "
                       f"{carteles}. Quita el 'cartel' de una de las escenas.")


def _validar_zona(z, ruta, limites, errores, pantalla_partida):
    tipo_escena = z["escena"]["tipo"]
    if tipo_escena == "taller" and pantalla_partida:
        errores.append(f"'{ruta}.escena.tipo' es \"taller\", que solo sirve con \"formato\": \"escena_unica\".")
    objetos = {}
    for i, o in enumerate(z.get("objetos", [])):
        r = f"{ruta}.objetos[{i}]"
        if not isinstance(o, dict):
            errores.append(f"'{r}' debe ser un objeto {{ }} con \"tipo\".")
            continue
        esquema = {"tipo": {"tipo": str, "opciones": list(_OBJETOS)}, "id": _o({"tipo": str}),
                   "dx": _o({"tipo": _NUM, "min": -1000, "max": 1000})}
        if o.get("tipo") in _OBJETOS:
            esquema.update(_OBJETOS[o["tipo"]])
        m0 = len(errores)
        _validar_objeto(o, esquema, r + ".", errores)
        if len(errores) > m0:
            continue
        ident = o.get("id", o["tipo"])
        if ident in objetos:
            errores.append(f"En '{ruta}' hay dos objetos con el id \"{ident}\". Ponles un \"id\" distinto a cada uno.")
        objetos[ident] = o["tipo"]
    personajes = []
    for i, p in enumerate(z["personajes"]):
        r = f"{ruta}.personajes[{i}]"
        if not isinstance(p, dict):
            errores.append(f"'{r}' debe ser un objeto {{ }} con \"tipo\" y \"acciones\".")
            continue
        m0 = len(errores)
        _validar_objeto(p, _PERSONAJE, r + ".", errores)
        if len(errores) > m0:
            continue
        personajes.append(p.get("id", p["tipo"]))
        _validar_acciones(p, r, objetos, limites, errores)
    for i, o in enumerate(z.get("objetos", [])):
        if isinstance(o, dict) and o.get("tipo") == "contador" and o.get("de") not in personajes:
            errores.append(f"'{ruta}.objetos[{i}].de' es \"{o.get('de')}\", pero en esa zona no hay ningún personaje "
                           f"con ese id. Personajes: {', '.join(personajes) or 'ninguno'}.")


def _validar_acciones(p, ruta, objetos, limites, errores):
    es_objeto = p["tipo"] in OBJETOS_VIVOS
    catalogo = ACCIONES_OBJETO if es_objeto else ACCIONES_MUNECO
    acciones = p["acciones"]
    if not acciones:
        errores.append(f"'{ruta}.acciones' necesita al menos una acción.")
        return
    r0, A = limites
    fin_anterior = None
    for i, ac in enumerate(acciones):
        r = f"{ruta}.acciones[{i}]"
        if not isinstance(ac, dict):
            errores.append(f"'{r}' debe ser un objeto {{ }} con \"accion\", \"desde_s\" y \"hasta_s\".")
            continue
        esquema = {"accion": {"tipo": str, "opciones": list(catalogo)},
                   "desde_s": {"tipo": _NUM, "min": 0, "max": 20}, "hasta_s": {"tipo": _NUM, "min": 0, "max": 20}}
        nombre = ac.get("accion")
        if nombre not in catalogo:  # primero, que diga qué acción no existe (y cuál quería decir)
            _validar_objeto({"accion": nombre}, {"accion": esquema["accion"]}, r + ".", errores)
            continue
        esquema.update(catalogo[nombre])
        m0 = len(errores)
        _validar_objeto(ac, esquema, r + ".", errores)
        if len(errores) > m0:
            continue
        d, h = ac["desde_s"], ac["hasta_s"]
        if not d < h:
            errores.append(f"'{r}': 'hasta_s' ({h}) tiene que ser mayor que 'desde_s' ({d}).")
        if isinstance(r0, (int, float)) and isinstance(A, (int, float)) and not (r0 <= d and h <= A):
            errores.append(f"'{r}' va de {d} s a {h} s, pero las acciones tienen que pasar entre el final del "
                           f"rebobinado ({r0} s) y el final de la acción ({A} s).")
        if fin_anterior is not None and d < fin_anterior:
            errores.append(f"'{r}' empieza ({d} s) antes de que termine la acción anterior ({fin_anterior} s).")
        fin_anterior = h
        for campo in ("objeto", "madera", "arregla", "plano"):
            if campo in ac:
                validos = _REFS.get((nombre, campo))
                tipo = objetos.get(ac[campo])
                if tipo is None:
                    errores.append(f"'{r}.{campo}' es \"{ac[campo]}\", pero no hay ningún objeto con ese id en la zona. "
                                   f"Objetos: {', '.join(objetos) or 'ninguno'}.")
                elif validos and tipo not in validos:
                    errores.append(f"'{r}.{campo}' apunta a un objeto \"{tipo}\", pero \"{nombre}\" necesita: "
                                   f"{', '.join(validos)}.")
        if not es_objeto:
            herr = p.get("herramienta", "ninguna")
            if nombre == "golpear" and herr != "mandarria":
                errores.append(f"'{r}' es \"golpear\": el personaje necesita \"herramienta\": \"mandarria\".")
            if nombre in ("construir", "martillear", "preparar") and herr != "martillo":
                errores.append(f"'{r}' es \"{nombre}\": el personaje necesita \"herramienta\": \"martillo\".")
            if nombre in ("dibujar", "medir", "borrar", "arrugar") and p.get("postura") != "sentado_suelo":
                errores.append(f"'{r}' es \"{nombre}\": el personaje tiene que tener \"postura\": \"sentado_suelo\".")
        elif nombre == "construir":
            for j, parte in enumerate(ac["partes"]):
                m0 = len(errores)
                if not isinstance(parte, dict):
                    errores.append(f"'{r}.partes[{j}]' debe ser un objeto {{ }} con \"aparece_s\" y \"tocs_s\".")
                    continue
                _validar_objeto(parte, _PARTE, f"{r}.partes[{j}].", errores)
            if len(ac["partes"]) != len(pz.PIEZAS_CAJA):
                errores.append(f"'{r}.partes' debe tener {len(pz.PIEZAS_CAJA)} partes (las de la caja), y tiene "
                               f"{len(ac['partes'])}.")


# ============================================================== EPISODIO
class EpisodioGuion(EpisodioMotor):
    """Episodio construido solo a partir del bloque "guion" del JSON."""

    def _preparar(self):
        g = self.ep["guion"]
        self.formato = g["formato"]
        self.POS_GANCHO = g.get("gancho", "centro" if self.formato == "pantalla_partida" else "arriba")
        self.Y_TARJETA = g.get("cierre_y", 960)
        if self.formato == "pantalla_partida":
            confs = [g["arriba"], g["abajo"]]
            self.oy_decorado = [0, ALTO_PANEL]
            self.oy_dibujo = [0, 0]  # cada panel se dibuja recortado
        else:
            confs = [g]
            oy = 0 if g["escena"]["tipo"] == "taller" else 480
            self.oy_decorado, self.oy_dibujo = [oy], [oy]
        self.zonas = []
        for indice, conf in enumerate(confs):
            objetos = {}
            for oc in conf.get("objetos", []):
                o = pz.TIPOS[oc["tipo"]](oc)
                o.indice = indice
                objetos[o.id] = o
            actores = [act.TIPOS[pc["tipo"]](pc, indice, objetos) for pc in conf["personajes"]]
            self.zonas.append((conf, objetos, actores))

    def _decorado(self) -> Image.Image:
        img = Image.new("RGB", (self.ancho * ESCALA, self.alto * ESCALA), fondo())
        self.estrellas = esc.construir(img, [(conf["escena"], self.oy_decorado[i], i)
                                             for i, (conf, _, _) in enumerate(self.zonas)])
        return img

    def _dibujar_zona(self, lz, indice, ts, fase_bucle):
        _, objetos, actores = self.zonas[indice]
        dec.estrellas(lz, self.estrellas, indice, fase_bucle)

        def mover(cosa):
            return Lienzo(lz.img, lz.ox + cosa.dx, lz.oy, escala=lz.s) if cosa.dx else lz

        for o in objetos.values():
            o.dibujar(mover(o), ts)
        for a in actores:
            a.dibujar(mover(a), ts)
        for o in objetos.values():
            o.dibujar_delante(mover(o), ts)

    def _dibujar(self, img: Image.Image, a: float, fase_bucle: float):
        ts = self.real(a)
        if self.formato == "pantalla_partida":
            for i in range(2):
                caja = (0, i * ALTO_PANEL * ESCALA, self.ancho * ESCALA, (i + 1) * ALTO_PANEL * ESCALA)
                sub = img.crop(caja)
                self._dibujar_zona(Lienzo(sub, 0, 0), i, ts, fase_bucle)
                img.paste(sub, caja[:2])
                for o in self.zonas[i][1].values():
                    o.texto(img, ts, i * ALTO_PANEL)
            Lienzo(img).boceto((0, ALTO_PANEL), (self.ancho, ALTO_PANEL), 3.2, tenue(0.85), semilla=999, amp=1.0)
        else:
            oy = self.oy_dibujo[0]
            self._dibujar_zona(Lienzo(img, 0, oy), 0, ts, fase_bucle)
            for o in self.zonas[0][1].values():
                o.texto(img, ts, oy)

    def eventos_episodio(self):
        ev = []
        for _, objetos, actores in self.zonas:
            for o in objetos.values():
                ev += o.eventos()
            for a in actores:
                ev += a.eventos()
        return ev

    # Para los tests
    def actor(self, zona: int, ident: str):
        return next(a for a in self.zonas[zona][2] if a.id == ident)

    def objeto(self, zona: int, ident: str):
        return self.zonas[zona][1][ident]
