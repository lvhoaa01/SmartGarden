import os
from pathlib import Path
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).parent.parent.parent


@dataclass
class DatabaseConfig:
    server: str = r"DAIKAHOAAAA\MSSQLSERVER01"
    database: str = "SmartGarden"

    @property
    def connection_string(self) -> str:
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server};DATABASE={self.database};"
            f"Trusted_Connection=yes"
        )


@dataclass
class ModelPaths:
    vlm_model: str = "AI_Models/qwen_vlm.gguf"
    clip_model: str = "AI_Models/mmproj.gguf"

    def get_vlm_path(self) -> str:
        return str(PROJECT_ROOT / self.vlm_model)

    def get_clip_path(self) -> str:
        return str(PROJECT_ROOT / self.clip_model)


@dataclass
class Config:
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    models: ModelPaths = field(default_factory=ModelPaths)
    host: str = "0.0.0.0"
    port: int = 8000
    api_key: str = field(
        default_factory=lambda: os.environ.get(
            "SMARTGARDEN_API_KEY", "smartgarden-secret-key-2026"
        )
    )
    uploads_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "uploads")
    dataset_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "dataset")


config = Config()