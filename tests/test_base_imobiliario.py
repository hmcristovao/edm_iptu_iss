import unittest

import pandas as pd

from src.moduloIV.base_imobiliario import (
    COLUNA_CNPJ_VALIDO,
    COLUNA_CPF_VALIDO,
    COLUNA_CELULAR,
    COLUNA_DOCUMENTO,
    COLUNA_ENDERECO,
    COLUNA_EMAIL,
    COLUNA_INSCRICAO,
    PREFIXO_EMAIL_ENRIQUECIDO,
    PREFIXO_TELEFONE_ENRIQUECIDO,
    BaseImobiliarioModuloIVService,
)


class FakeAnonimizador:
    def __init__(self, mapa):
        self.mapa = mapa

    def decrypt(self, valor):
        return self.mapa.get(valor, "[ERRO] valor invalido")


class BaseImobiliarioModuloIVServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = BaseImobiliarioModuloIVService(paths=None)

    def test_remove_duplicados_agregando_inscricoes_de_documentos_validos(self):
        df = pd.DataFrame(
            {
                COLUNA_DOCUMENTO: ["cpf_enc", "cpf_enc", "04252011000110", "04252011000110"],
                COLUNA_CPF_VALIDO: ["S", "S", "N", "N"],
                COLUNA_CNPJ_VALIDO: ["N", "N", "S", "S"],
                COLUNA_INSCRICAO: ["100", "200", "300", "400"],
                "nome": ["Ana", "Ana repetida", "Empresa", "Empresa repetida"],
            }
        )

        resultado, removidas = self.service._remover_duplicados_agregando_inscricoes(df)

        self.assertEqual(removidas, 2)
        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado.iloc[0][COLUNA_INSCRICAO], "100 | 200")
        self.assertEqual(resultado.iloc[1][COLUNA_INSCRICAO], "300 | 400")
        self.assertEqual(resultado.iloc[0]["nome"], "Ana")
        self.assertEqual(resultado.iloc[1]["nome"], "Empresa")

    def test_ignora_linhas_com_cpf_e_cnpj_invalidos_na_deduplicacao(self):
        df = pd.DataFrame(
            {
                COLUNA_DOCUMENTO: ["mesmo", "mesmo"],
                COLUNA_CPF_VALIDO: ["N", "N"],
                COLUNA_CNPJ_VALIDO: ["N", "N"],
                COLUNA_INSCRICAO: ["100", "200"],
            }
        )

        resultado, removidas = self.service._remover_duplicados_agregando_inscricoes(df)

        self.assertEqual(removidas, 0)
        self.assertEqual(resultado[COLUNA_INSCRICAO].tolist(), ["100", "200"])

    def test_reidentifica_apenas_cpfs_validos(self):
        df = pd.DataFrame(
            {
                COLUNA_DOCUMENTO: ["cpf_enc", "04252011000110", "erro"],
                COLUNA_CPF_VALIDO: ["S", "N", "S"],
                COLUNA_CNPJ_VALIDO: ["N", "S", "N"],
                COLUNA_INSCRICAO: ["100", "200", "300"],
            }
        )
        anonimizador = FakeAnonimizador({"cpf_enc": "529.982.247-25"})

        total = self.service._reidentificar_cpfs(df, anonimizador)

        self.assertEqual(total, 1)
        self.assertEqual(df[COLUNA_DOCUMENTO].tolist(), ["52998224725", "04252011000110", "erro"])

    def test_remove_endereco_imobiliario_da_saida(self):
        df = pd.DataFrame(
            {
                COLUNA_DOCUMENTO: ["04252011000110"],
                COLUNA_ENDERECO: ["Rua A"],
                COLUNA_INSCRICAO: ["100"],
            }
        )

        self.service._remover_colunas_saida(df)

        self.assertNotIn(COLUNA_ENDERECO, df.columns)
        self.assertIn(COLUNA_DOCUMENTO, df.columns)
        self.assertIn(COLUNA_INSCRICAO, df.columns)

    def test_conta_celular_e_email_preenchidos(self):
        df = pd.DataFrame(
            {
                COLUNA_CELULAR: ["81999990000", "", "  ", "8177778888", "-"],
                COLUNA_EMAIL: ["a@exemplo.com", "", "nan", "b@exemplo.com", " - "],
            }
        )

        self.assertEqual(self.service._contar_preenchidos(df, COLUNA_CELULAR), 2)
        self.assertEqual(self.service._contar_preenchidos(df, COLUNA_EMAIL), 2)

    def test_calcula_percentual_de_enriquecimento(self):
        self.assertEqual(self.service._calcular_percentual_enriquecimento(2123, 517), 410.64)
        self.assertEqual(self.service._calcular_percentual_enriquecimento(144, 221), 65.16)
        self.assertEqual(self.service._calcular_percentual_enriquecimento(1, 0), 0.0)

    def test_protege_cpfcnpj_como_texto_na_saida(self):
        df = pd.DataFrame({COLUNA_DOCUMENTO: ["00147611733", "04252011000110", ""]})

        self.service._proteger_documento_saida(df)

        self.assertEqual(df[COLUNA_DOCUMENTO].tolist(), ["\t00147611733", "\t04252011000110", ""])

    def test_ordena_registros_validos_antes_dos_invalidos(self):
        df = pd.DataFrame(
            {
                COLUNA_DOCUMENTO: ["invalido1", "cpf", "invalido2", "cnpj"],
                COLUNA_CPF_VALIDO: ["N", "S", "N", "N"],
                COLUNA_CNPJ_VALIDO: ["N", "N", "N", "S"],
                COLUNA_INSCRICAO: ["1", "2", "3", "4"],
            }
        )

        resultado = self.service._ordenar_validos_primeiro(df)

        self.assertEqual(resultado[COLUNA_DOCUMENTO].tolist(), ["cpf", "cnpj", "invalido1", "invalido2"])
        self.assertEqual(resultado[COLUNA_INSCRICAO].tolist(), ["2", "4", "1", "3"])

    def test_enriquece_telefones_e_emails_por_cpf_e_cnpj(self):
        imobiliario = pd.DataFrame(
            {
                COLUNA_DOCUMENTO: ["52998224725", "04252011000110"],
                COLUNA_CPF_VALIDO: ["S", "N"],
                COLUNA_CNPJ_VALIDO: ["N", "S"],
                COLUNA_INSCRICAO: ["100", "200"],
                COLUNA_CELULAR: ["81999990000", ""],
                COLUNA_EMAIL: ["", "contato@empresa.com"],
            }
        )
        integracao = pd.DataFrame(
            {
                "merge_key": ["CPF_52998224725", "CNPJ_04252011000110"],
                "telefoneSaude": ["81999990000 | 8133334444", "8132221111"],
                "celularEducacao": ["8177778888", ""],
                "emailSaude": ["ana@exemplo.com", "contato@empresa.com | novo@empresa.com"],
                "id_revisao": ["REV000001", ""],
                "usuario_revisao": ["maria", ""],
                "data_revisao": ["2026-07-23 10:00:00", ""],
                "nome": ["Ana", "Empresa"],
            }
        )

        telefones, emails = self.service._enriquecer_contatos(imobiliario, integracao)

        self.assertEqual(telefones, 2)
        self.assertEqual(emails, 2)
        self.assertEqual(imobiliario[f"{PREFIXO_TELEFONE_ENRIQUECIDO}1"].tolist(), ["8133334444", "8132221111"])
        self.assertEqual(imobiliario[f"{PREFIXO_TELEFONE_ENRIQUECIDO}2"].tolist(), ["8177778888", ""])
        self.assertEqual(imobiliario[f"{PREFIXO_EMAIL_ENRIQUECIDO}1"].tolist(), ["ana@exemplo.com", "novo@empresa.com"])
        self.assertEqual(imobiliario[f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_origem"].tolist(), ["telefoneSaude", "telefoneSaude"])
        self.assertEqual(imobiliario[f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_id_revisao"].tolist(), ["REV000001", ""])
        self.assertEqual(imobiliario[f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_usuario_revisao"].tolist(), ["maria", ""])
        self.assertEqual(
            imobiliario[f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_data_revisao"].tolist(),
            ["2026-07-23 10:00:00", ""],
        )
        self.assertEqual(imobiliario[f"{PREFIXO_EMAIL_ENRIQUECIDO}1_origem"].tolist(), ["emailSaude", "emailSaude"])
        self.assertEqual(imobiliario[f"{PREFIXO_EMAIL_ENRIQUECIDO}1_id_revisao"].tolist(), ["REV000001", ""])

    def test_nao_adiciona_telefone_repetido_com_formatacao_diferente(self):
        imobiliario = pd.DataFrame(
            {
                COLUNA_DOCUMENTO: ["52998224725"],
                COLUNA_CPF_VALIDO: ["S"],
                COLUNA_CNPJ_VALIDO: ["N"],
                COLUNA_INSCRICAO: ["100"],
                COLUNA_CELULAR: ["(81) 99999-0000"],
                COLUNA_EMAIL: ["ANA@EXEMPLO.COM"],
            }
        )
        integracao = pd.DataFrame(
            {
                "merge_key": ["CPF_52998224725"],
                "telefoneSaude": ["81999990000 | +55 81 99999-0000 | 8177778888"],
                "emailSaude": ["ana@exemplo.com | novo@exemplo.com"],
            }
        )

        telefones, emails = self.service._enriquecer_contatos(imobiliario, integracao)

        self.assertEqual(telefones, 1)
        self.assertEqual(emails, 1)
        self.assertEqual(imobiliario[f"{PREFIXO_TELEFONE_ENRIQUECIDO}1"].tolist(), ["8177778888"])
        self.assertEqual(imobiliario[f"{PREFIXO_EMAIL_ENRIQUECIDO}1"].tolist(), ["novo@exemplo.com"])

    def test_nao_enriquece_contato_de_linha_pendente_de_revisao_humana(self):
        imobiliario = pd.DataFrame(
            {
                COLUNA_DOCUMENTO: ["52998224725"],
                COLUNA_CPF_VALIDO: ["S"],
                COLUNA_CNPJ_VALIDO: ["N"],
                COLUNA_INSCRICAO: ["100"],
                COLUNA_CELULAR: [""],
                COLUNA_EMAIL: [""],
            }
        )
        integracao = pd.DataFrame(
            {
                "merge_key": ["CPF_52998224725"],
                "telefoneSaude": ["81999990000"],
                "emailSaude": ["ana@exemplo.com"],
                "id_revisao": ["REV000001"],
                "usuario_revisao": [""],
                "data_revisao": [""],
            }
        )

        telefones, emails = self.service._enriquecer_contatos(imobiliario, integracao)

        self.assertEqual(telefones, 0)
        self.assertEqual(emails, 0)
        self.assertNotIn(f"{PREFIXO_TELEFONE_ENRIQUECIDO}1", imobiliario.columns)
        self.assertNotIn(f"{PREFIXO_EMAIL_ENRIQUECIDO}1", imobiliario.columns)

    def test_move_colunas_de_rastreio_para_o_final_da_tabela(self):
        df = pd.DataFrame(
            columns=[
                COLUNA_DOCUMENTO,
                f"{PREFIXO_TELEFONE_ENRIQUECIDO}1",
                f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_origem",
                f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_id_revisao",
                f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_usuario_revisao",
                f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_data_revisao",
                f"{PREFIXO_EMAIL_ENRIQUECIDO}1",
                f"{PREFIXO_EMAIL_ENRIQUECIDO}1_origem",
                f"{PREFIXO_EMAIL_ENRIQUECIDO}1_id_revisao",
                f"{PREFIXO_EMAIL_ENRIQUECIDO}1_usuario_revisao",
                f"{PREFIXO_EMAIL_ENRIQUECIDO}1_data_revisao",
                COLUNA_INSCRICAO,
            ]
        )

        resultado = self.service._mover_colunas_rastreio_para_final(df)

        self.assertEqual(
            resultado.columns[-8:].tolist(),
            [
                f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_origem",
                f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_id_revisao",
                f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_usuario_revisao",
                f"{PREFIXO_TELEFONE_ENRIQUECIDO}1_data_revisao",
                f"{PREFIXO_EMAIL_ENRIQUECIDO}1_origem",
                f"{PREFIXO_EMAIL_ENRIQUECIDO}1_id_revisao",
                f"{PREFIXO_EMAIL_ENRIQUECIDO}1_usuario_revisao",
                f"{PREFIXO_EMAIL_ENRIQUECIDO}1_data_revisao",
            ],
        )


if __name__ == "__main__":
    unittest.main()
