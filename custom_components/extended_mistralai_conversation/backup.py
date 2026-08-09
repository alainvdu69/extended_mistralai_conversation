"""Lecture/écriture du fichier de sauvegarde des options (partagé entre __init__.py et config_flow.py)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: str, data: dict[str, Any]) -> None:
    """Écrit le JSON sur disque (fonction synchrone, à exécuter via l'executor)."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: str) -> dict[str, Any]:
    """Lit le JSON depuis le disque (fonction synchrone, à exécuter via l'executor)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
