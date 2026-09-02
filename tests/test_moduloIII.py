import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from src.moduloII.app_config import AppPaths
from src.moduloIII.reassociacao import ResultadoReidentificacao, ReidentificacaoService, resultado_reidentificacao_payload


class FakeAnonimizador:
    def __init__(self, mapa):
        self.mapa = mapa

    def decrypt(self, valor):
        return self.mapa.get(valor, "[ERRO] valor invalido")


class ReidentificacaoServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = ReidentificacaoService(paths=None)

    def test_detecta_colunas_cpf_ignorando_colunas_de_validacao(self):
        df = pd.DataFrame(
            columns=[
                "cpfSaude",
                "cpf_valido",
                "cnpj",
                "nome",
                "documentoCpfImobiliario",
            ]
        )

        colunas = self.service._colunas_cpf(df)

        self.assertEqual(colunas, ["cpfSaude", "documentoCpfImobiliario"])

    def test_decriptografa_serie_preservando_vazios_e_erros(self):
        serie = pd.Series(["abc", "", "sem_mapa"])
        anonimizador = FakeAnonimizador({"abc": "12345678901"})

        resultado, total = self.service._decriptografar_serie(serie, anonimizador)

        self.assertEqual(total, 1)
        self.assertEqual(resultado.tolist(), ["12345678901", "", "sem_mapa"])

    def test_decriptografa_apenas_merge_key_com_prefixo_cpf(self):
        serie = pd.Series(["CPF_abc", "CNPJ_123", "CPF_sem_mapa", ""])
        anonimizador = FakeAnonimizador({"abc": "12345678901"})

        resultado, total = self.service._decriptografar_merge_key(serie, anonimizador)

        self.assertEqual(total, 1)
        self.assertEqual(resultado.tolist(), ["CPF_12345678901", "CNPJ_123", "CPF_sem_mapa", ""])

    def test_payload_json_da_reidentificacao_nao_inclui_lista_de_colunas(self):
        resultado = ResultadoReidentificacao(
            entrada="entrada.csv",
            saida="saida.csv",
            colunas_reidentificadas=[f"cpf_{indice}" for indice in range(1000)],
            valores_reidentificados=10,
            base_imobiliaria_saida="arquivos_gerados/base_imobiliario_reidentificada.csv",
            base_imobiliaria_valores_reidentificados=2,
        )

        payload = resultado_reidentificacao_payload(resultado)

        self.assertNotIn("colunas_reidentificadas", payload)
        self.assertEqual(payload["total_colunas_reidentificadas"], 1000)
        self.assertEqual(payload["valores_reidentificados"], 10)
        self.assertEqual(payload["base_imobiliaria_saida"], "arquivos_gerados/base_imobiliario_reidentificada.csv")
        self.assertEqual(payload["base_imobiliaria_valores_reidentificados"], 2)

    def test_reidentificacao_tambem_gera_copia_identificada_da_base_imobiliaria(self):
        with TemporaryDirectory() as pasta:
            paths = AppPaths()
            paths.definir_pasta_trabalho(pasta)
            paths.garantir_pasta(paths.pasta_gerados)
            pd.DataFrame(
                {
                    "merge_key": ["CPF_cpf_enc"],
                    "cpfSaude": ["cpf_enc"],
                    "cnpjFonte": ["04252011000110"],
                    "cpfValidoSaude": ["S"],
                }
            ).to_csv(
                paths.resolver(paths.arquivo_integracao_final),
                sep=";",
                encoding="utf-8-sig",
                index=False,
            )
            pd.DataFrame({"cpfImobiliario": ["\tcpf_enc"], "cnpjImobiliario": [""]}).to_csv(
                paths.resolver(paths.arquivo_base_imobiliario_modulo_iv),
                sep=";",
                encoding="utf-8-sig",
                index=False,
            )

            with patch("src.moduloIII.reassociacao.AnonimizadorReversivel", return_value=FakeAnonimizador({"cpf_enc": "00147611733"})):
                resultado = ReidentificacaoService(paths).reidentificar("12345678")

            base = pd.read_csv(
                paths.resolver(paths.arquivo_base_imobiliario_reidentificada),
                sep=";",
                encoding="utf-8-sig",
                dtype=str,
            ).fillna("")
            conteudo_integracao = paths.resolver(paths.arquivo_integracao_reidentificada).read_text(
                encoding="utf-8-sig"
            )
            conteudo_base = paths.resolver(paths.arquivo_base_imobiliario_reidentificada).read_text(
                encoding="utf-8-sig"
            )

        self.assertEqual(resultado.base_imobiliaria_saida, paths.arquivo_base_imobiliario_reidentificada)
        self.assertEqual(resultado.base_imobiliaria_valores_reidentificados, 1)
        self.assertEqual(base.at[0, "cpfImobiliario"], "\t00147611733")
        self.assertIn("\t00147611733", conteudo_integracao)
        self.assertIn("\t04252011000110", conteudo_integracao)
        self.assertIn("\t00147611733", conteudo_base)


if __name__ == "__main__":
    unittest.main()
