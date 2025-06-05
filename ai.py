import re
import google.generativeai as genai
from typing import List, Tuple, Dict, Optional

API_KEY = "YOUR_API_KEY"


# --- Моковые ответы для тестирования ---
MOCK_RESPONSES = {
    "НАЧАЛО_ИСТОРИИ": {
        "story": "Вы стоите на распутье древней дороги. Северная тропа ведет в темный, шепчущий лес, южная - к мерцающим вдали горным пикам. У ваших ног лежит старый, ржавый меч, покрытый странными рунами.",
        "choices": ["Идти на север, в лес", "Идти на юг, к горам", "Подобрать меч и осмотреть руны"]
    },
    "Идти на север, в лес": {
        "story": "Лес становится все гуще и темнее с каждым шагом. Ветки цепляются за одежду, а тишину нарушает лишь треск сучьев под ногами и далекий, тоскливый вой.",
        "choices": ["Продолжать углубляться в лес", "Попытаться найти источник воя", "Вернуться на распутье"]
    },
    "Идти на юг, к горам": {
        "story": "Подъем к горам крут, но воздух становится свежее. Вдалеке, среди скал, вы замечаете слабый дымок, поднимающийся к небу.",
        "choices": ["Идти к источнику дыма", "Поискать безопасное место для лагеря", "Вернуться на распутье"]
    },
    "Подобрать меч и осмотреть руны": {
        "story": "Меч неожиданно легок для своего вида. Руны на нем слабо светятся голубоватым светом, когда вы берете его в руки. Кажется, они складываются в какое-то предостережение о тенях.",
        "choices": ["Идти на север, взяв меч", "Идти на юг, взяв меч", "Попытаться прочесть руны вслух"]
    },
    "Продолжать углубляться в лес": {
        "story": "Вы идете все дальше в лес. Становится холодно, и вы слышите хруст веток позади себя.",
        "choices": ["Обернуться", "Ускорить шаг", "Затаиться и ждать"]
    }
}
MOCK_REQUEST_COUNT = 0
MOCK_KEYS = list(MOCK_RESPONSES.keys())


def parse_ai_text_response(text_response: str) -> tuple[str, list[str]]:
    """
    Парсит структурированный текстовый ответ от ИИ.
    Ожидаемый формат:
    STORY: [Текст истории]
    CHOICES:
    1. [Вариант 1]
    2. [Вариант 2]
    ...
    """
    story_part = "Ошибка: Не удалось разобрать ответ ИИ."
    choices_part = ["Продолжить..."]

    try:
        # Ищем STORY: часть, которая может быть многострочной, до CHOICES:
        story_match = re.search(r"STORY:(.*?)CHOICES:", text_response, re.DOTALL | re.IGNORECASE)
        # Ищем CHOICES: часть, которая идет до конца текста
        choices_match = re.search(r"CHOICES:(.*)", text_response, re.DOTALL | re.IGNORECASE)

        if story_match and choices_match:
            story_part = story_match.group(1).strip()
            raw_choices = choices_match.group(1).strip()

            choices_part = []
            for line in raw_choices.split('\n'):
                line = line.strip()
                if not line:
                    continue
                cleaned_choice = re.sub(r"^\s*\d+[\.\)]\s*|^-\s*|^\*\s*", "", line).strip()  # Удаляем нумерацию/маркеры
                if cleaned_choice:
                    choices_part.append(cleaned_choice)

            if not choices_part:
                choices_part = ["Двигаться дальше"]
        elif "STORY:" in text_response.upper():
            story_part = re.sub(r"STORY:", "", text_response, flags=re.IGNORECASE).strip()
            choices_part = ["Что делать?"]
        elif "CHOICES:" in text_response.upper():
            raw_choices = re.sub(r"CHOICES:", "", text_response, flags=re.IGNORECASE).strip()
            choices_part = [line.strip() for line in raw_choices.split('\n') if line.strip()]
            story_part = "История не была предоставлена."
        else:
            story_part = text_response.strip()
            choices_part = ["Продолжить наугад"]
            print(f"Предупреждение: Ответ ИИ не соответствует ожидаемой структуре. Ответ: {text_response[:200]}...")

        if not story_part: story_part = "Повествование прервалось..."
        if not choices_part: choices_part = ["Попытаться еще раз"]

        return story_part, choices_part
    except Exception as e:
        print(f"Ошибка при парсинге ответа ИИ: {e}")
        return "Произошла ошибка в разборе ответа от ИИ.", ["Попробовать снова"]


