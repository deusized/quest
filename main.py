import pygame
import sys
import os
from menu import show_menu


class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error as e:
            print(f"Не удалось инициализировать pygame.mixer: {e}. Звука не будет.")

        self.fullscreen = False
        self.screen_width = 800
        self.screen_height = 600
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Текстовый Квест")

        try:
            icon_path = os.path.join("materials", "pics", "icon.png")
            if os.path.exists(icon_path):
                icon = pygame.image.load(icon_path)
                pygame.display.set_icon(icon)
            else:
                print(f"Файл иконки не найден: {icon_path}")
                icon_surface = pygame.Surface((32, 32))
                icon_surface.fill((100, 100, 100))
                pygame.draw.circle(icon_surface, (255,0,0), (16,16), 10)
                pygame.display.set_icon(icon_surface)
        except Exception as e:
            print(f"Не удалось загрузить иконку: {e}")

    def run(self):
        show_menu(self.screen)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game_instance = Game()
    game_instance.run()
