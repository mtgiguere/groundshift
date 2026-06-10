from pathlib import Path

import yaml


def load_profile_from_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)