def get_ai_response(player_action_prompt: str, game_history: Optional[List[Dict[str, str]]] = None) -> Tuple[
    str, List[str]]:
    global MOCK_REQUEST_COUNT

    if not API_KEY:
        print("ПРЕДУПРЕЖДЕНИЕ: API_KEY не установлен или используется ключ-заглушка. Используется моковый ответ.")

        mock_key_to_use = ""
        if player_action_prompt == "Начало истории...":
            mock_key_to_use = "НАЧАЛО_ИСТОРИИ"
        else:
            for key_mock in MOCK_RESPONSES.keys():
                if player_action_prompt.lower() in key_mock.lower() or key_mock.lower() in player_action_prompt.lower():
                    mock_key_to_use = key_mock
                    break
            if not mock_key_to_use:
                mock_key_to_use = MOCK_KEYS[MOCK_REQUEST_COUNT % len(MOCK_KEYS)]
                MOCK_REQUEST_COUNT += 1

        if mock_key_to_use in MOCK_RESPONSES:
            response_data = MOCK_RESPONSES[mock_key_to_use]
            ai_text_response = f"STORY: {response_data['story']}\nCHOICES:\n" + "\n".join(
                [f"{i + 1}. {c}" for i, c in enumerate(response_data['choices'])])
            print(f"MOCK AI: Действие: '{player_action_prompt}'. Ответ по ключу '{mock_key_to_use}'.")
            return parse_ai_text_response(ai_text_response)
        else:
            return "Ошибка в моковых данных.", ["Перезапустить игру"]

    # --- Реальный запрос к Gemini API ---
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')  # или 'gemini-pro'
    except Exception as e:
        print(f"Ошибка конфигурации Gemini: {e}")
        return f"Ошибка конфигурации AI: {e}", ["Проверить API ключ", "Выйти"]

    history_context_for_prompt = ""
    if game_history:
        for turn in game_history:
            history_context_for_prompt += f"Рассказчик: {turn.get('story', 'N/A')}\nИгрок: {turn.get('player_action', 'N/A')}\n\n"

    prompt_structure = """Твой ответ ДОЛЖЕН БЫТЬ СТРОГО СТРУКТУРИРОВАН следующим образом, И НИКАК ИНАЧЕ, без каких-либо дополнительных комментариев до или после этой структуры:
STORY: [здесь яркое и подробное описание текущей ситуации]
CHOICES:
1. [здесь первый вариант действия]
2. [здесь второй вариант действия]
(Если вариантов больше или меньше, продолжай/сокращай нумерацию.)

Пример желаемого ответа:
STORY: Вы стоите на распутье древней дороги. Северная тропа ведет в темный, шепчущий лес, южная - к мерцающим вдали горным пикам. У ваших ног лежит старый, ржавый меч, покрытый странными рунами.
CHOICES:
1. Идти на север, в лес
2. Подобрать меч и осмотреть руны
"""

    if player_action_prompt == "Начало истории...":
        full_prompt = f"""Ты — рассказчик в текстовой игре в жанре интерактивного фэнтези.
Твоя задача — создать увлекательную историю.
Начни новое приключение. Опиши начальную сцену и предложи игроку 3-4 четких варианта действий.
{prompt_structure}"""
    else:
        full_prompt = f"""Ты — рассказчик в текстовой игре в жанре интерактивного фэнтези.
Контекст предыдущих событий:
{history_context_for_prompt}
Игрок только что выбрал следующее действие: "{player_action_prompt}"

Продолжи историю, основываясь на выборе игрока. 
Опиши, что произошло дальше в результате этого действия, и предложи игроку 3-4 НОВЫХ, логичных и интересных варианта действий.
Не повторяй только что предложенные варианты, если это не обусловлено сюжетом (например, возвращение).
{prompt_structure}"""

    print(f"Отправка запроса к Gemini. Промт (начало): {full_prompt[:300]}...")

    try:
        # Настройки генерации и безопасности
        generation_config = genai.types.GenerationConfig(
            # temperature=0.8, # Экспериментируйте со значениями
            max_output_tokens=2048
        )
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]

        response = model.generate_content(
            full_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        ai_text_response = ""
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            ai_text_response = "".join(part.text for part in response.candidates[0].content.parts)

        if not ai_text_response:
            block_reason_info = "неизвестна"
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                block_reason_info = str(response.prompt_feedback.block_reason)
            elif response.candidates and response.candidates[0].finish_reason:
                block_reason_info = str(response.candidates[0].finish_reason)

            print(f"Ответ ИИ был заблокирован или пуст. Причина: {block_reason_info}")
            if hasattr(response, 'prompt_feedback'): print(f"Prompt Feedback: {response.prompt_feedback}")

            return f"Ответ ИИ был заблокирован или пуст (причина: {block_reason_info}).", ["Попробовать другой ход",
                                                                                           "Вернуться в меню"]

        print(f"Gemini ответил (начало): {ai_text_response[:200]}...")
        return parse_ai_text_response(ai_text_response)

    except Exception as e:  # Ловим более общие ошибки от genai, включая ошибки API
        error_message = f"Ошибка при взаимодействии с Gemini API: {e}"
        # Попытка извлечь детали, если это ошибка Google API
        if hasattr(e, 'message'):  # google.api_core.exceptions.GoogleAPIError
            error_message += f" Детали: {e.message}"  # type: ignore
        print(error_message)
        # Возвращаем более общее сообщение пользователю
        user_error_msg = "Произошла ошибка при обращении к AI. Проверьте API ключ и соединение."
        if "API key not valid" in str(e) or "PERMISSION_DENIED" in str(e):
            user_error_msg = "Ошибка API ключа. Пожалуйста, проверьте ваш ключ Gemini."

        return user_error_msg, ["Повторить запрос", "Вернуться в меню (проверить ключ)"]