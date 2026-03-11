import os
from dotenv import load_dotenv

load_dotenv()

# ===== API KEY =====
S2_API_KEY = os.getenv("S2_API_KEY")

# ===== SEARCH SETTINGS =====
POOL_MULTIPLIER = 6
POOL_MIN = 20
POOL_MAX = 120

PDF_CHECK_TIMEOUT = 12

# ===== PAPER LIMITS =====
DEFAULT_LIMIT = 3
SAFE_MAX_LIMIT = 10
HARD_CAP_LIMIT = 25

# ===== PATHS =====
DATA_DIR = "data"
PDF_DIR = os.path.join(DATA_DIR, "raw_pdfs")
METADATA_DIR = os.path.join(DATA_DIR, "metadata")

# ===== FUTURE FLAGS =====
ALLOW_NO_PDF_PAPERS = True
SUMMARIZE_PER_PAPER_FIRST = True
EXTRACTED_DIR = os.path.join(DATA_DIR, "extracted")