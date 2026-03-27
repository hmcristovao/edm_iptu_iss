from pathlib import Path
from dotenv import load_dotenv

from src.Domain.Package import Package
from src.handlers.Pseudonymization_handler import PseudonymizationHandler
from src.handlers.adapters.anomizador.anonimizador_reversivel_adaptado import AnonimizadorReversivel
from src.handlers.export_handler import ExportHandler
from src.handlers.extractor_handler import ExtractorHandler
from src.handlers.standardization_handler import StandardizationHandler
from src.usecase.leitor import ParameterReader

import logging

import sys
import os
import colorlog
import colorama
# Adiciona o diretório atual ao path do sistema
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
if __name__ == "__main__":
    logger = logging.getLogger()
    current_dir = Path(__file__).resolve().parent

    # Sobe dois níveis e entra na pasta 'dados' para achar o .env
    dotenv_path = current_dir.parent.parent / 'dados' / '.env'

    load_dotenv(dotenv_path=dotenv_path)
    colorama.init()

    # 1. Configuração de Cores (Dicionário padrão)
    log_colors_config = {
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }

    # 2. Formatador - A sacada é colocar o asctime ANTES da cor
    # e usar o secondary_log_colors para "limpar" o resto.
    console_formatter = colorlog.ColoredFormatter(
        fmt="%(asctime)s - %(log_color)s%(levelname)-8s%(reset)s - [%(name)s] %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors=log_colors_config,
        secondary_log_colors={},  # Força o reset nos campos secundários
        style='%'
    )
    # Formato simples para o Arquivo (TXT)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] %(message)s')

    # 3. Handlers
    # Handler para o Console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)

    # Handler para o Arquivo
    file_handler = logging.FileHandler("processamento_saae.log", encoding='utf-8')
    file_handler.setFormatter(file_formatter)

    # 4. Configuração Geral do Logger Raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [console_handler, file_handler]

    raiz_projeto = Path(__file__).resolve().parent.parent.parent
    caminho_txt = raiz_projeto / 'dados' #/ 'Saae2' / 'parametros_Saae.txt'

    for arquivo in caminho_txt.rglob("*.txt"):
        logger.info(f"######################################################################")
        parameter = ParameterReader(arquivo).ler_arquivo()
        package = Package(parameter)


        extractor = ExtractorHandler()
        standardizer = StandardizationHandler()
        anon = AnonimizadorReversivel()
        pseudo = PseudonymizationHandler(anon)
        exporthandler = ExportHandler()

        extractor.set_next(standardizer)
        standardizer.set_next(pseudo)
        pseudo.set_next(exporthandler)

        package = extractor.handle(request=package)
        logger.info(f"######################################################################")


