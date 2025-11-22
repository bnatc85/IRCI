# irci/config.py
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict
import os, json
from dotenv import load_dotenv
load_dotenv(override=True)

@dataclass
class Settings:
    fmp_api_key: str = os.getenv("FMP_API_KEY", "")
    worldnews_api_key: str = os.getenv("WORLDNEWS_API_KEY", "")
    alpha_vantage_api_key: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    data_dir: Path = Path(os.getenv("IRCI_DATA_DIR", "./data"))
    out_dir: Path = Path(os.getenv("IRCI_OUTPUT_DIR", "./outputs"))
    # SEC user-agent used by coverage.py for SEC requests
    user_agent: str = os.getenv("SEC_USER_AGENT", "IRCI/0.1 (contact@example.com)")
    # For media fetchers that read from the repo (e.g., data/news/*.csv)
    data_root: Path = Path(os.getenv("IRCI_DATA_ROOT", "."))
    # Credibility/reach weights for media domains
    domain_weights: Optional[Dict[str, float]] = None

    @staticmethod
    def load() -> "Settings":
        s = Settings()
        s.data_dir.mkdir(parents=True, exist_ok=True)
        s.out_dir.mkdir(parents=True, exist_ok=True)

        # --- YAML config (optional) ---
        cfg_path = os.environ.get("IRCI_SETTINGS_FILE", "config/settings.yaml")
        if Path(cfg_path).exists():
            try:
                import yaml  # pip install pyyaml
                with open(cfg_path, "r") as f:
                    y = yaml.safe_load(f) or {}
                ua = y.get("user_agent")
                if isinstance(ua, str) and ua.strip():
                    s.user_agent = ua.strip()
                dw = y.get("domain_weights")
                if isinstance(dw, dict):
                    s.domain_weights = {str(k).lower(): float(v) for k, v in dw.items()}
                dr = y.get("data_root")
                if isinstance(dr, str) and dr.strip():
                    s.data_root = Path(dr.strip())
            except Exception as e:
                import warnings
                warnings.warn(f"Could not parse {cfg_path}: {e}")

        # --- ENV overrides (take precedence) ---
        ua_env = os.getenv("IRCI_USER_AGENT")
        if ua_env:
            s.user_agent = ua_env

        dw_env = os.getenv("IRCI_DOMAIN_WEIGHTS")
        if dw_env:
            try:
                dwj = json.loads(dw_env)
                if isinstance(dwj, dict):
                    s.domain_weights = {str(k).lower(): float(v) for k, v in dwj.items()}
            except Exception as e:
                import warnings
                warnings.warn(f"IRCI_DOMAIN_WEIGHTS not valid JSON: {e}")

        # --- Sensible defaults if unset ---
        if not s.domain_weights:
            s.domain_weights = {
                "wsj.com": 1.0,
                "bloomberg.com": 1.0,
                "reuters.com": 0.9,
                "seekingalpha.com": 0.6,
                "prnewswire.com": 0.4,
            }
        return s