import unittest

import pandas as pd

from src.moduloII.app_config import (
    COLUNA_DATA_REVISAO,
    COLUNA_DECISAO_REVISAO,
    COLUNA_MERGE_KEY,
    COLUNA_OBSERVACAO_REVISAO,
    COLUNA_REVISAO,
    COLUNA_SCORE_REVISAO,
    COLUNA_USUARIO_REVISAO,
)
from src.moduloII.services import RevisaoService, extrair_porcentagem, texto_valor, valor_vazio


class ServicesModuloIITest(unittest.TestCase):
    def test_utilitarios_tratam_valores_vazios_e_porcentagem(self):
        self.assertTrue(valor_vazio(""))
        self.assertTrue(valor_vazio(" null "))
        self.assertFalse(valor_vazio("texto"))
        self.assertEqual(texto_valor(None), "")
        self.assertEqual(texto_valor(" abc "), " abc ")
        self.assertEqual(extrair_porcentagem("Inicio 12% fim 140%"), 100)
        self.assertIsNone(extrair_porcentagem("sem percentual"))

    def test_cria_pares_candidatos_com_valido_e_invalidos_do_mesmo_grupo(self):
        df = pd.DataFrame(
            {
                COLUNA_REVISAO: ["G1", "G1", "G1", "G2"],
                COLUNA_MERGE_KEY: ["CPF_1", "", "", ""],
                COLUNA_SCORE_REVISAO: ["", "91.5", "82", "99"],
            }
        )
        service = RevisaoService(paths=None)

        pares = service.criar_pares_candidatos(df)

        self.assertEqual([par["par_id"] for par in pares], ["G1:0:1", "G1:0:2"])
        self.assertEqual(pares[0]["idx_valido"], 0)
        self.assertEqual(pares[0]["idx_invalido"], 1)
        self.assertEqual(pares[0]["score_revisao"], "91.5")

    def test_aplicar_decisao_aprovada_preenche_vazios_remove_invalido_e_registra_metadados(self):
        df = pd.DataFrame(
            {
                COLUNA_MERGE_KEY: ["CPF_1", ""],
                "nome": ["Ana", "Ana Silva"],
                "telefone": ["", "81999990000"],
            }
        )
        decisoes = {
            "G1:0:1": {
                "par_id": "G1:0:1",
                "id_revisao": "G1",
                "idx_valido": 0,
                "idx_invalido": 1,
                "score_revisao": "90",
                "decisao": "aprovar",
                "usuario_revisor": "usuario",
                "observacao": "ok",
                "data_decisao": "2026-07-13 10:00:00",
            }
        }
        service = RevisaoService(paths=None)

        resultado = service.aplicar_decisoes(df, decisoes)

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado.at[0, "nome"], "Ana")
        self.assertEqual(resultado.at[0, "telefone"], "81999990000")
        self.assertEqual(resultado.at[0, COLUNA_USUARIO_REVISAO], "usuario")
        self.assertEqual(resultado.at[0, COLUNA_DECISAO_REVISAO], "aprovar")
        self.assertEqual(resultado.at[0, COLUNA_OBSERVACAO_REVISAO], "ok")
        self.assertEqual(resultado.at[0, COLUNA_DATA_REVISAO], "2026-07-13 10:00:00")


if __name__ == "__main__":
    unittest.main()
