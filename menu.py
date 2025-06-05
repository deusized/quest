# menu.py
import sys
import pygame
import os
from typing import Optional, List
from game import start_game
from save_manager import load_game_data, has_save_file


class Button:
    def __init__(self, text: str, pos: tuple, action: str, font: pygame.font.Font,
                 enabled: bool = True):  # Добавили enabled
        self.text = text
        self.pos = pos
        self.action = action
        self.font = font
        self.rect = None
        self.bg_rect = None
        self.hovered = False
        self.enabled = enabled  # Состояние кнопки
        self.normal_color = (100, 100, 100) if enabled else (50, 50, 50)  # Цвет для неактивной кнопки
        self.hover_color = (150, 150, 150) if enabled else (50, 50, 50)
        self.text_color = (255, 255, 255) if enabled else (120, 120, 120)
        self.click_sound = self.load_sound("button_click.wav")

    def load_sound(self, filename: str) -> Optional[pygame.mixer.Sound]:
        try:
            path = os.path.join("materials", "audio", filename)
            if os.path.exists(path):
                return pygame.mixer.Sound(path)
            return None
        except Exception as e:
            print(f"Не удалось загрузить звук {filename}: {e}")
            return None

    def draw(self, surface: pygame.Surface):
        current_color = self.hover_color if self.hovered and self.enabled else self.normal_color

        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.pos)

        self.bg_rect = text_rect.inflate(30, 20)
        self.rect = text_rect  # Для старой логики check_hover, если bg_rect еще не создан

        pygame.draw.rect(surface, current_color, self.bg_rect, border_radius=5)
        pygame.draw.rect(surface, (70, 70, 70) if self.enabled else (40, 40, 40), self.bg_rect, 2, border_radius=5)

        surface.blit(text_surface, text_rect)

    def check_hover(self, mouse_pos: tuple):
        if not self.enabled:
            self.hovered = False
            return False

        if self.bg_rect:
            self.hovered = self.bg_rect.collidepoint(mouse_pos)
        else:  # Fallback if bg_rect not yet calculated (e.g., first frame)
            temp_text_surface = self.font.render(self.text, True, self.text_color)
            temp_text_rect = temp_text_surface.get_rect(center=self.pos)
            temp_bg_rect = temp_text_rect.inflate(30, 20)
            self.hovered = temp_bg_rect.collidepoint(mouse_pos)
        return self.hovered

    def play_click_sound(self) -> None:
        if self.click_sound and self.enabled:
            self.click_sound.play()


class VolumeSlider:
    def __init__(self, pos: tuple, length: int = 200):
        self.pos = pos
        self.length = length
        try:
            current_volume = pygame.mixer.music.get_volume()
        except pygame.error:  # Если микшер не инициализирован
            current_volume = 0.5
            # Попытка установить громкость, если микшер доступен
            try:
                pygame.mixer.music.set_volume(current_volume)
            except:
                pass

        self.handle_pos_x = pos[0] + int(current_volume * length)
        self.dragging = False
        self.slider_interaction_rect = pygame.Rect(pos[0] - 10, pos[1] - 15, length + 20,
                                                   30)  # Увеличили область взаимодействия

    def draw(self, surface: pygame.Surface):
        pygame.draw.line(surface, (150, 150, 150), (self.pos[0], self.pos[1]),
                         (self.pos[0] + self.length, self.pos[1]), 4)
        pygame.draw.circle(surface, (100, 100, 100), (self.handle_pos_x, self.pos[1]), 10)
        pygame.draw.circle(surface, (200, 200, 200), (self.handle_pos_x, self.pos[1]), 10, 2)

    def update(self, mouse_pos: tuple, mouse_pressed: bool):
        if mouse_pressed and self.slider_interaction_rect.collidepoint(mouse_pos):
            self.dragging = True

        if not mouse_pressed:  # mouse_buttons_pressed[0] is better for dragging
            self.dragging = False

        if self.dragging:
            self.handle_pos_x = max(self.pos[0], min(mouse_pos[0], self.pos[0] + self.length))
            volume = (self.handle_pos_x - self.pos[0]) / self.length
            try:
                pygame.mixer.music.set_volume(volume)
            except pygame.error as e:
                print(f"Ошибка установки громкости: {e}")


