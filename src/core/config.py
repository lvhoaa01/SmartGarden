import os
from pathlib import Path
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).parent.parent.parent

@dataclass
class DatabaseConfig:
    server: str = r"DAIKAHOAAAA\MSSQLSERVER01"
    database: str = "SmartGarden_Core"
    
    @property
    def connection_string(self) -> str:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.server};DATABASE={self.database};Trusted_Connection=yes"

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

config = Config()