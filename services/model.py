from schemas import PredictionRequest

def get_recommendation(level: str) -> str:
    """
    Возвращает рекомендацию в зависимости от категории риска.
    """

    if level == "low":
        return "Стандартное рассмотрение"

    if level == "medium":
        return "Требуется дополнительная проверка"

    return "Высокий риск. Требуется ручное рассмотрение"

def calculate_risk(data: PredictionRequest) -> float:
    """
    Реализует простую логику оценки риска по финансовым показателям
    и отраслевым факторам.
    """

    score = 0.1

    # Длительная просрочка увеличивает риск
    if data.payment_delay_days > 30:
        score += 0.3

    # Наличие предыдущих дефолтов увеличивает риск
    if data.previous_defaults > 0:
        score += 0.3

    # Большая задолженность увеличивает риск
    if data.debt > 5_000_000:
        score += 0.2

    # Малое количество осадков условно увеличивает
    # аграрный риск
    if data.precipitation_mm < 100:
        score += 0.1

    # Ограничиваем значение диапазоном от 0 до 1
    score = min(score, 1.0)

    return round(score, 2)

def get_risk_level(score: float) -> str:
    """
    Преобразует score в категорию риска.
    """

    if score < 0.3:
        return "low"

    if score < 0.7:
        return "medium"

    return "high"