class Menu:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.current_menu = "main"

        try:
            font_path = os.path.join("materials", "gothic.ttf")
            self.font_large = pygame.font.Font(font_path, 48)
            self.font_medium = pygame.font.Font(font_path, 36)
        except Exception as e:
            print(f"Не удалось загрузить кастомный шрифт, используется системный: {e}")
            self.font_large = pygame.font.SysFont("Arial", 48)
            self.font_medium = pygame.font.SysFont("Arial", 36)

        try:
            bg_path = os.path.join("materials", "pics", "bgMenu.png")
            self.background = pygame.image.load(bg_path).convert()
            self.background = pygame.transform.scale(self.background, screen.get_size())
        except Exception as e:
            print(f"Не удалось загрузить фон, используется черный: {e}")
            self.background = pygame.Surface(screen.get_size())
            self.background.fill((0, 0, 0))

        try:
            if pygame.mixer.get_init() and not pygame.mixer.music.get_busy():  # Проверяем, инициализирован ли микшер
                music_path = os.path.join("materials", "audio", "background.mp3")
                if os.path.exists(music_path):
                    pygame.mixer.music.load(music_path)
                    pygame.mixer.music.set_volume(0.5)  # Устанавливаем громкость перед воспроизведением
                    pygame.mixer.music.play(-1)
        except pygame.error as e:
            print(f"Не удалось загрузить или воспроизвести фоновую музыку: {e}")

        self.buttons: List[Button] = []
        self.slider: Optional[VolumeSlider] = None
        self.setup_menus()

    def setup_menus(self):
        center_x = self.screen.get_width() // 2
        self.buttons = []
        self.slider = None

        if self.current_menu == "main":
            can_load = has_save_file()
            self.buttons = [
                Button("Новая игра", (center_x, 250), "new_game", self.font_large),
                Button("Загрузить игру", (center_x, 320), "load_game" if can_load else "no_load_file", self.font_large,
                       enabled=can_load),
                Button("Настройки", (center_x, 390), "settings", self.font_large),
                Button("Выход", (center_x, 460), "exit", self.font_large)
            ]
        elif self.current_menu == "settings":
            self.buttons = [
                Button("Назад", (center_x, 450), "back", self.font_medium)
            ]
            self.slider = VolumeSlider((center_x - 100, 300))
        elif self.current_menu == "exit_confirm":
            self.buttons = [
                Button("Да", (center_x - 70, 300), "exit_confirmed", self.font_medium),
                Button("Нет", (center_x + 70, 300), "back", self.font_medium)
            ]

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        # Используем get_pressed() для непрерывного состояния, но для кликов - MOUSEBUTTONDOWN
        mouse_buttons_pressed = pygame.mouse.get_pressed()
        left_mouse_clicked_this_frame = False

        action_to_perform = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.current_menu = "exit_confirm"
                self.setup_menus()
                return None  # Важно, чтобы не обрабатывать дальше

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Левый клик
                    left_mouse_clicked_this_frame = True

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.current_menu == "main":
                        self.current_menu = "exit_confirm"
                    elif self.current_menu == "exit_confirm":  # Возврат из подтверждения выхода
                        self.current_menu = "main"
                    else:  # Возврат из настроек и т.д.
                        self.current_menu = "main"
                    self.setup_menus()
                    return None  # Перестроили меню, выходим из обработки событий

        # Обработка кликов по кнопкам
        if left_mouse_clicked_this_frame:
            for button in self.buttons:
                if button.enabled and button.bg_rect and button.bg_rect.collidepoint(mouse_pos):
                    button.play_click_sound()
                    action_to_perform = button.action
                    break  # Клик обработан

        # Обновление слайдера и состояния наведения кнопок
        if self.slider:
            self.slider.update(mouse_pos, mouse_buttons_pressed[0])  # Передаем состояние ЛКМ

        for button in self.buttons:
            button.check_hover(mouse_pos)

        return action_to_perform

    def draw(self):
        self.screen.blit(self.background, (0, 0))

        if self.current_menu == "main":
            title_text = "Текстовый Квест"
            title_surface = self.font_large.render(title_text, True, (255, 255, 255))
            title_rect = title_surface.get_rect(center=(self.screen.get_width() // 2, 150))
            self.screen.blit(title_surface, title_rect)
        elif self.current_menu == "settings":
            settings_title = self.font_large.render("Настройки", True, (255, 255, 255))
            settings_rect = settings_title.get_rect(center=(self.screen.get_width() // 2, 150))
            self.screen.blit(settings_title, settings_rect)

            vol_text = self.font_medium.render("Громкость музыки:", True, (255, 255, 255))
            slider_x_start = self.screen.get_width() // 2 - 100  # Совпадает с VolumeSlider pos
            self.screen.blit(vol_text, (slider_x_start, 250))  # Над слайдером
            if self.slider:
                self.slider.draw(self.screen)
        elif self.current_menu == "exit_confirm":
            confirm_text = self.font_large.render("Вы уверены, что хотите выйти?", True, (255, 255, 255))
            # Отрисовка текста с переносом для длинных сообщений
            text_rect = pygame.Rect(self.screen.get_width() * 0.1, 130, self.screen.get_width() * 0.8, 100)
            # Используем draw_text_wrapped из game.py (если хотим общий, или свою реализацию)
            # Для простоты пока так:
            confirm_surf = self.font_large.render("Вы уверены?", True, (255, 255, 255))
            confirm_rect_msg = confirm_surf.get_rect(center=(self.screen.get_width() // 2, 150))
            self.screen.blit(confirm_surf, confirm_rect_msg)

            confirm_surf2 = self.font_medium.render("Что хотите выйти?", True, (255, 255, 255))
            confirm_rect_msg2 = confirm_surf2.get_rect(center=(self.screen.get_width() // 2, 200))
            self.screen.blit(confirm_surf2, confirm_rect_msg2)

        for button in self.buttons:
            button.draw(self.screen)

        pygame.display.flip()

    def run(self):
        menu_running = True
        while menu_running:
            action = self.handle_events()

            if action:
                if action == "new_game":
                    start_game(self.screen)  # Запускаем игру без загруженных данных
                    self.current_menu = "main"  # Возвращаемся в меню после игры
                    self.setup_menus()
                elif action == "load_game":
                    loaded_data = load_game_data()
                    if loaded_data:
                        start_game(self.screen, loaded_game_data=loaded_data)
                        self.current_menu = "main"
                        self.setup_menus()
                    else:
                        print(
                            "Файл сохранения не найден или поврежден (это не должно было случиться, кнопка неактивна).")
                elif action == "no_load_file":
                    print("Файл сохранения отсутствует. Кнопка 'Загрузить игру' неактивна.")
                    # Можно добавить визуальное уведомление на экране
                elif action == "settings":
                    self.current_menu = "settings"
                    self.setup_menus()
                elif action == "exit":
                    self.current_menu = "exit_confirm"
                    self.setup_menus()
                elif action == "exit_confirmed":
                    pygame.quit()
                    sys.exit()
                elif action == "back":
                    self.current_menu = "main"
                    self.setup_menus()

            self.draw()
            self.clock.tick(60)


def show_menu(screen: pygame.Surface):
    menu = Menu(screen)
    menu.run()