"""Carga y validación estricta del JSON de un episodio.

Todos los errores se explican en español y se acumulan, para que se puedan
corregir de una vez (útil cuando se edita el JSON desde el móvil).
"""
from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ErrorConfig(Exception):
    """El JSON del episodio no es válido. `errores` contiene cada problema."""

    def __init__(self, errores: list[str], archivo: str | None = None):
        self.errores = errores
        cabecera = f"El archivo '{archivo}' no es válido" if archivo else "La configuración no es válida"
        lineas = "\n".join(f"  - {e}" for e in errores)
        super().__init__(f"{cabecera} ({len(errores)} error(es)):\n{lineas}")


# --- Esquema -----------------------------------------------------------------
# Cada campo: tipo, y opcionalmente min/max, valores permitidos ("opciones"),
# valor exacto ("igual") o longitud máxima de texto ("max_len").

_NUM = (int, float)

ESQUEMA: dict[str, Any] = {
    "serie": {"tipo": str, "igual": "Done, not perfect"},
    "episodio": {"tipo": int, "min": 1, "max": 999},
    "id": {"tipo": str, "patron_id": True, "max_len": 60},
    "titulo": {"tipo": str, "max_len": 60},
    "video": {
        "tipo": dict,
        "campos": {
            "ancho": {"tipo": int, "igual": 1080},
            "alto": {"tipo": int, "igual": 1920},
            "fps": {"tipo": int, "igual": 30},
            "duracion_s": {"tipo": _NUM, "min": 15, "max": 20},
        },
    },
    "tiempos": {
        "tipo": dict,
        "campos": {
            "gancho_fin_s": {"tipo": _NUM, "min": 0.5, "max": 3},
            "rebobinado_fin_s": {"tipo": _NUM, "min": 1, "max": 6},
            "accion_fin_s": {"tipo": _NUM, "min": 8, "max": 18},
        },
    },
    "textos": {
        "tipo": dict,
        "campos": {
            "gancho": {"tipo": str, "max_len": 40},
            "cierre": {"tipo": str, "max_len": 24},
            "marca": {"tipo": str, "max_len": 30},
        },
    },
    "perfeccionista": {
        "tipo": dict,
        "campos": {"intentos": {"tipo": int, "min": 1, "max": 4}},
    },
    "hacedor": {
        "tipo": dict,
        "campos": {
            "inclinacion_inicial_grados": {"tipo": _NUM, "min": 2, "max": 15},
            "inclinacion_final_grados": {"tipo": _NUM, "min": 0, "max": 10},
        },
    },
    "audio": {
        "tipo": dict,
        "campos": {
            "musica": {"tipo": str, "max_len": 200},
            "volumen_musica": {"tipo": _NUM, "min": 0, "max": 1},
            "volumen_efectos": {"tipo": _NUM, "min": 0, "max": 1},
            "bpm_aproximado": {"tipo": _NUM, "min": 50, "max": 160},
        },
    },
}

_NOMBRE_TIPO = {
    str: "texto",
    int: "número entero",
    float: "número",
    bool: "verdadero/falso",
    dict: "objeto { }",
    list: "lista [ ]",
    type(None): "null (vacío)",
}


def _tipo_de(valor: Any) -> str:
    return _NOMBRE_TIPO.get(type(valor), type(valor).__name__)


def _tipo_esperado(tipo: Any) -> str:
    if tipo == _NUM:
        return "número"
    return _NOMBRE_TIPO.get(tipo, str(tipo))


def _cumple_tipo(valor: Any, tipo: Any) -> bool:
    if isinstance(valor, bool):  # en Python bool es int: lo rechazamos aparte
        return tipo is bool
    if tipo == _NUM:
        return isinstance(valor, (int, float))
    return isinstance(valor, tipo)


def _validar_objeto(datos: dict, esquema: dict, ruta: str, errores: list[str]) -> None:
    for clave in datos:
        if clave not in esquema:
            sugerencia = difflib.get_close_matches(clave, list(esquema), n=1, cutoff=0.6)
            extra = f" ¿Querías decir '{sugerencia[0]}'?" if sugerencia else ""
            permitidos = ", ".join(sorted(esquema))
            errores.append(
                f"Campo desconocido '{ruta}{clave}'.{extra} Campos permitidos aquí: {permitidos}."
            )
    for clave, regla in esquema.items():
        nombre = f"{ruta}{clave}"
        if clave not in datos:
            errores.append(f"Falta el campo obligatorio '{nombre}'.")
            continue
        _validar_valor(datos[clave], regla, nombre, errores)


def _validar_valor(valor: Any, regla: dict, nombre: str, errores: list[str]) -> None:
    tipo = regla["tipo"]
    if not _cumple_tipo(valor, tipo):
        errores.append(
            f"'{nombre}' debe ser {_tipo_esperado(tipo)}, pero es {_tipo_de(valor)} ({json.dumps(valor, ensure_ascii=False)})."
        )
        return
    if tipo is dict:
        _validar_objeto(valor, regla["campos"], f"{nombre}.", errores)
        return
    if "igual" in regla and valor != regla["igual"]:
        errores.append(
            f"'{nombre}' debe valer exactamente {json.dumps(regla['igual'], ensure_ascii=False)} "
            f"(es fijo en la serie), pero vale {json.dumps(valor, ensure_ascii=False)}."
        )
    if "min" in regla and valor < regla["min"]:
        errores.append(f"'{nombre}' vale {valor}, pero el mínimo es {regla['min']}.")
    if "max" in regla and valor > regla["max"]:
        errores.append(f"'{nombre}' vale {valor}, pero el máximo es {regla['max']}.")
    if isinstance(valor, str):
        if not valor.strip():
            errores.append(f"'{nombre}' no puede estar vacío.")
        if "max_len" in regla and len(valor) > regla["max_len"]:
            errores.append(
                f"'{nombre}' es demasiado largo ({len(valor)} caracteres, máximo {regla['max_len']})."
            )
        if regla.get("patron_id") and not all(c.islower() or c.isdigit() or c == "_" for c in valor):
            errores.append(
                f"'{nombre}' solo puede tener minúsculas sin tildes, números y guiones bajos (por ejemplo 'ep01_la_silla')."
            )


