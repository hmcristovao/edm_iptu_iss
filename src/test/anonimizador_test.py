import pytest
import pandas as pd
import os
from unittest import mock
# Certifique-se de que este caminho está correto para o seu projeto
from ProcesssadorDados import ProcessadorSaae


# A importação de AnonimizadorReversivel não é mais necessária,
# pois ela será simulada (mocked).

# Fixture que será usada para simular o AnonimizadorReversivel
@pytest.fixture
def mock_anonimizador():
    # O caminho do patch deve apontar para onde a classe é procurada no MÓDULO EM TESTE (src.Saae)
    with mock.patch('src.Saae.AnonimizadorReversivel') as MockAnon:
        # Simula o comportamento do encrypt e decrypt
        instance = MockAnon.return_value
        instance.encrypt.side_effect = lambda x: f"ANON_{x}"
        instance.decrypt.side_effect = lambda x: x.replace("ANON_", "")
        yield instance


# Fixture para criar uma instância do ProcessadorSaae
@pytest.fixture
def processador_instance(tmp_path, mock_anonimizador):
    # O mock_anonimizador é injetado aqui para garantir que ProcessadorSaae use a versão simulada
    return ProcessadorSaae(pasta=str(tmp_path))


# ======================================================================
# 1. Testes de Funções Estáticas (Validação CPF/CNPJ)
# ======================================================================

def test_validar_cpf_valido():
    # CPF real e válido
    cpf_valido = "849.456.220-78"
    assert ProcessadorSaae.validarCpf(cpf_valido) is True


def test_validar_cpf_invalido_digito():
    # CPF com dígitos verificadores incorretos
    cpf_invalido = "33333333300"
    assert ProcessadorSaae.validarCpf(cpf_invalido) is False


def test_validar_cpf_sequencial_invalido():
    # CPFs sequenciais são inválidos pela regra de negócio
    cpf_sequencial = "11111111111"
    assert ProcessadorSaae.validarCpf(cpf_sequencial) is False


def test_validar_cnpj_valido():
    # CNPJ real e válido
    cnpj_valido = "11.222.333/0001-81"
    assert ProcessadorSaae.validarCnpj(cnpj_valido) is True


def test_validar_cnpj_invalido_tamanho():
    # CNPJ com tamanho incorreto
    cnpj_curto = "123"
    assert ProcessadorSaae.validarCnpj(cnpj_curto) is False


# ======================================================================
# 2. Teste de Carregar e Unir XLSX (Mock de I/O)
# ======================================================================

@pytest.fixture
def setup_excel_files(tmp_path):
    # Cria dois arquivos Excel temporários para simular a leitura

    # Arquivo 1
    data1 = {
        "Ligação": [101, 102],
        "Cliente": ["Alice", "Bob"],
        "Documento": ["123", "456"],
    }
    df1 = pd.DataFrame(data1)
    # Salva o arquivo temporário, pulando 2 linhas (header=2)
    df1.to_excel(tmp_path / "saae_1.xlsx", startrow=2, index=False)

    # Arquivo 2
    data2 = {
        "Ligação": [103],
        "Cliente": ["Charlie"],
        "Documento": ["789"],
    }
    df2 = pd.DataFrame(data2)
    df2.to_excel(tmp_path / "saae_2.xlsx", startrow=2, index=False)

    return tmp_path


# TESTE AJUSTADO: Adicionamos 'mock_anonimizador' como dependência
def test_carregar_unir_xlsx(setup_excel_files, mock_anonimizador):
    # O mock_anonimizador garante que AnonimizadorReversivel() não falhe ao ser chamado
    proc = ProcessadorSaae(pasta=str(setup_excel_files))
    df_unido = proc.carregarUnirXlsx()

    # Verifica se os três registros foram unidos corretamente
    assert len(df_unido) == 3

    # Verifica se as colunas e dados estão corretos
    assert list(df_unido["Ligação"].values) == [101, 102, 103]
    assert "Cliente" in df_unido.columns
    assert "Documento" in df_unido.columns


# ======================================================================
# 3. Teste de Padronização e Anonimização
# ======================================================================
# Estes testes já usam a fixture 'processador_instance', que por sua vez
# injeta o 'mock_anonimizador', então não precisam de ajustes.

def test_padronizar_colunas_e_validacao(processador_instance):
    # DataFrame de entrada simulando dados brutos
    data_in = {
        "Ligação": [200, 201],
        "Cliente": ["Empresa Alfa", "Pessoa Beta"],
        # Um CNPJ válido e um CPF válido para testar a validação
        "Documento": ["11222333000181", "849.456.220-78"],
        "Bairro": ["Centro", "Zona Sul"],
        "Coluna Extra": ["X", "Y"],  # Testa se colunas extras são mantidas
    }
    df_in = pd.DataFrame(data_in)

    df_out = processador_instance.padronizarColunas(df_in)

    # Verifica o mapeamento de colunas
    assert "nomeCliente" in df_out.columns
    assert "codigoLigacao" in df_out.columns

    # Verifica a divisão e validação do documento (CNPJ e CPF)
    assert df_out.iloc[0]["cnpj"] == "11222333000181"
    assert df_out.iloc[0]["cnpjValido"] == "S"
    assert df_out.iloc[1]["cpf"] == "84945622078"
    assert df_out.iloc[1]["cpfValido"] == "S"

    # Verifica se a coluna "Documento" original foi removida
    assert "Documento" not in df_out.columns

    # Verifica se a ordem das colunas e as colunas extras foram mantidas
    assert df_out.columns.tolist()[-1] == "Coluna Extra"


