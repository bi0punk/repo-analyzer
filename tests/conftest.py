import sys
from pathlib import Path

# repo_scanner_mvp vive bajo src/; lo añadimos al path para que los tests
# importen el paquete sin necesidad de instalar el proyecto.
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))