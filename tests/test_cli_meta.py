"""Metadatos de la CLI: versión y ayuda."""

import pytest

from repo_agent import __version__
from repo_agent.cli import main


def test_version_expone_la_version_del_paquete(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])

    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_help_lista_subcomandos(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])

    salida = capsys.readouterr().out
    assert exc.value.code == 0
    assert "analyze" in salida
    assert "scan" in salida
