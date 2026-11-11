import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SPTRANS_BASE_URL = os.getenv(
    "SPTRANS_BASE_URL",
    "https://api.olhovivo.sptrans.com.br/v2.1",
).rstrip("/")
SPTRANS_TOKEN = os.getenv("SPTRANS_TOKEN", "").strip()
