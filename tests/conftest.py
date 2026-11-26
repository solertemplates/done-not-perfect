import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
EP1 = RAIZ / "episodios" / "ep01_la_silla.json"


@pytest.fixture
def datos():
    return json.loads(EP1.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def escena():
    from dnp.config import cargar
    from dnp.ep01_silla import EpisodioSilla

    return EpisodioSilla(cargar(EP1))
