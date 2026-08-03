import unittest

import pandas as pd

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
        )

        payload = resultado_reidentificacao_payload(resultado)

        self.assertNotIn("colunas_reidentificadas", payload)
        self.assertEqual(payload["total_colunas_reidentificadas"], 1000)
        self.assertEqual(payload["valores_reidentificados"], 10)


if __name__ == "__main__":
    unittest.main()