def _validar_coherencia(d: dict, errores: list[str]) -> None:
    """Reglas entre campos, solo si los campos individuales ya son válidos."""
    t, v = d["tiempos"], d["video"]
    g, r, a, dur = t["gancho_fin_s"], t["rebobinado_fin_s"], t["accion_fin_s"], v["duracion_s"]
    if not g < r:
        errores.append(f"'tiempos.rebobinado_fin_s' ({r}) debe ser mayor que 'tiempos.gancho_fin_s' ({g}).")
    if not r < a:
        errores.append(f"'tiempos.accion_fin_s' ({a}) debe ser mayor que 'tiempos.rebobinado_fin_s' ({r}).")
    if a - r < 8:
        errores.append(f"La acción en paralelo dura {a - r:g} s; necesita al menos 8 s para que se entienda.")
    if dur - a < 3:
        errores.append(
            f"El final (desde 'tiempos.accion_fin_s' = {a} hasta 'video.duracion_s' = {dur}) dura {dur - a:g} s; "
            "necesita al menos 3 s para mostrar el cierre y volver a la imagen del gancho."
        )
    if abs(dur * v["fps"] - round(dur * v["fps"])) > 1e-6:
        errores.append(
            f"'video.duracion_s' ({dur}) por 'video.fps' ({v['fps']}) debe dar un número entero de fotogramas."
        )
    h = d["hacedor"]
    if h["inclinacion_final_grados"] >= h["inclinacion_inicial_grados"]:
        errores.append(
            "'hacedor.inclinacion_final_grados' debe ser menor que 'hacedor.inclinacion_inicial_grados': "
            "al arreglarla, la silla tiene que quedar mejor."
        )
    musica = d["audio"]["musica"]
    if musica not in ("auto", "generada") and not musica.startswith("audio/"):
        errores.append(
            "'audio.musica' debe ser \"auto\" (usa tu archivo de la carpeta audio/ si existe), "
            "\"generada\" (música creada por código) o una ruta dentro de la carpeta audio/, "
            f"por ejemplo \"audio/musica.mp3\". Ahora vale \"{musica}\"."
        )


@dataclass(frozen=True)
class Episodio:
    datos: dict
    archivo: Path | None = None

    def __getitem__(self, clave: str) -> Any:
        return self.datos[clave]

    @property
    def fps(self) -> int:
        return self.datos["video"]["fps"]

    @property
    def duracion(self) -> float:
        return float(self.datos["video"]["duracion_s"])

    @property
    def num_fotogramas(self) -> int:
        return int(round(self.duracion * self.fps))

    @property
    def tamano(self) -> tuple[int, int]:
        return self.datos["video"]["ancho"], self.datos["video"]["alto"]


def validar(datos: Any, archivo: str | None = None) -> Episodio:
    errores: list[str] = []
    if not isinstance(datos, dict):
        raise ErrorConfig([f"El contenido principal debe ser un objeto {{ }}, pero es {_tipo_de(datos)}."], archivo)
    _validar_objeto(datos, ESQUEMA, "", errores)
    if not errores:
        _validar_coherencia(datos, errores)
    if errores:
        raise ErrorConfig(errores, archivo)
    return Episodio(datos=datos, archivo=Path(archivo) if archivo else None)


def cargar(ruta: str | Path) -> Episodio:
    ruta = Path(ruta)
    if not ruta.exists():
        raise ErrorConfig([f"No existe el archivo '{ruta}'. Revisa el nombre y la carpeta."], str(ruta))
    texto = ruta.read_text(encoding="utf-8")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as e:
        pista = ""
        for curva in ("“", "”"):
            if curva in texto:
                linea = texto[: texto.index(curva)].count("\n") + 1
                raise ErrorConfig(
                    [
                        f"La línea {linea} tiene comillas tipográficas ({curva}). El teclado del iPhone las pone solas: "
                        "usa comillas rectas (\") o desactiva 'Puntuación inteligente' en Ajustes > General > Teclado."
                    ],
                    str(ruta),
                ) from None
        if "trailing comma" in e.msg:
            pista = " Sobra una coma de más antes de '}' o ']'."
        elif "Expecting property name" in e.msg:
            pista = " Suele ser una coma de más antes de '}' o comillas que faltan en un nombre."
        elif "Expecting ',' delimiter" in e.msg:
            pista = " Suele faltar una coma entre dos campos."
        elif "Expecting value" in e.msg:
            pista = " Falta un valor, o hay una coma de más antes de ']' o '}'."
        elif "Invalid control character" in e.msg or "Unterminated string" in e.msg:
            pista = " Hay un texto sin cerrar comillas."
        raise ErrorConfig(
            [f"El JSON está mal escrito en la línea {e.lineno}, columna {e.colno}.{pista} (detalle técnico: {e.msg})"],
            str(ruta),
        ) from None
    return validar(datos, str(ruta))
