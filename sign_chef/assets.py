"""Procedural asset üretim yardımcıları."""

from __future__ import annotations

import math
import random
from typing import List, Tuple

import pygame

Color = pygame.Color
Surface = pygame.Surface

_WHITE = Color(255, 255, 255)
_BLACK = Color(0, 0, 0)


def _seeded_rng(key: str) -> random.Random:
    """Deterministik bir rastgele üretici döndür."""
    return random.Random(hash(key) & 0xFFFF_FFFF)


def _color_from_name(name: str) -> Color:
    """Malzeme adına göre canlı bir renk seç."""
    rng = _seeded_rng(f"color:{name}")
    hue = rng.randrange(0, 360)
    saturation = 60 + rng.randrange(0, 25)
    value = 80 + rng.randrange(0, 15)
    color = Color(0)
    color.hsva = (hue % 360, saturation, value, 100)
    return color


def _lighten(color: Color, amount: float) -> Color:
    return color.lerp(_WHITE, max(0.0, min(amount, 1.0)))


def _darken(color: Color, amount: float) -> Color:
    return color.lerp(_BLACK, max(0.0, min(amount, 1.0)))


def generate_background(size: Tuple[int, int]) -> Surface:
    """Pastel tonlu çizgiler ve şekiller ile arka plan üret."""
    width, height = size
    surf = Surface(size)

    top = Color(149, 207, 255)
    bottom = Color(255, 238, 209)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = top.lerp(bottom, ratio)
        pygame.draw.line(surf, color, (0, y), (width, y))

    table_y = int(height * 0.68)
    table_rect = pygame.Rect(0, table_y, width, height - table_y)
    pygame.draw.rect(surf, Color(250, 232, 210), table_rect)

    stripe_color = Color(236, 208, 182)
    for x in range(-40, width + 40, 80):
        pygame.draw.rect(surf, stripe_color, (x, table_y, 40, table_rect.height))

    bubble = Surface((160, 160), pygame.SRCALPHA)
    pygame.draw.circle(bubble, Color(255, 255, 255, 28), (60, 80), 60)
    pygame.draw.circle(bubble, Color(255, 255, 255, 36), (110, 60), 36)
    for i in range(12):
        bx = (i * 120) % width - 60
        by = 80 + (i % 3) * 24
        surf.blit(bubble, (bx, by), special_flags=pygame.BLEND_PREMULTIPLIED)

    return surf


def generate_plate_surface(size: Tuple[int, int]) -> Surface:
    width, height = size
    surf = Surface(size, pygame.SRCALPHA)
    base_rect = pygame.Rect(0, 0, width, height)
    rim_rect = base_rect.inflate(-40, -32)

    pygame.draw.ellipse(surf, Color(244, 244, 252), base_rect)
    pygame.draw.ellipse(surf, Color(230, 230, 240), base_rect, 6)
    pygame.draw.ellipse(surf, Color(255, 255, 255), rim_rect)

    highlight = Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(highlight, Color(255, 255, 255, 90), base_rect.inflate(-60, -50))
    surf.blit(highlight, (0, 0))

    shadow = Surface((width, 40), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, Color(0, 0, 0, 60), shadow.get_rect())
    return surf, shadow


