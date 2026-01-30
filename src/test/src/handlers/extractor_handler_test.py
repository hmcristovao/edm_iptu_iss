import pytest

from src.Domain.Package import Package
from src.errors.extract_error import NotFoundExtensionError,NotFoundPathError,UnknownExtensioError
from src.handlers.extractor_handler import ExtractorHandler
from src.Domain.Parameters import Parameters


mockPackege = Package(
    Parameters(
        pasta='dados/Saae',
        footer=1,
        header=0,
        formato= None,
        saida='dados/processed',
        sufixo=['Saae'],
        variaveis=[{'Ligação': ['codigoLigacao']}, {'Cliente': ['nomeCliente']},
                   {'Documento': ['cpf', 'cpfValido', 'cnpj', 'cnpjValido']}, {'Contato': ['telefone']},
                   {'Tipo do logradouro': ['tipoLogradouro']}, {'Logradouro': ['logradouro']}, {'Número': ['numero']},
                   {'Bairro': ['bairro']}, {'Complemento': ['complemento']}, {'CEP': ['cep']}]
    ),
    data= None
)

@pytest.fixture
def instancia():
    instancia = ExtractorHandler()
    return instancia

def test_Extractor_Error_NOT_FOUND_EXTENSION(instancia):
    with pytest.raises(NotFoundExtensionError) as excinfo:
        instancia.handle(request=mockPackege)
    assert  isinstance(excinfo.value,NotFoundExtensionError)

def test_Extractor_Error_NOT_FOUND_PATH(instancia):
    mockPackege.parameters.formato = "xlsx"
    mockPackege.parameters.pasta = None
    with pytest.raises(NotFoundPathError) as excinfo:
        instancia.handle(request=mockPackege)
    assert isinstance(excinfo.value,NotFoundPathError)

def test_Extractor_Error_UNKNOWN_EXTENSION_(instancia):
    mockPackege.parameters.formato = "csx"
    with pytest.raises(UnknownExtensioError) as excinfo:
        instancia.handle(request=mockPackege)
    assert isinstance(excinfo.value,UnknownExtensioError)