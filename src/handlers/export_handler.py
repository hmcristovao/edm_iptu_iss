import logging
import pathlib  # Melhor prática para manipulação de caminhos
import pandas as pd
from src.Domain.Package import Package
from src.handlers.Handler import AbstractHandler


class ExportHandler(AbstractHandler):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def handle(self, request: Package):
        self.logger.info(f'Salvando - {request.parameters.sufixo}')

        pasta_saida = pathlib.Path(request.parameters.saida)

        try:
            pasta_saida.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Erro ao criar diretório {pasta_saida}: {e}")
            raise


        out_csv = pasta_saida / "Saae.csv"
        print(f"Salvando - {out_csv}")

        request.datas.to_csv(out_csv, index=False)

        self.logger.info(f"Arquivo gerado com sucesso em: {out_csv}")

        return super().handle(request)