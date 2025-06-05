# game.py
import pygame
import sys
import os
from typing import Optional, Dict, List, Any
from ai import get_ai_response
import save_manager

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_SLATE_BLUE = (72, 61, 139)
LIGHT_SLATE_GREY = (119, 136, 153)
HOVER_LIGHT_SLATE_GREY = (159, 176, 193)
TEXT_COLOR = WHITE
ERROR_COLOR = (255, 100, 100)
LOADING_COLOR = (200, 200, 200)
SAVE_SUCCESS_COLOR = (100, 255, 100)

# Размеры и отступы
PADDING = 20
CHOICE_BUTTON_HEIGHT = 50
CHOICE_BUTTON_SPACING = 10
BOTTOM_BAR_HEIGHT = CHOICE_BUTTON_HEIGHT + 10  # Высота для кнопок меню и сохранения


# Вспомогательная функция для отрисовки текста с переносом строк
def draw_text_wrapped(surface, text, rect, font, color, aa=True):
    lines = []
    words = text.split(' ')
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] <= rect.width:
            current_line = test_line
        else:
            lines.append(current_line.strip())
            current_line = word + " "
    lines.append(current_line.strip())

    y = rect.top
    line_height = font.get_linesize()
    for line_idx, line_text in enumerate(lines):
        if y + line_height > rect.bottom:
            if line_idx > 0:  # Попытка добавить многоточие, если текст не влезает
                # Удаляем последнюю отрисованную строку (сложно без перерисовки)
                # Проще просто обрезать и, возможно, показать "..." на последней видимой строке
                if len(lines[line_idx - 1]) > 3:
                    prev_line_surf = font.render(lines[line_idx - 1][:-3] + "...", aa, color)
                    # Нужно очистить область предыдущей строки и нарисовать новую
                    # Это усложнение, пока просто прерываем вывод
                    pass  # Placeholder для улучшения
            break
        text_surface = font.render(line_text, aa, color)
        surface.blit(text_surface, (rect.left, y))
        y += line_height
    return y


class GameChoiceButton:
    def __init__(self, text: str, pos: tuple, width: int, height: int, font: pygame.font.Font, action_text: str):
        self.text_to_display = text
        self.action_text = action_text
        self.font = font
        self.rect = pygame.Rect(pos[0], pos[1], width, height)
        self.hovered = False
        self.normal_color = LIGHT_SLATE_GREY
        self.hover_color = HOVER_LIGHT_SLATE_GREY
        self.text_color = TEXT_COLOR
        self.click_sound = None
        try:
            path = os.path.join("materials", "audio", "button_click.wav")
            if os.path.exists(path):
                self.click_sound = pygame.mixer.Sound(path)
        except pygame.error as e:
            print(f"Не удалось загрузить звук клика для игровой кнопки: {e}")

    def draw(self, surface: pygame.Surface):
        color = self.hover_color if self.hovered else self.normal_color
        pygame.draw.rect(surface, color, self.rect, border_radius=8)

        text_surf = self.font.render(self.text_to_display, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)

        if text_rect.width > self.rect.width - PADDING:
            available_width = self.rect.width - PADDING
            avg_char_width = self.font.size("a")[0] if self.font.size("a")[0] > 0 else 10
            max_chars = available_width // avg_char_width
            display_text = self.text_to_display[:max_chars - 3] + "..." if len(
                self.text_to_display) > max_chars else self.text_to_display
            text_surf = self.font.render(display_text, True, self.text_color)
            text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos: tuple) -> bool:
        self.hovered = self.rect.collidepoint(mouse_pos)
        return self.hovered

    def handle_click(self) -> str:
        if self.click_sound:
            self.click_sound.play()
        return self.action_text


