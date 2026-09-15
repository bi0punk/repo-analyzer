import sys
from pathlib import Path

# repo_scanner_mvp vive bajo src/ y repo_agent en la raíz del proyecto.
# Se añaden ambos al path para que los tests importen los paquetes sin
# necesidad de instalar el proyecto.
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
for directory in (ROOT_DIR, SRC_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))