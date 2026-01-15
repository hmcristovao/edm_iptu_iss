import logging
import os
import pandas as pd
from src.Domain.Package import Package
from src.handlers.Handler import AbstractHandler


class ExportHandler(AbstractHandler):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
    def handle(self, request: Package):
        self.logger.info(f'Salvando - {request.parameters.sufixo}')
        out_csv = os.path.join(request.parameters.saida, "Saae.csv")
        request.datas.to_csv(out_csv, index=False)
        self.logger.info("Arquivos gerados:")
        self.logger.info(out_csv)