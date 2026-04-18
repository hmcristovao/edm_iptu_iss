import logging
import pathlib
from src.Domain.Package import Package
from src.handlers.Handler import AbstractHandler


class ExportHandler(AbstractHandler):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def handle(self, request: Package):
        sufixo = request.parameters.sufixo[0]

        # O caminho vindo do parâmetro já deve apontar para onde queres salvar.
        # Garantimos que o objeto Path aponte para a pasta 'dados_processados'
        # conforme a tua instrução de que este é o destino final.
        pasta_saida = pathlib.Path(request.parameters.saida)

        self.logger.info(f'Exportando dados para: {pasta_saida}')

        try:
            # Cria a pasta de saída (definida no parâmetro) se ela não existir
            pasta_saida.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Erro ao criar diretório de saída {pasta_saida}: {e}")
            raise

        # Define o nome do arquivo final dentro dessa pasta
        out_csv = pasta_saida / f"{sufixo}.csv"

        try:
            if request.datas is not None and not request.datas.empty:
                # Gravação do CSV
                # Nota: Usei encoding utf-8-sig para evitar problemas com acentos em sistemas Windows/Excel
                request.datas.to_csv(out_csv, index=False, sep=';', encoding='utf-8-sig')
                self.logger.info(f"Arquivo gerado com sucesso: {out_csv}")
            else:
                self.logger.warning(f"O DataFrame '{sufixo}' está vazio. Nada foi exportado.")
        except Exception as e:
            self.logger.error(f"Falha ao gravar o arquivo {out_csv}: {e}")
            raise

        return super().handle(request)