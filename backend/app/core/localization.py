"""Translate product copy only. User notes and medical values remain unchanged."""
import json
from pathlib import Path

_catalog = json.loads((Path(__file__).resolve().parents[3] / 'shared/i18n/en.json').read_text(encoding='utf-8'))


def translate(value: str, language: str = 'en') -> str:
    return _catalog.get(value, value) if language == 'en' else value
