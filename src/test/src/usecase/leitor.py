import pytest
from pathlib import Path
from src.usecase.leitor import ParameterReader
from src.Domain.Parameters import Parameters


@pytest.fixture
def instanciando_leitor():
    raiz_projeto = Path(__file__).resolve().parent.parent.parent.parent.parent

    caminho_txt = raiz_projeto / 'dados' / 'Saae' / 'parametros_Saae.txt'

    return ParameterReader(str(caminho_txt))


def test_serization_parameter(instanciando_leitor):
    resultado = instanciando_leitor.ler_arquivo()
    print(resultado.variaveis)
    assert isinstance(resultado, Parameters)