"""
Утилиты для определения типа устройства по User-Agent.
"""
from starlette.requests import Request

# Ключевые слова для определения мобильных устройств
_MOBILE_KEYWORDS = (
    "mobile", "android", "iphone", "ipad", "ipod",
    "blackberry", "windows phone", "webos", "opera mini",
    "silk", "kindle", "playbook", "tablet",
)

# Исключения — устройства, которые НЕ считаем мобильными
# (например, iPad с desktop mode, некоторые планшеты)
_DESKTOP_KEYWORDS = ("ipados",)


def is_mobile(request: Request) -> bool:
    """
    Определяет, зашёл ли пользователь с мобильного устройства.
    
    Анализирует User-Agent header на наличие мобильных ключевых слов.
    Также учитывает заголовок X-Mobile-Detect для случаев когда
    клиент сам сообщает о мобильности (например, через meta viewport).
    
    Returns:
        True если запрос с мобильного устройства, False иначе.
    """
    # Проверяем явный заголовок (может устанавливаться JS на клиенте)
    if request.headers.get("x-mobile-detect", "").lower() == "true":
        return True

    ua = request.headers.get("user-agent", "").lower()

    # Сначала проверяем исключения
    if any(kw in ua for kw in _DESKTOP_KEYWORDS):
        # iPad на iPadOS может запрашивать десктопную версию
        # Но если в UA есть "mobile" — всё равно считаем мобильным
        if "mobile" not in ua:
            return False

    return any(kw in ua for kw in _MOBILE_KEYWORDS)
