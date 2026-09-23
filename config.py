MODEL_NAME = "agro-risk-model"
MODEL_VERSION = "1.0"
MODEL_TYPE = "risk-scoring"

# Имитируем состояние модели.
# Если установить False, /predict будет возвращать HTTP 503.
MODEL_READY = True

ALLOWED_REGIONS = {
    "Krasnodar",
    "Rostov",
    "Stavropol"
}