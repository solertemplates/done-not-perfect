"""videos/ERRORES.txt con un apartado para los Shorts y otro para los vídeos largos.

Cada parte del workflow solo toca su apartado, así los errores de un largo no
bloquean ni borran los de los Shorts (y al revés). Cuando no queda ningún
apartado, ERRORES.txt se borra.

Uso (lo lanza el workflow al guardar en main):
    python -m dnp.errores fusionar salida/videos videos
"""
from __future__ import annotations

import sys
from pathlib import Path

# apartado -> (archivo con errores, aviso de que todo fue bien), en la carpeta de salida
APARTADOS = {"SHORTS": ("ERRORES.txt", ".sin_errores"), "LARGOS": ("ERRORES_LARGOS.txt", ".sin_errores_largos")}
CABECERA = "########## {} ##########"


def leer(texto: str) -> dict[str, str]:
    """Apartados de un ERRORES.txt. Un archivo antiguo sin cabeceras cuenta como SHORTS."""
    partes: dict[str, list[str]] = {}
    actual = "SHORTS"
    for linea in texto.splitlines():
        s = linea.strip()
        nombre = next((a for a in APARTADOS if s == CABECERA.format(a)), None)
        if nombre:
            actual = nombre
            continue
        partes.setdefault(actual, []).append(linea)
    return {k: "\n".join(v).strip() + "\n" for k, v in partes.items() if "\n".join(v).strip()}


def escribir(partes: dict[str, str]) -> str:
    return "\n".join(f"{CABECERA.format(k)}\n{partes[k]}" for k in APARTADOS if k in partes)


def fusionar(salida: Path, videos: Path) -> None:
    """Actualiza videos/ERRORES.txt con lo que dejó cada parte en `salida`."""
    destino = videos / "ERRORES.txt"
    partes = leer(destino.read_text(encoding="utf-8")) if destino.exists() else {}
    for nombre, (archivo, ok) in APARTADOS.items():
        if (salida / archivo).exists():
            partes[nombre] = (salida / archivo).read_text(encoding="utf-8").strip() + "\n"
        elif (salida / ok).exists():
            partes.pop(nombre, None)
    if partes:
        videos.mkdir(parents=True, exist_ok=True)
        destino.write_text(escribir(partes), encoding="utf-8")
    elif destino.exists():
        destino.unlink()


if __name__ == "__main__":
    if len(sys.argv) != 4 or sys.argv[1] != "fusionar":
        sys.exit("Uso: python -m dnp.errores fusionar <carpeta_salida> <carpeta_videos>")
    fusionar(Path(sys.argv[2]), Path(sys.argv[3]))
