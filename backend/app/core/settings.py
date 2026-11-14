import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


@dataclass
class Settings:
    database_url: str = os.getenv('DATABASE_URL', f"sqlite:///{ROOT / 'data/private/aura.sqlite3'}")
    storage_dir: Path = Path(os.getenv('STORAGE_DIR', str(ROOT / 'data/private/captures')))
    frontend_dir: Path = ROOT / 'frontend/dist'
    secure_cookies: bool = os.getenv('SECURE_COOKIES', 'false').lower() == 'true'
    public_origin: str = os.getenv('PUBLIC_ORIGIN', '')
    session_hours: int = 8
    max_upload_bytes: int = 8 * 1024 * 1024

    def prepare(self):
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith('sqlite:///'):
            Path(self.database_url.removeprefix('sqlite:///')).parent.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif self.database_url.startswith('postgresql://'):
            self.database_url = self.database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