def start_game(screen: pygame.Surface, loaded_game_data: Optional[Dict[str, Any]] = None):
    pygame.display.set_caption("Текстовый Квест - Приключение")
    game_running = True
    clock = pygame.time.Clock()
    screen_width, screen_height = screen.get_size()

    try:
        font_path = os.path.join("materials", "gothic.ttf")
        story_font = pygame.font.Font(font_path, 26)
        choice_font = pygame.font.Font(font_path, 22)
        message_font = pygame.font.Font(font_path, 18)
    except:
        print("Не удалось загрузить кастомный шрифт, используется системный.")
        story_font = pygame.font.SysFont("Arial", 26)
        choice_font = pygame.font.SysFont("Arial", 22)
        message_font = pygame.font.SysFont("Arial", 18)

    current_story_text = "Загрузка..."
    current_choices: List[str] = []
    game_history: List[Dict[str, str]] = []
    story_context_for_ai = ""  # Последний текст истории от ИИ (для добавления в game_history)

    ui_buttons: List[GameChoiceButton] = []
    status_message = ""
    status_message_color = LOADING_COLOR
    is_loading_ai_response = True

    story_area_height = int(screen_height * 0.60)
    story_rect = pygame.Rect(PADDING, PADDING, screen_width - 2 * PADDING, story_area_height - 2 * PADDING)

    choices_area_y_start = story_area_height + PADDING
    choices_area_height = screen_height - choices_area_y_start - PADDING - BOTTOM_BAR_HEIGHT

    # Кнопки внизу экрана
    button_bar_y = screen_height - PADDING - (CHOICE_BUTTON_HEIGHT - 10)  # Y для кнопок "В меню" и "Сохранить"
    back_to_menu_button = GameChoiceButton(
        "В Меню",
        (screen_width - PADDING - 150, button_bar_y),
        150, CHOICE_BUTTON_HEIGHT - 10, choice_font, "##BACK_TO_MENU##"
    )
    save_game_button = GameChoiceButton(
        "Сохранить",
        (screen_width - PADDING - 150 - 10 - 150, button_bar_y),  # Левее кнопки "В Меню"
        150, CHOICE_BUTTON_HEIGHT - 10, choice_font, "##SAVE_GAME##"
    )

    def update_ui_elements(story_text: str, choices_list: List[str]):
        nonlocal current_story_text, current_choices, ui_buttons, story_context_for_ai
        nonlocal is_loading_ai_response, status_message, status_message_color

        current_story_text = story_text
        current_choices = choices_list
        story_context_for_ai = story_text  # Обновляем контекст для следующего хода

        ui_buttons = []
        if not choices_list:
            is_loading_ai_response = False
            if not status_message or "Ошибка" not in status_message:  # Не перезаписывать сообщение об ошибке
                status_message = "Нет доступных действий. Возможно, это конец?"
                status_message_color = TEXT_COLOR
            return

        button_width = screen_width - 2 * PADDING
        # max_buttons_in_view = choices_area_height // (CHOICE_BUTTON_HEIGHT + CHOICE_BUTTON_SPACING)
        # visible_choices = choices_list[:max_buttons_in_view]
        # Пока отображаем все, если их будет слишком много, нужно будет добавить прокрутку
        visible_choices = choices_list

        for i, choice_action in enumerate(visible_choices):
            display_text = (choice_action[:70] + "...") if len(choice_action) > 73 else choice_action
            button_y = choices_area_y_start + i * (CHOICE_BUTTON_HEIGHT + CHOICE_BUTTON_SPACING)
            if button_y + CHOICE_BUTTON_HEIGHT > choices_area_y_start + choices_area_height:  # Не выходить за область
                break
            btn = GameChoiceButton(display_text, (PADDING, button_y), button_width, CHOICE_BUTTON_HEIGHT, choice_font,
                                   choice_action)
            ui_buttons.append(btn)

        is_loading_ai_response = False
        # Очищаем статус, если не было ошибки при загрузке элементов
        if "Ошибка" not in status_message and "заблокирован" not in status_message:
            status_message = ""

    if loaded_game_data:
        current_story_text = loaded_game_data.get("current_story_text", "Ошибка загрузки истории.")
        current_choices = loaded_game_data.get("current_choices", ["Ошибка загрузки вариантов."])
        game_history = loaded_game_data.get("history", [])
        story_context_for_ai = current_story_text  # Восстанавливаем контекст

        update_ui_elements(current_story_text, current_choices)
        status_message = "Игра загружена."
        status_message_color = LOADING_COLOR
        is_loading_ai_response = False
    else:
        game_history = []  # Новая игра, пустая история
        status_message = "ИИ пишет для вас историю..."
        status_message_color = LOADING_COLOR
        # Для "Начало истории..." game_history пуст и это нормально
        raw_story, raw_choices = get_ai_response("Начало истории...", game_history)
        update_ui_elements(raw_story, raw_choices)
        if "Ошибка" in raw_story or "заблокирован" in raw_story:
            status_message = raw_story
            status_message_color = ERROR_COLOR

    while game_running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if is_loading_ai_response:
                        continue

                    # Обработка кнопок "В Меню" и "Сохранить"
                    if back_to_menu_button.check_hover(mouse_pos):
                        action = back_to_menu_button.handle_click()
                        if action == "##BACK_TO_MENU##":
                            game_running = False
                            continue

                    if save_game_button.check_hover(mouse_pos):
                        action = save_game_button.handle_click()
                        if action == "##SAVE_GAME##":
                            if save_manager.save_game_data(current_story_text, current_choices, game_history):
                                status_message = "Игра успешно сохранена!"
                                status_message_color = SAVE_SUCCESS_COLOR
                            else:
                                status_message = "Ошибка при сохранении игры."
                                status_message_color = ERROR_COLOR
                            # Не выходим, просто показываем сообщение
                            continue  # Предотвращаем обработку других кнопок в этот клик

                    for button in ui_buttons:
                        if button.check_hover(mouse_pos):
                            chosen_action = button.handle_click()

                            # Добавляем текущий ход в историю *перед* получением нового ответа
                            if story_context_for_ai and chosen_action:  # story_context_for_ai - это current_story_text
                                game_history.append({"story": story_context_for_ai, "player_action": chosen_action})
                                # Ограничиваем размер истории в памяти
                                if len(game_history) > save_manager.MAX_HISTORY_TURNS:
                                    game_history = game_history[-save_manager.MAX_HISTORY_TURNS:]

                            is_loading_ai_response = True
                            status_message = "ИИ обдумывает ваш выбор..."
                            status_message_color = LOADING_COLOR
                            current_story_text = "Пожалуйста, подождите..."
                            current_choices = []
                            ui_buttons = []

                            screen.fill(BLACK)
                            draw_text_wrapped(screen, current_story_text, story_rect, story_font, TEXT_COLOR)
                            if status_message:
                                msg_surf = message_font.render(status_message, True, status_message_color)
                                msg_rect = msg_surf.get_rect(center=(screen_width // 2, choices_area_y_start - 20))
                                screen.blit(msg_surf, msg_rect)
                            back_to_menu_button.draw(screen)
                            save_game_button.draw(screen)
                            pygame.display.flip()

                            new_story, new_choices = get_ai_response(chosen_action, game_history)
                            update_ui_elements(new_story, new_choices)
                            if "Ошибка" in new_story or "заблокирован" in new_story:  # Если ИИ вернул ошибку
                                status_message = new_story
                                status_message_color = ERROR_COLOR
                            elif not status_message:  # Если не было ошибки, но статус был (напр. "Игра сохранена"), не стираем его сразу
                                pass  # Статус останется от сохранения или будет очищен в update_ui_elements

                            break

        if not is_loading_ai_response:
            for button in ui_buttons:
                button.check_hover(mouse_pos)
        back_to_menu_button.check_hover(mouse_pos)
        save_game_button.check_hover(mouse_pos)

        screen.fill(BLACK)
        pygame.draw.rect(screen, DARK_SLATE_BLUE, story_rect, border_radius=10)
        story_text_render_rect = story_rect.inflate(-PADDING, -PADDING)
        draw_text_wrapped(screen, current_story_text, story_text_render_rect, story_font, TEXT_COLOR)

        if not is_loading_ai_response:
            for button in ui_buttons:
                button.draw(screen)

        back_to_menu_button.draw(screen)
        save_game_button.draw(screen)

        if status_message:
            # Позиционируем сообщение
            message_y_pos = choices_area_y_start - PADDING - message_font.get_height() / 2
            if message_y_pos < story_rect.bottom + PADDING:
                message_y_pos = story_rect.bottom + PADDING + message_font.get_height() / 2

            status_rect_width = screen_width - 2 * PADDING
            # Очищаем область под текстом статуса, чтобы избежать наложения
            clear_rect = pygame.Rect(PADDING, message_y_pos - message_font.get_height(), status_rect_width,
                                     message_font.get_height() * 2 + 5)
            pygame.draw.rect(screen, BLACK, clear_rect)

            status_render_rect = pygame.Rect(PADDING, message_y_pos - message_font.get_height() / 2, status_rect_width,
                                             message_font.get_height() * 3)
            draw_text_wrapped(screen, status_message, status_render_rect, message_font, status_message_color)

        pygame.display.flip()
        clock.tick(30)

    pygame.display.set_caption("Текстовый Квест")