import logging
import pathlib

from src.moduloI.Domain.Package import Package
from src.moduloI.handlers.Handler import AbstractHandler


class ExportHandler(AbstractHandler):
    def __init__(self):
        super().__init__()
        self.iteracao = 0
        self.logger = logging.getLogger(self.__class__.__name__)

    def handle(self, request: Package):
        sufixo = request.parameters.sufixo[0]

        # O caminho de saída já vem definido em request.parameters.saida.
        # Aqui apenas garantimos que a pasta exista antes de exportar o CSV.
        pasta_saida = pathlib.Path(request.parameters.saida)

        self.logger.info(f'Exportando dados para: {pasta_saida}')

        try:
            pasta_saida.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Erro ao criar diretório de saída {pasta_saida}: {e}")
            raise

        out_csv = pasta_saida / f"{sufixo}.csv"

        try:
            if request.datas is not None and not request.datas.empty:
                dados_exportacao = self._preparar_documentos_como_texto(request.datas)
                dados_exportacao.to_csv(out_csv, index=False, sep=';', encoding='utf-8-sig')
                request.exported = True
                self.iteracao += 1
                self.logger.info(f"Arquivo gerado com sucesso: {out_csv}")
            else:
                request.exported = False
                self.logger.warning(f"O DataFrame '{sufixo}' está vazio. Nada foi exportado.")
        except Exception as e:
            request.exported = False
            self.logger.error(f"Falha ao gravar o arquivo {out_csv}: {e}")
            raise

        return super().handle(request)

    def _preparar_documentos_como_texto(self, df):
        resultado = df.copy()

        for coluna in resultado.columns:
            nome = str(coluna).lower()
            if ("cpf" not in nome and "cnpj" not in nome) or "valid" in nome:
                continue

            resultado[coluna] = resultado[coluna].apply(self._formatar_como_texto)

        return resultado

    def _formatar_como_texto(self, valor):
        texto = "" if valor is None else str(valor).strip()
        if not texto or texto.lower() in {"nan", "none", "null"}:
            return ""
        if texto.startswith("\t"):
            return texto
        return f"\t{texto}"
