import json
import os

TAXONOMY_PATH = os.path.join(os.path.dirname(__file__), '..', 'taxonomy', 'taxonomy.json')


def load_taxonomy() -> dict:
    with open(TAXONOMY_PATH, 'r') as f:
        return json.load(f)


def taxonomy_to_text(taxonomy: dict, indent: int = 0) -> str:
    """Convert taxonomy dict to readable text for the AI prompt."""
    lines = []
    for key, value in taxonomy.items():
        lines.append('  ' * indent + '- ' + key)
        if isinstance(value, dict):
            lines.append(taxonomy_to_text(value, indent + 1))
        elif isinstance(value, list):
            for item in value:
                lines.append('  ' * (indent + 1) + '• ' + item)
    return '\n'.join(lines)
