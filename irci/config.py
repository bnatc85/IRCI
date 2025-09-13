from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass(frozen=True)
class Settings:
    fmp_api_key: str = os.getenv("FMP_API_KEY", "")
    data_dir: Path = Path(os.getenv("IRCI_DATA_DIR", "./data"))
    out_dir: Path = Path(os.getenv("IRCI_OUTPUT_DIR", "./outputs"))
    user_agent: str = os.getenv("SEC_USER_AGENT", "IRCI/0.1 (contact@example.com)")

    @staticmethod
    def load() -> "Settings":
        s = Settings()
        s.data_dir.mkdir(parents=True, exist_ok=True)
        s.out_dir.mkdir(parents=True, exist_ok=True)
        return s
