import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppPaths:
    code_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    work_dir: Path = field(default_factory=lambda: Path(os.environ.get("AVALIADOR_WORKDIR", Path.cwd())).resolve())
    pasta_gerados: str = "arquivos_gerados"
    pasta_logs: str = "logs"
    arquivo_config_integracao: str = os.path.join("arquivos_gerados", "integracao_config.json")

    @property
    def arquivo_preparacao(self) -> str:
        return os.path.join(self.pasta_gerados, "integracao_base.csv")

    @property
    def arquivo_enriquecimento(self) -> str:
        return os.path.join(self.pasta_gerados, "integracao_enriquecida.csv")

    @property
    def arquivo_log_merges(self) -> str:
        return os.path.join(self.pasta_gerados, "integracao_log_merges.csv")

    @property
    def arquivo_decisoes(self) -> str:
        return os.path.join(self.pasta_gerados, "revisao_merges_decisoes.csv")

    @property
    def arquivo_integracao_final(self) -> str:
        return os.path.join(self.pasta_gerados, "integracao_final.csv")

    @property
    def arquivo_integracao_parcial(self) -> str:
        return os.path.join(self.pasta_gerados, "integracao_parcial.csv")

    @property
    def arquivo_integracao_reidentificada(self) -> str:
        return os.path.join(self.pasta_gerados, "integracao_reidentificada.csv")

    @property
    def arquivo_base_imobiliario_modulo_iv(self) -> str:
        return os.path.join(self.pasta_gerados, "base_imobiliario_modulo_iv.csv")

    @property
    def pasta_dados_processados(self) -> str:
        return "dados_processados"

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
    integracao_config_padrao: dict = field(
        default_factory=lambda: {
            "threshold_similaridade": 85,
            "threshold_revisar": 80,
            "threshold_apoio_nome": 100,
            "threshold_apoio_telefone": 95,
            "threshold_apoio_email": 99,
            "threshold_apoio_nascimento": 99,
            "threshold_apoio_endereco": 100,
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
