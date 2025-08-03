
import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')

def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"Plik konfiguracyjny nie zostal znaleziony: {CONFIG_PATH}")
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

config = load_config()