def generate_tick_surface(diameter: int = 160) -> Surface:
    surf = Surface((diameter, diameter), pygame.SRCALPHA)
    rect = surf.get_rect()
    pygame.draw.circle(surf, Color(109, 202, 133), rect.center, rect.width // 2)
    pygame.draw.circle(surf, Color(232, 250, 237), rect.center, rect.width // 2 - 10)
    pts = [
        (rect.width * 0.28, rect.height * 0.52),
        (rect.width * 0.45, rect.height * 0.7),
        (rect.width * 0.74, rect.height * 0.32),
    ]
    pygame.draw.lines(surf, Color(55, 145, 85), False, pts, 16)
    pygame.draw.lines(surf, Color(255, 255, 255), False, pts, 6)
    return surf


def generate_cross_surface(diameter: int = 160) -> Surface:
    surf = Surface((diameter, diameter), pygame.SRCALPHA)
    rect = surf.get_rect()
    pygame.draw.circle(surf, Color(242, 123, 120), rect.center, rect.width // 2)
    pygame.draw.circle(surf, Color(254, 231, 229), rect.center, rect.width // 2 - 10)
    bar_color = Color(181, 60, 56)
    pygame.draw.line(surf, bar_color, (rect.width * 0.3, rect.height * 0.3), (rect.width * 0.7, rect.height * 0.7), 18)
    pygame.draw.line(surf, bar_color, (rect.width * 0.7, rect.height * 0.3), (rect.width * 0.3, rect.height * 0.7), 18)
    pygame.draw.line(surf, Color(255, 255, 255), (rect.width * 0.3, rect.height * 0.3), (rect.width * 0.7, rect.height * 0.7), 6)
    pygame.draw.line(surf, Color(255, 255, 255), (rect.width * 0.7, rect.height * 0.3), (rect.width * 0.3, rect.height * 0.7), 6)
    return surf


def generate_sign_frames(name: str, frame_size: Tuple[int, int] = (130, 130), frame_count: int = 12) -> List[Surface]:
    rng = _seeded_rng(f"sign:{name}")
    width, height = frame_size
    frames: List[Surface] = []
    bg = _lighten(_color_from_name(name), 0.4)
    stroke = _darken(bg, 0.3)
    accent = _color_from_name(f"accent:{name}")
    accent2 = _lighten(accent, 0.2)

    path_radius = min(width, height) * 0.28
    sparkle_data = [
        (
            rng.uniform(0.18, 0.82),
            rng.uniform(0.18, 0.82),
            rng.randint(4, 7),
        )
        for _ in range(6)
    ]

    for i in range(frame_count):
        surf = Surface(frame_size, pygame.SRCALPHA)
        rect = pygame.Rect(0, 0, width, height)
        pygame.draw.rect(surf, bg, rect, border_radius=32)
        pygame.draw.rect(surf, stroke, rect, 4, border_radius=32)

        for rel_x, rel_y, radius in sparkle_data:
            offset = math.sin(i / frame_count * math.tau + rel_x * math.pi) * 6
            sx = int(rect.x + rel_x * width)
            sy = int(rect.y + rel_y * height + offset)
            pygame.draw.circle(surf, Color(255, 255, 255, 60), (sx, sy), radius)

        angle = (i / frame_count) * math.tau
        center_x = width / 2 + math.cos(angle) * 8
        center_y = height / 2 + math.sin(angle) * 6
        pygame.draw.circle(surf, accent, (int(center_x), int(center_y)), int(path_radius))
        pygame.draw.circle(surf, accent2, (int(center_x - 6), int(center_y - 6)), int(path_radius * 0.7))

        for finger in range(4):
            finger_angle = angle + finger * 0.7
            fx = center_x + math.cos(finger_angle) * path_radius * 0.9
            fy = center_y + math.sin(finger_angle) * path_radius * 0.9
            radius = int(path_radius * (0.45 - finger * 0.07))
            color = accent2.lerp(_WHITE, 0.1 * finger)
            pygame.draw.circle(surf, color, (int(fx), int(fy)), max(radius, 6))

        orbit_angle = angle + math.pi / 2
        px = center_x + math.cos(orbit_angle) * path_radius * 1.2
        py = center_y + math.sin(orbit_angle) * path_radius * 1.2
        pygame.draw.circle(surf, Color(255, 255, 255, 150), (int(px), int(py)), 10)

        frames.append(surf)

    return frames


def generate_ingredient_icon(name: str, size: Tuple[int, int] = (96, 96)) -> Surface:
    width, height = size
    surf = Surface(size, pygame.SRCALPHA)
    base = _color_from_name(name)
    rect = pygame.Rect(0, 0, width, height)
    pygame.draw.rect(surf, _lighten(base, 0.35), rect, border_radius=28)
    pygame.draw.rect(surf, _darken(base, 0.2), rect, 4, border_radius=28)

    stripe_rect = rect.inflate(-26, -26)
    stripe_h = stripe_rect.height // 3
    for i in range(3):
        row_rect = pygame.Rect(
            stripe_rect.x,
            stripe_rect.y + i * stripe_h + 6,
            stripe_rect.width,
            stripe_h - 8,
        )
        color = _lighten(base, 0.1 * i)
        pygame.draw.rect(surf, color, row_rect, border_radius=18)

    sparkle = Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(sparkle, Color(255, 255, 255, 120), (width * 0.1, height * 0.05, width * 0.5, height * 0.25))
    surf.blit(sparkle, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

    return surf
