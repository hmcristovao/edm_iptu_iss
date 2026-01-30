import pytest
from pathlib import Path
from src.usecase.leitor import ParameterReader
from src.Domain.Parameters import Parameters


mockParameters = Parameters(
    pasta='dados/Saae',
    footer= 1,
    header= 0,
    seq= ';',
    formato='xlsx',
    saida='dados/processed',
    sufixo=['Saae'],
    variaveis= [{'Ligação': ['codigoLigacao']}, {'Cliente': ['nomeCliente']}, {'Documento': ['cpf', 'cpfValido', 'cnpj', 'cnpjValido']}, {'Contato': ['telefone']}, {'Tipo do logradouro': ['tipoLogradouro']}, {'Logradouro': ['logradouro']}, {'Número': ['numero']}, {'Bairro': ['bairro']}, {'Complemento': ['complemento']}, {'CEP': ['cep']}]
)

@pytest.fixture
def instanciando_leitor():
    raiz_projeto = Path(__file__).resolve().parent.parent.parent.parent.parent

    caminho_txt = raiz_projeto / 'src'/'test'/ 'dados' / 'Saae' / 'parametros_Saae.txt'

    return ParameterReader(str(caminho_txt))


def test_serization_parameter(instanciando_leitor):
    resultado = instanciando_leitor.ler_arquivo()
    print(resultado.variaveis)
    assert isinstance(resultado, Parameters)

def test_extraindo_dados_do_txt_parametro(instanciando_leitor):
    resultado = instanciando_leitor.ler_arquivo()
    assert resultado.__eq__(mockParameters)