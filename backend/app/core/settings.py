import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def public_origin():
    explicit = os.getenv('PUBLIC_ORIGIN', '').strip()
    domain = os.getenv('RAILWAY_PUBLIC_DOMAIN', '').strip()
    return explicit or (f'https://{domain}' if domain else '')


@dataclass
class Settings:
    database_url: str = os.getenv('DATABASE_URL', f"sqlite:///{ROOT / 'data/private/aura.sqlite3'}")
    storage_dir: Path = Path(os.getenv('STORAGE_DIR', str(ROOT / 'data/private/captures')))
    frontend_dir: Path = ROOT / 'frontend/dist'
    secure_cookies: bool = field(default_factory=lambda: os.getenv('SECURE_COOKIES', 'true' if os.getenv('RAILWAY_PUBLIC_DOMAIN') else 'false').lower() == 'true')
    public_origin: str = field(default_factory=public_origin)
    session_hours: int = field(default_factory=lambda: int(os.getenv('AURA_SESSION_HOURS', '720')))
    max_upload_bytes: int = 8 * 1024 * 1024

    def prepare(self):
        if not 1 <= self.session_hours <= 2160:
            raise ValueError('AURA_SESSION_HOURS debe estar entre 1 y 2160.')
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith('sqlite:///'):
            Path(self.database_url.removeprefix('sqlite:///')).parent.mkdir(parents=True, exist_ok=True)
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif self.database_url.startswith('postgresql://'):
            self.database_url = self.database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
