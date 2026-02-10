"""Configuration settings for the system."""

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

MODEL_NAME = "llama3.2"
TEMPERATURE = 0
MAX_ITERATIONS = 10

# Pipeline models
PARSER_MODEL = "mistral"
EXPLAINER_MODEL = "llama3.2"

# =============================================================================
# DATA PATHS
# =============================================================================

DATA_DIR = "data"
TRANSACTIONS_FILE = f"{DATA_DIR}/sample_transactions.csv"
LOG_DIR = "logs"

# =============================================================================
# SETTINGS
# =============================================================================

VERBOSE_MODE = True
STREAMING_ENABLED = True
USE_LLM_EXPLAINER = True
