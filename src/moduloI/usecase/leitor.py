from pathlib import Path
import os
from dotenv import load_dotenv
from src.moduloI.Domain.Parameters import Parameters

load_dotenv()


class ParameterReader:
    def __init__(self, caminho_arquivo):
        self.caminho = Path(caminho_arquivo).resolve()
        self.base_path = Path(os.getenv('DATA_PATH', os.getcwd())).resolve()

    def ler_arquivo(self) -> Parameters:
        config = {
            'CSV separator': None,
            'Format': '',
            'Header#': 0,
            'Footer#': 0,
            'Sufix': [],
            'Variables': []
        }

        with open(self.caminho, 'r', encoding='utf-8') as f:
            linhas = f.readlines()

        lendo_variaveis = False

        for linha in linhas:
            linha_limpa = linha.strip()
            if not linha_limpa:
                continue

            linha_lower = linha_limpa.lower()

            if linha_lower.startswith('footer#:'):
                config['Footer#'] = int(linha_limpa.split(':', 1)[1].strip())

            elif linha_lower.startswith('header#:'):
                config['Header#'] = int(linha_limpa.split(':', 1)[1].strip())

            elif linha_lower.startswith('csv separator:'):
                sep = linha_limpa.split(':', 1)[1].strip()
                config['CSV separator'] = None if sep.lower() == 'none' or not sep else sep

            elif linha_lower.startswith('format:'):
                config['Format'] = linha_limpa.split(':', 1)[1].strip()

            elif linha_lower.startswith('sufix:'):
                config['Sufix'] = [linha_limpa.split(':', 1)[1].strip()]

            elif linha_lower.startswith('variables:'):
                lendo_variaveis = True
                continue

            elif lendo_variaveis and ':' in linha_limpa:
                partes = linha_limpa.split(':', 1)
                chave = partes[0].strip()
                campos = [c.strip() for c in partes[1].split(',')]
                config['Variables'].append({chave: campos})

        # A pasta de entrada passa a ser a pasta onde o TXT está
        caminho_entrada = self.caminho.parent

        # Saída continua centralizada na raiz informada na interface
        caminho_saida = self.base_path.parent / 'dados_processados'

        return Parameters(
            pasta=str(caminho_entrada),
            saida=str(caminho_saida),
            footer=config['Footer#'],
            header=config['Header#'],
            sep=config['CSV separator'],
            sufixo=config['Sufix'],
            formato=config['Format'],
            variaveis=config['Variables']
        )
