from pathlib import Path

from src.Domain.Package import Package
from src.handlers.Pseudonymization_handler import PseudonymizationHandler
from src.handlers.export_handler import ExportHandler
from src.handlers.extractor_handler import ExtractorHandler
from src.handlers.standardization_handler import StandardizationHandler
from src.usecase.leitor import ParameterReader
import logging

import sys
import os

# Adiciona o diretório atual ao path do sistema
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
        handlers=[
            logging.FileHandler("processamento_saae.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    raiz_projeto = Path(__file__).resolve().parent.parent.parent
    caminho_txt = raiz_projeto / 'dados' / 'Saae' / 'parametros_Saae.txt'

    parameter = ParameterReader(caminho_txt).ler_arquivo()
    package = Package(parameter)


    extractor = ExtractorHandler()
    standardizer = StandardizationHandler()
    pseudo = PseudonymizationHandler()
    exporthandler = ExportHandler()

    extractor.set_next(standardizer)
    standardizer.set_next(pseudo)
    pseudo.set_next(exporthandler)

    package = extractor.handle(request=package)

