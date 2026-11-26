import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
EP1 = RAIZ / "episodios" / "ep01_la_silla.json"
EP2 = RAIZ / "episodios" / "ep02_la_escalera.json"
EP3 = RAIZ / "episodios" / "ep03_los_dos_martillos.json"
EP4 = RAIZ / "episodios" / "04_roca.json"
EPISODIOS = [EP1, EP2, EP3, EP4]


@pytest.fixture
def datos():
    return json.loads(EP1.read_text(encoding="utf-8"))


def _crear(ruta):
    from dnp.config import cargar
    from dnp.render import crear_escena

    return crear_escena(cargar(ruta))


@pytest.fixture(scope="session")
def escena():
    """Episodio 1 (se mantiene por compatibilidad con los tests de audio)."""
    return _crear(EP1)


@pytest.fixture(scope="session", params=EPISODIOS, ids=lambda p: p.stem)
def cada_escena(request):
    return _crear(request.param)


@pytest.fixture(scope="session")
def martillos():
    return _crear(EP3)


@pytest.fixture(scope="session")
def roca():
    return _crear(EP4)


@pytest.fixture
def datos_roca():
    return json.loads(EP4.read_text(encoding="utf-8"))
