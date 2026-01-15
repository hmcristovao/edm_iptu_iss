import os
import pandas as pd
from src.Domain.Package import Package
from src.handlers.Handler import AbstractHandler


class ExportHandler(AbstractHandler):
    def handle(self, request: Package):
        out_csv = os.path.join(request.parameters.saida, "Saae.csv")
        request.datas.to_csv(out_csv, index=False)
        print("Arquivos gerados:")
        print(out_csv)