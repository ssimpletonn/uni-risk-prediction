from pathlib import Path

# ============================================================
# МОДЕЛЬ
# ============================================================

MODEL_NAME = "agro-risk-model"
MODEL_VERSION = "1.0"
MODEL_TYPE = "risk-scoring"

# Имитация состояния модели.
# Если False, endpoints инференса возвращают HTTP 503.
MODEL_READY = True


# ============================================================
# LLM / VIREONIX
# ============================================================

# Vireonix предоставляет OpenAI-совместимый endpoint
# без API-ключа и авторизации.
LLM_BASE_URL = "https://vireonix.ai/v1"
LLM_MODEL = "auto"

LLM_TIMEOUT_SECONDS = 60.0

LLM_DEFAULT_MAX_TOKENS = 300
LLM_DEFAULT_TEMPERATURE = 0.3


# ============================================================
# BATCHING / QUEUE
# ============================================================

# Максимальное число объектов в одном batch.
MAX_BATCH_SIZE = 8

# Максимальное время ожидания накопления dynamic batch.
MAX_BATCH_WAIT_MS = 50

# Максимальное количество запросов в очереди.
QUEUE_MAX_SIZE = 100

# Максимальное время ожидания результата инференса.
INFERENCE_TIMEOUT_SECONDS = 2.0


# ============================================================
# ИМИТАЦИЯ ВРЕМЕНИ РАБОТЫ МОДЕЛИ
# ============================================================

# 20 ms — фиксированный overhead одного вызова модели;
# 3 ms — вычисления на один объект.
#
# В реальном проекте asyncio.sleep() заменяется на
# model.predict(), model.predict_proba().

MODEL_FIXED_OVERHEAD_SECONDS = 0.020
MODEL_PER_ITEM_SECONDS = 0.003


# ============================================================
# SQLITE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "agro_scoring.db"

# Если SQLite временно занята другой транзакцией,
# соединение будет ожидать до 5 секунд.
DB_BUSY_TIMEOUT_MS = 5000


# ============================================================
# БИЗНЕС-СПРАВОЧНИКИ
# ============================================================

ALLOWED_REGIONS = {
    "Krasnodar",
    "Rostov",
    "Stavropol",
}

ALLOWED_RISK_LEVELS = {
    "low",
    "medium",
    "high",
}

# SQLite strftime('%w', ...) возвращает:
# 0 = Sunday, 1 = Monday, ..., 6 = Saturday.
WEEKDAY_MAP = {
    "sunday": "0",
    "monday": "1",
    "tuesday": "2",
    "wednesday": "3",
    "thursday": "4",
    "friday": "5",
    "saturday": "6",
}
