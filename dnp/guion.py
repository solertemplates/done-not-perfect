"""Episodios descritos solo con JSON (bloque "guion").

Formatos:
* "pantalla_partida": dos zonas, "arriba" y "abajo" (1080x960 cada una).
* "escena_unica": una sola zona con los dos personajes juntos.
* "franjas": de 3 a 6 franjas apiladas ("franjas": [zona, zona, ...]), cada una con su muñeco.

Los personajes pueden llevar una "etiqueta" (palabra grande, p. ej. DONE) y cada zona
puede tener "marcadores" (una línea con números que cambian, p. ej. "HITS {g} · DONE {d}").

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
from . import rotulos as rot
from .config import _NUM, _validar_objeto
from .lienzo import ESCALA, Lienzo, fondo, tenue
from .motor import EpisodioMotor

ALTO_PANEL = 960
FORMATOS = ["pantalla_partida", "escena_unica", "franjas"]
VISTA_FRANJA = (230, 930)  # parte de la zona (en y) que se ve en cada franja
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
    "farolas": {"tipo": list, "elemento": _NUM, "opcional": True},
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
    "kiosco": {"x": {"tipo": _NUM}, "ancho": {"tipo": _NUM, "min": 180, "max": 420, "opcional": True},
               "toldo": {"tipo": str, "opciones": list(pz.TOLDOS), "opcional": True},
               "cola": {"tipo": str, "opciones": ["derecha", "izquierda"], "opcional": True}},
    "limonada": {"kiosco": {"tipo": str}, "stock": {"tipo": int, "min": 0, "max": 20, "opcional": True},
                 "reponer": {"tipo": list, "opcional": True}},
    "cartel_precio": {"x": {"tipo": _NUM}, "y": {"tipo": _NUM}, "precio": {"tipo": str, "max_len": 6},
                      "cambios": {"tipo": list, "opcional": True}, "tachado_s": {"tipo": _NUM, "opcional": True},
                      "borde": {"tipo": str, "opciones": ["ambar", "naranja", "rosa_neon", "violeta"], "opcional": True}},
    "monedas": {"x": {"tipo": _NUM}, "y": {"tipo": _NUM, "opcional": True},
                "cantidad": {"tipo": int, "min": 1, "max": 24, "opcional": True}},
    "bolsa_dinero": {"x": {"tipo": _NUM}, "y": {"tipo": _NUM, "opcional": True}, "kiosco": {"tipo": str, "opcional": True},
                     "monedas": {"tipo": int, "min": 0, "max": 30, "opcional": True},
                     "detalle": {"tipo": dict, "opcional": True, "campos": {
                         "color": {"tipo": str, "opciones": ["verde", "rojo"]}, "aparece_s": {"tipo": _NUM}}}},
    "clientes": {"kiosco": {"tipo": str}, "cantidad": {"tipo": int, "min": 1, "max": 8, "opcional": True},
                 "movimientos": {"tipo": list, "opcional": True}},
}
# Objetos que apuntan a un kiosco (campo "kiosco").
_APUNTAN_A_KIOSCO = ("limonada", "bolsa_dinero", "clientes")

# -------------------------------------------------------------- PERSONAJES
MUNECOS = ["hacedor", "perfeccionista"]
OBJETOS_VIVOS = ["martillo_hacedor", "martillo_perfeccionista"]
_PERSONAJE = {
    "tipo": {"tipo": str, "opciones": MUNECOS + OBJETOS_VIVOS},
    "id": {"tipo": str, "opcional": True},
    "herramienta": {"tipo": str, "opciones": ["martillo", "mandarria", "ninguna"], "opcional": True},
    "postura": {"tipo": str, "opciones": ["de_pie", "sentado_suelo"], "opcional": True},
    "mira": {"tipo": str, "opciones": ["izquierda", "derecha"], "opcional": True},
    "x": {"tipo": _NUM, "opcional": True}, "y": {"tipo": _NUM, "opcional": True},
    "espejo": {"tipo": bool, "opcional": True}, "tamano": {"tipo": _NUM, "min": 0.5, "max": 2, "opcional": True},
    "parpadeos_s": {"tipo": list, "elemento": _NUM, "opcional": True},
    "paneo": {"tipo": _NUM, "min": -1, "max": 1, "opcional": True},
    "dx": {"tipo": _NUM, "min": -1000, "max": 1000, "opcional": True},
    "etiqueta": {"tipo": dict, "opcional": True, "campos": {
        "texto": {"tipo": str, "max_len": 14},
        "color_final": {"tipo": str, "opciones": COLORES, "opcional": True},
        "desde_s": {"tipo": _NUM, "opcional": True},
        "x": {"tipo": _NUM, "opcional": True}, "y": {"tipo": _NUM, "opcional": True},
        "tamano": {"tipo": _NUM, "min": 30, "max": 160, "opcional": True}}},
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
    "vender": {"kiosco": _REF, "veces": _o({"tipo": int, "min": 1, "max": 20})},
    "burlarse": {"hacia": _o({"tipo": str, "opciones": ["izquierda", "derecha"]})},
    "comprar_todo": {"kiosco": _REF, "pago": _o({"tipo": int, "min": 1, "max": 30}), "x": _o({"tipo": _NUM})},
    "cambiar_precio": {"cartel": _REF, "precio": {"tipo": str, "max_len": 6}},
    "contar_dinero": {},
    "encogerse": {},
    "cruzar_brazos": {},
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
    ("vender", "kiosco"): ("kiosco",), ("comprar_todo", "kiosco"): ("kiosco",),
    ("cambiar_precio", "cartel"): ("cartel_precio",),
}

_ZONA = {
    "escena": {"tipo": dict, "campos": _ESCENA},
    "objetos": {"tipo": list, "opcional": True},
    "personajes": {"tipo": list},
    "marcadores": {"tipo": list, "opcional": True},
}
_MARCADOR = {"texto": {"tipo": str, "max_len": 40}, "valores": {"tipo": dict, "opcional": True, "campos": None},
             "x": {"tipo": _NUM, "opcional": True}, "y": {"tipo": _NUM, "opcional": True},
             "tamano": {"tipo": _NUM, "min": 20, "max": 80, "opcional": True}}
_VALOR = {"de": {"tipo": str, "opcional": True}, "golpes": {"tipo": bool, "opcional": True},
          "ventas": {"tipo": bool, "opcional": True}, "dinero": {"tipo": bool, "opcional": True},
          "cuenta": {"tipo": list, "elemento": str, "opcional": True}, "fijo": {"tipo": int, "opcional": True},
          "max": {"tipo": int, "min": 0, "opcional": True},
          "color": {"tipo": str, "opciones": COLORES, "opcional": True}}
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
    else:
        esquema["franjas"] = {"tipo": list}
    n0 = len(errores)
    _validar_objeto(g, esquema, "guion.", errores)
    if len(errores) > n0:
        return
    t = datos.get("tiempos", {})
    limites = (t.get("rebobinado_fin_s"), t.get("accion_fin_s"))
    if formato in ("pantalla_partida", "franjas"):
        if formato == "pantalla_partida":
            zonas = [("guion.arriba", g["arriba"]), ("guion.abajo", g["abajo"])]
        else:
            if not 3 <= len(g["franjas"]) <= 6:
                errores.append(f"'guion.franjas' debe tener de 3 a 6 franjas, y tiene {len(g['franjas'])}.")
                return
            zonas = [(f"guion.franjas[{i}]", z) for i, z in enumerate(g["franjas"])]
            for ruta, z in zonas:
                if not isinstance(z, dict):
                    errores.append(f"'{ruta}' debe ser un objeto {{ }} con \"escena\" y \"personajes\".")
            if len(errores) > n0:
                return
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
    for i, o in enumerate(z.get("objetos", [])):
        if not isinstance(o, dict):
            continue
        r = f"{ruta}.objetos[{i}]"
        if o.get("tipo") in _APUNTAN_A_KIOSCO and o.get("kiosco") is not None:
            if objetos.get(o["kiosco"]) != "kiosco":
                errores.append(f"'{r}.kiosco' es \"{o['kiosco']}\", pero no hay ningún kiosco con ese id en la zona.")
        for campo, sub in (("reponer", {"desde_s": {"tipo": _NUM}, "cantidad": {"tipo": int, "min": 1, "max": 20}}),
                           ("cambios", {"desde_s": {"tipo": _NUM}, "precio": {"tipo": str, "max_len": 6}}),
                           ("movimientos", {"desde_s": {"tipo": _NUM}, "kiosco": {"tipo": str}})):
            for j, item in enumerate(o.get(campo, []) if isinstance(o.get(campo), list) else []):
                if not isinstance(item, dict):
                    errores.append(f"'{r}.{campo}[{j}]' debe ser un objeto {{ }}.")
                    continue
                _validar_objeto(item, sub, f"{r}.{campo}[{j}].", errores)
                if campo == "movimientos" and objetos.get(item.get("kiosco")) != "kiosco":
                    errores.append(f"'{r}.movimientos[{j}].kiosco' es \"{item.get('kiosco')}\", "
                                   "pero no hay ningún kiosco con ese id en la zona.")
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
    for i, m in enumerate(z.get("marcadores", [])):
        r = f"{ruta}.marcadores[{i}]"
        if not isinstance(m, dict):
            errores.append(f"'{r}' debe ser un objeto {{ }} con \"texto\".")
            continue
        m0 = len(errores)
        _validar_objeto(m, _MARCADOR, r + ".", errores)
        if len(errores) > m0:
            continue
        valores = m.get("valores", {})
        import re

        for nombre in re.findall(r"\{(\w+)\}", m["texto"]):
            if nombre not in valores:
                errores.append(f"'{r}.texto' usa {{{nombre}}}, pero no está en 'valores'.")
        for nombre, v in valores.items():
            if not isinstance(v, dict):
                errores.append(f"'{r}.valores.{nombre}' debe ser un objeto {{ }}.")
                continue
            _validar_objeto(v, _VALOR, f"{r}.valores.{nombre}.", errores)
            if "fijo" not in v and v.get("de") not in set(personajes) | set(objetos):
                errores.append(f"'{r}.valores.{nombre}.de' es \"{v.get('de')}\", pero no hay ningún personaje "
                               "ni objeto con ese id en la zona.")
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
        for campo in ("objeto", "madera", "arregla", "plano", "kiosco", "cartel"):
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
        self.leccion = self.textos.get("leccion")
        self.margen = rot.ALTO_LECCION if self.leccion else 0  # franja de arriba para la lección
        if self.formato == "pantalla_partida":
            confs = [g["arriba"], g["abajo"]]
            self.oy_decorado = [0, ALTO_PANEL]
            self.oy_dibujo = [0, 0]  # cada panel se dibuja recortado
        elif self.formato == "franjas":
            confs = g["franjas"]
            n = len(confs)
            alto = (self.alto - self.margen) / n
            self.regiones = [(self.margen + i * alto, self.margen + (i + 1) * alto) for i in range(n)]
            self.oy_decorado = self.oy_dibujo = [0] * n
        else:
            confs = [g]
            oy = 0 if g["escena"]["tipo"] == "taller" else 700  # suelo en y=1500: el cielo llena la parte de arriba
            self.oy_decorado, self.oy_dibujo = [oy], [oy]
        self.zonas = []
        for indice, conf in enumerate(confs):
            objetos = {}
            for oc in conf.get("objetos", []):
                o = pz.TIPOS[oc["tipo"]](oc)
                o.indice = indice
                objetos[o.id] = o
            for o in objetos.values():
                o.enlazar(objetos)
            actores = [act.TIPOS[pc["tipo"]](pc, indice, objetos) for pc in conf["personajes"]]
            if indice == 0 and self.formato == "pantalla_partida" and self.margen:
                for o in objetos.values():  # el contador baja para dejar sitio a la lección
                    if isinstance(o, pz.Contador) and o.y < 300:
                        o.y += self.margen - 40
            self.zonas.append((conf, objetos, actores))
        self.marcadores = [[rot.Marcador(m, objetos, actores) for m in conf.get("marcadores", [])]
                           for conf, objetos, actores in self.zonas]

    def _decorado(self) -> Image.Image:
        img = Image.new("RGB", (self.ancho * ESCALA, self.alto * ESCALA), fondo())
        if self.formato == "franjas":
            self.estrellas = []
            for i, (y0, y1) in enumerate(self.regiones):
                lz = self._lienzo_franja(img, i)
                self.estrellas += _decorado_franja(lz, i, self._ancho_logico(i), self.ox_franja(i))
            return img
        if self.formato == "pantalla_partida":
            regiones = [(0, ALTO_PANEL), (ALTO_PANEL, 2 * ALTO_PANEL)]
        else:
            regiones = [(0, self.alto)]
        self.estrellas = esc.construir(img, [(conf["escena"], self.oy_decorado[i], i, regiones[i])
                                             for i, (conf, _, _) in enumerate(self.zonas)])
        return img

    # ---------------------------------------------------------------- franjas
    def _k(self, i):
        """Escala de la franja: cabe la acción a lo alto y la roca no se sale por la derecha."""
        y0, y1 = self.regiones[i]
        return min((y1 - y0) / (VISTA_FRANJA[1] - VISTA_FRANJA[0]), 0.58)

    def _ancho_logico(self, i):
        return self.ancho / self._k(i)

    def ox_franja(self, i):
        """Desplazamiento para que la acción (muñeco y roca) quede a la derecha de la etiqueta."""
        return 690 / self._k(i) - 280  # el muñeco (x≈280) queda en x=690 de la pantalla

    def _lienzo_franja(self, img, i):
        y0, y1 = self.regiones[i]
        k = self._k(i)
        centro = (VISTA_FRANJA[0] + VISTA_FRANJA[1]) / 2
        return Lienzo(img, self.ox_franja(i), (y0 + y1) / 2 / k - centro, escala=ESCALA * k)

    def _zonas_color(self):
        if self.formato == "franjas":
            return [(y0, y1, None) for y0, y1 in self.regiones]
        if self.formato == "pantalla_partida":
            regiones = [(0, ALTO_PANEL), (ALTO_PANEL, 2 * ALTO_PANEL)]
        else:
            regiones = [(0, self.alto)]
        return [(y0, y1, esc.horizonte(conf["escena"], self.oy_decorado[i]))
                for i, ((conf, _, _), (y0, y1)) in enumerate(zip(self.zonas, regiones))]

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
        if self.formato == "franjas":
            for i, (y0, y1) in enumerate(self.regiones):
                caja = (0, int(y0 * ESCALA), self.ancho * ESCALA, int(y1 * ESCALA))
                sub = img.crop(caja)
                lz = self._lienzo_franja(sub, i)
                lz.oy -= y0 / self._k(i)
                self._dibujar_zona(lz, i, ts, fase_bucle)
                img.paste(sub, caja[:2])
                h = y1 - y0
                for a_ in self.zonas[i][2]:
                    if "etiqueta" in a_.conf:
                        rot.etiqueta(img, a_.conf["etiqueta"], ts, (40, y0 + h * 0.3), min(88, h * 0.2), "lm", 480)
                for m in self.marcadores[i]:
                    m.dibujar(img, ts, (40, y0 + h * 0.62), min(40, h * 0.1), "lm")
                if i:
                    Lienzo(img).boceto((0, y0), (self.ancho, y0), 2.4, tenue(0.7), semilla=990 + i, amp=1.0)
            return
        if self.formato == "pantalla_partida":
            for i in range(2):
                caja = (0, i * ALTO_PANEL * ESCALA, self.ancho * ESCALA, (i + 1) * ALTO_PANEL * ESCALA)
                sub = img.crop(caja)
                self._dibujar_zona(Lienzo(sub, 0, 0), i, ts, fase_bucle)
                img.paste(sub, caja[:2])
                for o in self.zonas[i][1].values():
                    o.texto(img, ts, i * ALTO_PANEL)
                self._rotulos(img, i, ts, i * ALTO_PANEL)
            Lienzo(img).boceto((0, ALTO_PANEL), (self.ancho, ALTO_PANEL), 3.2, tenue(0.85), semilla=999, amp=1.0)
        else:
            oy = self.oy_dibujo[0]
            self._dibujar_zona(Lienzo(img, 0, oy), 0, ts, fase_bucle)
            for o in self.zonas[0][1].values():
                o.texto(img, ts, oy)
            self._rotulos(img, 0, ts, oy)

    def _rotulos(self, img, i, ts, oy):
        """Etiquetas de los personajes y marcadores de la zona (en coordenadas de zona + oy)."""
        partida = self.formato == "pantalla_partida"
        for a_ in self.zonas[i][2]:
            e = a_.conf.get("etiqueta")
            if not e:
                continue
            if partida:
                # abajo, un poco más baja para que no la tape la tarjeta del centro (gancho y cierre)
                pos = (e.get("x", 50), e.get("y", 110 + (self.margen - 20 if i == 0 else 65)) + oy)
                rot.etiqueta(img, e, ts, pos, e.get("tamano", 104), "lm", 640)
            else:
                tam = e.get("tamano", 84)
                tam = min(tam, tam * 520 / max(1.0, rot.ancho_texto(e["texto"], tam)))
                medio = rot.ancho_texto(e["texto"], tam) / 2
                x = min(max(e.get("x", getattr(a_, "x", 540)), 30 + medio), self.ancho - 30 - medio)
                rot.etiqueta(img, e, ts, (x, e.get("y", 120) + oy), tam, "mm", 520)
        for m in self.marcadores[i]:
            c = m.conf
            pos = (c.get("x", 540), c.get("y", 885) + oy)
            m.dibujar(img, ts, pos, c.get("tamano", 40))

    def eventos_episodio(self):
        ev = []
        for _, objetos, actores in self.zonas:
            for o in objetos.values():
                ev += o.eventos()
            for a in actores:
                ev += a.eventos()
        if self.formato == "franjas":  # muchas rocas a la vez: los golpes, más bajos para no saturar
            f = len(self.zonas) ** -0.5
            ev = [(t, n, g * f if n in ("mandarria", "grieta") else g, p, x) for t, n, g, p, x in ev]
        return ev

    # Para los tests
    def actor(self, zona: int, ident: str):
        return next(a for a in self.zonas[zona][2] if a.id == ident)

    def objeto(self, zona: int, ident: str):
        return self.zonas[zona][1][ident]


def _decorado_franja(lz, indice, ancho_logico, ox):
    """Fondo sencillo de una franja: suelo de boceto de lado a lado, grava y estrellas."""
    import random

    from .decorado import SUELO, Estrella, decor
    from .variedad import actual

    rnd = random.Random(4000 + indice * 31 + actual().semilla)
    x0, x1 = -ox, ancho_logico - ox
    lz.boceto((x0 + 10, SUELO), (x1 - 10, SUELO), 2.6, decor(0.75), semilla=4100 + indice)
    for j in range(int((x1 - x0) / 60)):
        x = rnd.uniform(x0, x1)
        y = rnd.uniform(SUELO + 18, SUELO + 110)
        w = rnd.uniform(4, 11)
        lz.poligono([(x - w, y), (x - w * 0.3, y - w * 0.7), (x + w, y - w * 0.2), (x + w * 0.6, y + w * 0.4)],
                    borde=decor(0.4), ancho=1.4)
    parpadean = []
    for _ in range(int((x1 - x0) / 45 * actual().estrellas)):
        x, y = rnd.uniform(x0 + 20, x1 - 20), rnd.uniform(250, 640)
        r = rnd.choice((1.4, 1.8, 2.2, 2.8))
        brillo = rnd.uniform(0.45, 0.95)
        if rnd.random() < 0.35:
            parpadean.append(Estrella(indice, x, y, r, brillo, rnd.choice((1, 2, 3)), rnd.random()))
        else:
            lz.circulo((x, y), r, relleno=decor(brillo * 0.8))
    return parpadean
