"""İşaretli Aşçı oyun döngüsü."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

import pygame

from .assets import (
    generate_background,
    generate_cross_surface,
    generate_ingredient_icon,
    generate_plate_surface,
    generate_sign_frames,
    generate_tick_surface,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
WINDOW_SIZE = (1024, 640)
SIGN_SIZE = (130, 130)
ICON_SIZE = (96, 96)
FPS = 60

DISPLAY_OVERRIDES: Dict[str, str] = {
    "bal": "Bal",
    "cilek": "Çilek",
    "cikolata": "Çikolata",
    "ekmek": "Ekmek",
    "falafel": "Falafel",
    "feslegen": "Fesleğen",
    "fistik": "Fıstık",
    "havuc": "Havuç",
    "humus": "Humus",
    "ketcap": "Ketçap",
    "kofte": "Köfte",
    "krep": "Krep",
    "krema": "Krema",
    "kruton": "Kruton",
    "limon": "Limon",
    "makarna": "Makarna",
    "marul": "Marul",
    "maydanoz": "Maydanoz",
    "mercimek": "Mercimek",
    "muz": "Muz",
    "nane": "Nane",
    "nohut": "Nohut",
    "pankek": "Pankek",
    "patates": "Patates",
    "peynir": "Peynir",
    "pirinc": "Pirinç",
    "salata": "Salata",
    "salatalik": "Salatalık",
    "sogan": "Soğan",
    "somon": "Somon",
    "sut": "Süt",
    "tarcin": "Tarçın",
    "tereyag": "Tereyağı",
    "ton_balik": "Ton Balığı",
    "tursu": "Turşu",
    "yaban_mersini": "Yaban Mersini",
    "yaprak": "Asma Yaprağı",
    "yogurt": "Yoğurt",
    "yufka": "Yufka",
    "yumurta": "Yumurta",
    "zeytin": "Zeytin",
    "zeytin_yagi": "Zeytinyağı",
}


def display_name(key: str) -> str:
    return DISPLAY_OVERRIDES.get(key, key.replace("_", " ").title())


@dataclass
class IngredientPlaced:
    name: str
    icon: pygame.Surface

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, pos: tuple[int, int]) -> None:
        rect = self.icon.get_rect(topleft=pos)
        shadow = pygame.Surface((rect.width, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, pygame.Color(0, 0, 0, 60), shadow.get_rect())
        surface.blit(shadow, (rect.x, rect.bottom - 6))
        surface.blit(self.icon, rect)
        label = font.render(display_name(self.name), True, (45, 40, 40))
        label_rect = label.get_rect(midtop=(rect.centerx, rect.bottom + 6))
        surface.blit(label, label_rect)


class SignSprite:
    def __init__(self, name: str, frames: Sequence[pygame.Surface], pos: tuple[int, int], fps: int = 8) -> None:
        self.name = name
        self.frames = list(frames)
        self.rect = self.frames[0].get_rect(topleft=pos)
        self.home = pygame.Vector2(pos)
        self.fps = fps
        self.timer = 0.0
        self.frame_index = 0
        self.playing = False
        self.dragging = False
        self.offset = pygame.Vector2()
        self.active = True

    def start_animation(self) -> None:
        if not self.active:
            return
        self.playing = True
        self.timer = 0.0

    def stop_animation(self) -> None:
        self.playing = False
        self.frame_index = 0

    def update(self, dt: float) -> None:
        if self.playing and self.active:
            self.timer += dt
            frame_duration = 1.0 / max(self.fps, 1)
            if self.timer >= frame_duration:
                self.timer -= frame_duration
                self.frame_index = (self.frame_index + 1) % len(self.frames)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.active:
            return
        surface.blit(self.frames[self.frame_index], self.rect)
        shadow = pygame.Surface((self.rect.width, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, pygame.Color(0, 0, 0, 55), shadow.get_rect())
        surface.blit(shadow, (self.rect.x, self.rect.bottom - 6))

    def return_home(self) -> None:
        self.rect.topleft = (int(self.home.x), int(self.home.y))


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("İşaretli Aşçı")
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.clock = pygame.time.Clock()

        self.background = generate_background(WINDOW_SIZE)
        self.plate, self.plate_shadow = generate_plate_surface((420, 260))
        self.plate_rect = self.plate.get_rect(center=(WINDOW_SIZE[0] // 2 - 160, WINDOW_SIZE[1] // 2 + 70))
        self.plate_shadow_rect = self.plate_shadow.get_rect(midtop=(self.plate_rect.centerx, self.plate_rect.bottom - 20))
        self.tick = generate_tick_surface(160)
        self.cross = generate_cross_surface(160)

        self.font_small = pygame.font.SysFont("DejaVu Sans", 20, bold=False)
        self.font = pygame.font.SysFont("DejaVu Sans", 26, bold=True)
        self.font_big = pygame.font.SysFont("DejaVu Sans", 56, bold=True)

        self.state = "menu"
        self.level_index = 0
        self.levels = self._load_levels()
        self.level_data: Dict[str, object] | None = None

        self.required: List[str] = []
        self.palette: List[str] = []
        self.sign_sprites: List[SignSprite] = []
        self.ingredient_icons: Dict[str, pygame.Surface] = {}
        self.placed: List[IngredientPlaced] = []
        self.dish_preview: pygame.Surface | None = None
        self.dish_rect = pygame.Rect(0, 0, 0, 0)

        self.feedback_timer = 0.0
        self.feedback_kind: str | None = None
        self.feedback_text = ""

    def _load_levels(self) -> List[Dict[str, object]]:
        with open(DATA_DIR / "levels.json", "r", encoding="utf-8") as fh:
            return json.load(fh)

    def load_level(self, index: int) -> None:
        level = self.levels[index]
        self.level_data = level
        self.required = list(level["required"])
        self.palette = list(level["palette"])
        self.sign_sprites = []
        self.placed = []
        self.feedback_timer = 0.0
        self.feedback_kind = None
        self.feedback_text = ""

        self.ingredient_icons = {name: generate_ingredient_icon(name, ICON_SIZE) for name in set(self.palette)}

        self._layout_signs()
        self._build_preview()

    def _layout_signs(self) -> None:
        start_x, start_y = 60, WINDOW_SIZE[1] - 170
        gap_x, gap_y = 150, 150
        per_row = 6
        self.sign_sprites.clear()
        for idx, name in enumerate(self.palette):
            col = idx % per_row
            row = idx // per_row
            pos = (start_x + col * gap_x, start_y + row * gap_y)
            frames = generate_sign_frames(name, SIGN_SIZE)
            sprite = SignSprite(name, frames, pos)
            sprite.home.update(pos)
            self.sign_sprites.append(sprite)

    def _build_preview(self) -> None:
        level_name = str(self.level_data.get("name", "")) if self.level_data else ""
        preview = pygame.Surface((220, 150), pygame.SRCALPHA)
        pygame.draw.rect(preview, pygame.Color(255, 255, 255, 235), preview.get_rect(), border_radius=24)
        pygame.draw.rect(preview, pygame.Color(208, 210, 232), preview.get_rect(), 4, border_radius=24)

        title = self.font.render(level_name, True, (54, 58, 90))
        preview.blit(title, title.get_rect(midtop=(preview.get_width() // 2, 14)))

        stack_h = 30
        for idx, name in enumerate(self.required):
            color = pygame.Color(0)
            color.hsva = ((hash(name) & 0xFFFF) % 360, 45, 90, 100)
            layer_rect = pygame.Rect(30, 60 + idx * (stack_h + 6), preview.get_width() - 60, stack_h)
            pygame.draw.rect(preview, color, layer_rect, border_radius=14)
            pygame.draw.rect(preview, pygame.Color(255, 255, 255, 90), layer_rect.inflate(-8, -14), border_radius=10)

        self.dish_preview = preview
        self.dish_rect = self.dish_preview.get_rect(topright=(WINDOW_SIZE[0] - 30, 24))

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = "menu"

                if self.state == "menu":
                    self._handle_menu_event(event)
                elif self.state == "play":
                    self._handle_play_event(event)
                elif self.state == "end":
                    self._handle_end_event(event)

            if self.state == "menu":
                self._draw_menu(dt)
            elif self.state == "play":
                self._update_play(dt)
                self._draw_play()
            else:
                self._draw_end()

            pygame.display.flip()

        pygame.quit()

    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._play_button_rect().collidepoint(event.pos):
                self.level_index = 0
                self.load_level(self.level_index)
                self.state = "play"

    def _handle_play_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for sprite in reversed(self.sign_sprites):
                if sprite.active and sprite.rect.collidepoint(event.pos):
                    sprite.dragging = True
                    sprite.start_animation()
                    sprite.offset.update(sprite.rect.x - event.pos[0], sprite.rect.y - event.pos[1])
                    break
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            for sprite in self.sign_sprites:
                if sprite.dragging:
                    sprite.dragging = False
                    placed = False
                    if self.plate_rect.collidepoint(sprite.rect.center):
                        placed = self._handle_drop(sprite)
                    if not placed:
                        sprite.return_home()
                    sprite.stop_animation()
        elif event.type == pygame.MOUSEMOTION:
            for sprite in self.sign_sprites:
                if sprite.dragging:
                    sprite.rect.topleft = (
                        int(event.pos[0] + sprite.offset.x),
                        int(event.pos[1] + sprite.offset.y),
                    )

    def _handle_end_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.state = "menu"

    def _update_play(self, dt: float) -> None:
        for sprite in self.sign_sprites:
            sprite.update(dt)

        if self.feedback_timer > 0:
            self.feedback_timer -= dt
            if self.feedback_timer <= 0:
                self.feedback_timer = 0
                self.feedback_kind = None
                self.feedback_text = ""

        if self._is_level_complete():
            self._show_completion()

    def _draw_menu(self, dt: float) -> None:  # noqa: ARG002
        self.screen.blit(self.background, (0, 0))
        title = self.font_big.render("İşaretli Aşçı", True, (54, 58, 90))
        self.screen.blit(title, title.get_rect(center=(WINDOW_SIZE[0] // 2, 180)))

        button_rect = self._play_button_rect()
        pygame.draw.rect(self.screen, pygame.Color(255, 255, 255), button_rect, border_radius=22)
        pygame.draw.rect(self.screen, pygame.Color(75, 80, 120), button_rect, 4, border_radius=22)
        label = self.font.render("OYNA", True, (75, 80, 120))
        self.screen.blit(label, label.get_rect(center=button_rect.center))

        info = self.font_small.render("Türk İşaret Dili ile malzemeleri öğren!", True, (60, 64, 92))
        self.screen.blit(info, info.get_rect(center=(WINDOW_SIZE[0] // 2, button_rect.bottom + 40)))

    def _draw_play(self) -> None:
        self.screen.blit(self.background, (0, 0))
        self.screen.blit(self.plate_shadow, self.plate_shadow_rect)
        self.screen.blit(self.plate, self.plate_rect)

        self._draw_required_panel()
        self._draw_palette_panel()
        self._draw_dish_preview()
        self._draw_feedback()

        for sprite in self.sign_sprites:
            if sprite.dragging:
                continue
            sprite.draw(self.screen)

        for sprite in self.sign_sprites:
            if sprite.dragging:
                sprite.draw(self.screen)

        self._draw_placed()

    def _draw_end(self) -> None:
        self.screen.blit(self.background, (0, 0))
        title = self.font_big.render("Tüm seviyeler tamamlandı!", True, (60, 100, 70))
        self.screen.blit(title, title.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2 - 40)))
        info = self.font.render("Yeni bir oyuna başlamak için tıkla", True, (75, 80, 120))
        self.screen.blit(info, info.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2 + 30)))

    def _draw_required_panel(self) -> None:
        if not self.level_data:
            return
        panel_rect = pygame.Rect(260, 22, 420, 150)
        pygame.draw.rect(self.screen, pygame.Color(255, 255, 255), panel_rect, border_radius=24)
        pygame.draw.rect(self.screen, pygame.Color(208, 210, 232), panel_rect, 3, border_radius=24)

        title = self.font.render(str(self.level_data.get("name", "")), True, (54, 58, 90))
        self.screen.blit(title, title.get_rect(midtop=(panel_rect.centerx, panel_rect.y + 16)))

        for idx, name in enumerate(self.required):
            text = self.font_small.render(f"• {display_name(name)}", True, (70, 74, 110))
            self.screen.blit(text, (panel_rect.x + 24, panel_rect.y + 60 + idx * 28))

        level_text = self.font_small.render(
            f"Seviye {self.level_index + 1} / {len(self.levels)}", True, (90, 94, 130)
        )
        self.screen.blit(level_text, (panel_rect.x + 24, panel_rect.bottom - 32))

    def _draw_palette_panel(self) -> None:
        panel_rect = pygame.Rect(40, WINDOW_SIZE[1] - 190, WINDOW_SIZE[0] - 80, 150)
        pygame.draw.rect(self.screen, pygame.Color(255, 255, 255, 230), panel_rect, border_radius=26)
        pygame.draw.rect(self.screen, pygame.Color(185, 189, 220), panel_rect, 3, border_radius=26)
        caption = self.font_small.render("İşaret kartları - tıklayıp tabağa sürükle", True, (70, 74, 110))
        self.screen.blit(caption, (panel_rect.x + 24, panel_rect.y + 12))

    def _draw_dish_preview(self) -> None:
        if self.dish_preview:
            self.screen.blit(self.dish_preview, self.dish_rect)

    def _draw_feedback(self) -> None:
        if self.feedback_kind:
            icon = self.tick if self.feedback_kind == "ok" else self.cross
            icon_rect = icon.get_rect(midbottom=(self.plate_rect.centerx, self.plate_rect.y - 14))
            self.screen.blit(icon, icon_rect)
            if self.feedback_kind == "no" and self.feedback_text:
                label = self.font.render(self.feedback_text, True, (170, 60, 60))
                self.screen.blit(label, label.get_rect(midtop=(icon_rect.centerx, icon_rect.bottom + 6)))

    def _draw_placed(self) -> None:
        if not self.placed:
            return
        gap = 22
        icon_w, icon_h = ICON_SIZE
        total = len(self.placed)
        total_width = total * icon_w + (total - 1) * gap
        start_x = self.plate_rect.centerx - total_width // 2
        y = self.plate_rect.centery - icon_h // 2 + 12
        for idx, placed in enumerate(self.placed):
            placed.draw(self.screen, self.font_small, (start_x + idx * (icon_w + gap), y))

    def _handle_drop(self, sprite: SignSprite) -> bool:
        already = {item.name for item in self.placed}
        if sprite.name in self.required and sprite.name not in already:
            icon = self.ingredient_icons[sprite.name]
            self.placed.append(IngredientPlaced(sprite.name, icon))
            sprite.active = False
            sprite.return_home()
            self.feedback_kind = "ok"
            self.feedback_text = ""
            self.feedback_timer = 1.2
            return True
        self.feedback_kind = "no"
        self.feedback_text = display_name(sprite.name)
        self.feedback_timer = 1.6
        return False

    def _is_level_complete(self) -> bool:
        return len(self.placed) == len(self.required) and {
            item.name for item in self.placed
        } == set(self.required)

    def _show_completion(self) -> None:
        tick_scaled = pygame.transform.smoothscale(self.tick, (220, 220))
        rect = tick_scaled.get_rect(center=(WINDOW_SIZE[0] // 2, WINDOW_SIZE[1] // 2 - 20))
        self.screen.blit(tick_scaled, rect)
        congrats = self.font_big.render("TEBRİKLER!", True, (50, 110, 70))
        self.screen.blit(congrats, congrats.get_rect(center=(WINDOW_SIZE[0] // 2, rect.bottom + 80)))
        pygame.display.flip()
        pygame.time.delay(1000)
        self.level_index += 1
        if self.level_index >= len(self.levels):
            self.state = "end"
        else:
            self.load_level(self.level_index)

    def _play_button_rect(self) -> pygame.Rect:
        return pygame.Rect(WINDOW_SIZE[0] // 2 - 120, WINDOW_SIZE[1] // 2 - 40, 240, 80)


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
