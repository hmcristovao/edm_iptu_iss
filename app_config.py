import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppPaths:
    code_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    work_dir: Path = field(default_factory=lambda: Path(os.environ.get("AVALIADOR_WORKDIR", Path.cwd())).resolve())
    pasta_gerados: str = "arquivos_gerados"
    pasta_logs: str = "logs"
    arquivo_config_etapa2: str = "etapa2_config.json"

    @property
    def arquivo_etapa1(self) -> str:
        return os.path.join(self.pasta_gerados, "etapa1_final.csv")

    @property
    def arquivo_etapa2(self) -> str:
        return os.path.join(self.pasta_gerados, "etapa2_final.csv")

    @property
    def arquivo_log_merges(self) -> str:
        return os.path.join(self.pasta_gerados, "etapa2_log_merges.csv")

    @property
    def arquivo_decisoes(self) -> str:
        return os.path.join(self.pasta_gerados, "revisao_merges_decisoes.csv")

    @property
    def arquivo_etapa3_final(self) -> str:
        return os.path.join(self.pasta_gerados, "etapa3_final.csv")

    @property
    def arquivo_etapa3_parcial(self) -> str:
        return os.path.join(self.pasta_gerados, "etapa3_parcial.csv")

    def resolver(self, caminho: str | os.PathLike) -> Path:
        caminho_path = Path(caminho)
        if caminho_path.is_absolute():
            return caminho_path
        return self.work_dir / caminho_path

    def resolver_codigo(self, caminho: str | os.PathLike) -> Path:
        caminho_path = Path(caminho)
        if caminho_path.is_absolute():
            return caminho_path
        return self.code_dir / caminho_path

    def definir_pasta_trabalho(self, caminho: str | os.PathLike):
        self.work_dir = Path(caminho).expanduser().resolve()

    def garantir_pasta(self, caminho: str | os.PathLike):
        self.resolver(caminho).mkdir(parents=True, exist_ok=True)

    def garantir_pasta_arquivo(self, caminho: str | os.PathLike):
        pasta = Path(caminho).parent
        if str(pasta) != ".":
            self.garantir_pasta(pasta)

    def existe(self, caminho: str | os.PathLike) -> bool:
        return self.resolver(caminho).exists()


@dataclass(frozen=True)
class AppSettings:
    senha_padrao: str = field(default_factory=lambda: os.environ.get("APP_SENHA_PADRAO", "1234"))
    etapa2_config_padrao: dict = field(
        default_factory=lambda: {
            "threshold_similaridade": 85,
            "threshold_revisar": 80,
            "threshold_apoio_nome": 96,
            "threshold_apoio_telefone": 98,
            "threshold_apoio_email": 100,
            "threshold_apoio_nascimento": 100,
            "threshold_apoio_endereco": 98,
            "threshold_apoio_numero": 100,
            "threshold_apoio_identificador_documento": 98,
            "max_pares_por_valor_bloco": 1500000,
        }
    )


COLUNA_REVISAO = "id_revisao"
COLUNA_SCORE_REVISAO = "score_revisao"
COLUNA_MERGE_KEY = "merge_key"
COLUNA_USUARIO_REVISAO = "usuario_revisao"
COLUNA_DECISAO_REVISAO = "decisao_revisao"
COLUNA_OBSERVACAO_REVISAO = "observacao_revisao"
COLUNA_DATA_REVISAO = "data_revisao"
