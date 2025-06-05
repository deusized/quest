# save_manager.py
import json
import os
from typing import Optional, List, Dict, Any

SAVE_FILE = "savegame.json"
MAX_HISTORY_TURNS = 3


def save_game_data(story_text: str, choices: List[str], history: List[Dict[str, str]]) -> bool:
    """Saves the current game state."""
    data_to_save = {
        "current_story_text": story_text,
        "current_choices": choices,
        "history": history[-MAX_HISTORY_TURNS:]  # Сохраняем только последние N ходов
    }
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print(f"Игра сохранена в {SAVE_FILE}")
        return True
    except Exception as e:
        print(f"Ошибка сохранения игры: {e}")
        return False


def load_game_data() -> Optional[Dict[str, Any]]:
    """Loads the game state."""
    if not os.path.exists(SAVE_FILE):
        # print("Файл сохранения не найден.") # Сообщение может быть излишним, если кнопка неактивна
        return None
    try:
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Игра загружена из {SAVE_FILE}")
        return data
    except Exception as e:
        print(f"Ошибка загрузки игры: {e}")
        return None


def has_save_file() -> bool:
    """Checks if a save file exists."""
    return os.path.exists(SAVE_FILE)