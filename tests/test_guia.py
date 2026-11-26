"""El ejemplo de GUIA_GUIONES.md es válido y es exactamente episodios/04_roca.json."""
import json
import re

from dnp.config import validar
from tests.conftest import EP4, RAIZ


def test_ejemplo_de_la_guia():
    guia = (RAIZ / "GUIA_GUIONES.md").read_text(encoding="utf-8")
    ejemplo = json.loads(re.search(r"```json\n(.*?)```", guia, re.S).group(1))
    validar(ejemplo)
    assert ejemplo == json.loads(EP4.read_text(encoding="utf-8"))


def test_la_guia_nombra_todas_las_piezas():
    from dnp import actores, escena, guion, piezas

    guia = (RAIZ / "GUIA_GUIONES.md").read_text(encoding="utf-8")
    nombres = (list(piezas.TIPOS) + list(actores.TIPOS) + list(guion.ACCIONES_MUNECO) + list(guion.ACCIONES_OBJETO)
               + escena.ESCENAS + escena.CARTELES + guion.FORMATOS)
    faltan = [n for n in nombres if f"`{n}`" not in guia and f'"{n}"' not in guia]
    assert not faltan, f"La guía no explica: {faltan}"