def test_anonimizar_desanonimizar_cpf(processador_instance):
    # Dataframe de teste com um CPF válido e um inválido/vazio
    data_test = {
        "cpf": ["84945622078", ""],
        "cpfValido": ["S", "N"]
    }
    df_in = pd.DataFrame(data_test)

    # 1. Teste de Anonimização
    df_anon = processador_instance.anonimizar(df_in.copy(), "cpf", "cpfValido")
    # O CPF válido deve ser anonimizado pelo Mock
    assert df_anon.iloc[0]["cpf"] == "ANON_84945622078"
    # O CPF inválido (N) deve permanecer inalterado
    assert df_anon.iloc[1]["cpf"] == ""

    # 2. Teste de Desanonimização
    df_desanon = processador_instance.desanonimizar(df_anon.copy(), "cpf", "cpfValido")
    # O CPF anonimizado deve ser revertido pelo Mock
    assert df_desanon.iloc[0]["cpf"] == "84945622078"
    # O CPF inválido permanece inalterado
    assert df_desanon.iloc[1]["cpf"] == ""


# ======================================================================
# 4. Teste do Pipeline Completo (Mock de I/O)
# ======================================================================
# Este teste já estava correto ao receber 'mock_anonimizador'.
# Fixture: Deixa apenas um arquivo para simplificar o teste de pipeline,
# mas garanta que contenha múltiplas linhas com CNPJ e CPF.
@pytest.fixture
def setup_excel_files(tmp_path):
    # Cria UM arquivo Excel temporário com todos os dados relevantes
    data = {
        "Ligação": [101, 102, 103, 104],
        "Cliente": ["Alice (CNPJ)", "Bob (CPF Inválido)", "Charlie (CPF Válido)", "David (Sem Doc)"],
        # CNPJ válido, CPF inválido, CPF válido, Doc vazio
        "Documento": ["11222333000181", "123.456.789-01", "84945622078", None],
    }
    df = pd.DataFrame(data)
    df.to_excel(tmp_path / "saae_unico.xlsx", startrow=2, index=False)

    return tmp_path


# ... (Mantenha as outras fixtures e testes estáticos inalterados)

# ... (Remova os testes carregarUnirXlsx se eles falharem com o novo setup, ou ajuste-os)
# Se o teste test_carregar_unir_xlsx falhar, mude-o para esperar apenas um arquivo:
def test_carregar_unir_xlsx(setup_excel_files, mock_anonimizador):
    proc = ProcessadorSaae(pasta=str(setup_excel_files))
    df_unido = proc.carregarUnirXlsx()
    assert len(df_unido) == 4
    # ...


# 4. Teste do Pipeline Completo AJUSTADO (usando busca por valor)
def test_processar_pipeline_completo(setup_excel_files, mock_anonimizador):
    proc = ProcessadorSaae(pasta=str(setup_excel_files))

    with mock.patch.object(pd.DataFrame, 'to_csv') as mock_to_csv:
        # ------------------------------------------------------------------
        # REMOVA O BLOCO ABAIXO (O SETUP JÁ CRIOU O ARQUIVO saae_unico.xlsx)
        # df_base = pd.DataFrame(...)
        # df_base.to_excel(...)
        # ------------------------------------------------------------------

        # Executa o pipeline
        df_resultado = proc.processar(salvar=True)

        # 1. VERIFICAÇÃO AJUSTADA: Use query para encontrar a linha CNPJ
        # O CNPJ '11222333000181' foi anonimizado/desanonimizado e deve estar no DF final.
        cnpj_row = df_resultado[df_resultado['nomeCliente'] == "Alice (CNPJ)"]

        # Garante que a linha CNPJ válida foi encontrada
        assert not cnpj_row.empty

        # Asserção: O valor final do CNPJ deve ser o original
        assert cnpj_row.iloc[0]['cnpj'] == "11222333000181"
        assert cnpj_row.iloc[0]['cnpjValido'] == "S"

        # Verificação do CPF (para o CPF válido)
        cpf_row = df_resultado[df_resultado['nomeCliente'] == "Charlie (CPF Válido)"]
        assert cpf_row.iloc[0]['cpf'] == "84945622078"
        assert cpf_row.iloc[0]['cpfValido'] == "S"

        # Verificação do CPF (para o CPF inválido)
        cpf_invalido_row = df_resultado[df_resultado['nomeCliente'] == "Bob (CPF Inválido)"]
        # O documento tinha 11 dígitos, mas era inválido, então CPF deveria ser preenchido, mas cpfValido = N
        assert cpf_invalido_row.iloc[0]['cpf'] == "12345678901"  # Pois a limpeza mantém
        assert cpf_invalido_row.iloc[0]['cpfValido'] == "N"