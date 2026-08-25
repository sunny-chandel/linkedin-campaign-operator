#!/usr/bin/env python3
"""Render the deterministic animated hero used at the top of README.md."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "claude-linkedin-hero.gif"
WIDTH, HEIGHT = 960, 540
FRAME_COUNT = 52

BG = (10, 10, 10)
SURFACE = (17, 17, 17)
BORDER = (45, 45, 45)
TEXT = (245, 245, 240)
DIM = (136, 136, 136)
CORAL = (224, 120, 80)
GREEN = (74, 222, 128)
BLUE = (96, 165, 250)
AMBER = (240, 168, 48)


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        ["/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc"]
        if mono
        else [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/SFNS.ttf",
            "/System/Library/Fonts/SFNS.ttf" if not bold else "/System/Library/Fonts/HelveticaNeue.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for candidate in candidates:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


DISPLAY = font(60, bold=True)
DISPLAY_SMALL = font(58, bold=True)
MONO = font(13, mono=True)
MONO_SMALL = font(10, mono=True)
MONO_BOLD = font(11, bold=True, mono=True)


def ease(value: float) -> float:
    return value * value * (3 - 2 * value)


def path_position(points: list[tuple[float, float]], progress: float) -> tuple[float, float]:
    segment_count = len(points) - 1
    location = progress * segment_count
    index = min(int(location), segment_count - 1)
    local = ease(location - index)
    x1, y1 = points[index]
    x2, y2 = points[index + 1]
    return x1 + (x2 - x1) * local, y1 + (y2 - y1) * local


def centered_text(draw: ImageDraw.ImageDraw, y: int, value: str, face: ImageFont.FreeTypeFont, fill: tuple[int, int, int]) -> None:
    box = draw.textbbox((0, 0), value, font=face)
    draw.text(((WIDTH - (box[2] - box[0])) / 2, y), value, font=face, fill=fill)


def cursor(draw: ImageDraw.ImageDraw, x: float, y: float, label: str, color: tuple[int, int, int]) -> None:
    draw.polygon([(x, y), (x + 8, y + 18), (x + 12, y + 10), (x + 21, y + 9)], fill=color)
    text_box = draw.textbbox((0, 0), label, font=MONO_BOLD)
    width = text_box[2] - text_box[0] + 14
    draw.rectangle((x + 14, y + 12, x + 14 + width, y + 33), fill=color)
    draw.text((x + 21, y + 16), label, font=MONO_BOLD, fill=BG)


def render_frame(index: int) -> Image.Image:
    progress = index / FRAME_COUNT
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    for x in range(0, WIDTH, 48):
        draw.line((x, 0, x, HEIGHT), fill=(14, 14, 14), width=1)
    for y in range(0, HEIGHT, 48):
        draw.line((0, y, WIDTH, y), fill=(14, 14, 14), width=1)

    draw.rectangle((0, 0, WIDTH, 64), fill=(9, 9, 9))
    draw.rectangle((56, 26, 69, 39), fill=CORAL)
    draw.text((80, 25), "CLAUDE LINKEDIN", font=MONO_BOLD, fill=TEXT)
    draw.text((737, 27), "8 SKILLS  //  1 MEMORY", font=MONO_SMALL, fill=DIM)

    intro = ease(min(progress / 0.18, 1.0))
    title_alpha = int(255 * (0.68 + 0.32 * intro))
    title_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    title_draw = ImageDraw.Draw(title_layer)
    offset_x = int(-36 * (1 - intro))
    line1 = "YOUR LINKEDIN TEAM"
    line2 = "IN CLAUDE."
    line1_box = title_draw.textbbox((0, 0), line1, font=DISPLAY)
    line2_box = title_draw.textbbox((0, 0), line2, font=DISPLAY_SMALL)
    title_draw.text(((WIDTH - line1_box[2]) / 2 + offset_x, 136), line1, font=DISPLAY, fill=(*TEXT, title_alpha))
    title_draw.text(((WIDTH - line2_box[2]) / 2 + offset_x, 205), line2, font=DISPLAY_SMALL, fill=(*CORAL, title_alpha))
    image = Image.alpha_composite(image.convert("RGBA"), title_layer).convert("RGB")
    draw = ImageDraw.Draw(image)

    centered_text(draw, 294, "RESEARCH  ·  PRODUCE  ·  ENGAGE  ·  LEARN  ·  RESUME", MONO_SMALL, DIM)

    terminal = (138, 352, 822, 470)
    draw.rectangle(terminal, fill=SURFACE, outline=BORDER, width=1)
    draw.line((138, 386, 822, 386), fill=BORDER, width=1)
    draw.text((157, 366), "CLAUDE LINKEDIN  //  CAMPAIGN LIVE", font=MONO_SMALL, fill=DIM)
    draw.ellipse((758, 365, 767, 374), fill=GREEN)
    draw.text((775, 366), "ADAPTIVE", font=MONO_SMALL, fill=GREEN)

    command = ">  start my LinkedIn growth campaign"
    type_progress = (progress * 1.45) % 1.0
    visible = command[: max(1, int(len(command) * min(type_progress / 0.55, 1.0)))]
    draw.text((158, 405), visible, font=MONO, fill=CORAL)
    if int(progress * 16) % 2 == 0:
        cursor_x = 158 + draw.textlength(visible, font=MONO) + 4
        draw.rectangle((cursor_x, 406, cursor_x + 7, 421), fill=CORAL)

    stages = ["RESEARCH", "PRODUCE", "ENGAGE", "LEARN"]
    stage_index = min(int(progress * len(stages)), len(stages) - 1)
    draw.text((158, 442), "CURRENT STAGE", font=MONO_SMALL, fill=DIM)
    draw.text((279, 440), stages[stage_index], font=MONO_BOLD, fill=TEXT)
    bar_left, bar_right = 632, 798
    draw.rectangle((bar_left, 443, bar_right, 449), fill=(32, 32, 32))
    fill_right = bar_left + int((bar_right - bar_left) * ((progress * 4) % 1.0))
    draw.rectangle((bar_left, 443, fill_right, 449), fill=CORAL)

    sweep_x = int(-180 + progress * (WIDTH + 360))
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.polygon([(sweep_x, 64), (sweep_x + 150, 64), (sweep_x - 20, HEIGHT), (sweep_x - 170, HEIGHT)], fill=(224, 120, 80, 8))
    glow = glow.filter(ImageFilter.GaussianBlur(24))
    image = Image.alpha_composite(image.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(image)

    paths = [
        ([(18, 80), (170, 100), (420, 76), (775, 110), (680, 260), (210, 250), (18, 80)], "RESEARCH", CORAL, 0.00),
        ([(18, 116), (260, 90), (735, 160), (820, 286), (470, 310), (115, 210), (18, 116)], "WRITE", CORAL, 0.00),
        ([(18, 152), (120, 270), (405, 318), (760, 248), (610, 92), (205, 82), (18, 152)], "ENGAGE", GREEN, 0.00),
        ([(18, 188), (330, 290), (820, 210), (680, 76), (295, 120), (110, 300), (18, 188)], "LEARN", BLUE, 0.00),
    ]
    for points, label, color, phase in paths:
        x, y = path_position(points, (progress + phase) % 1.0)
        cursor(draw, x, y, label, color)

    draw.text((56, 505), "OPEN SOURCE  //  CLAUDE CODE + CODEX", font=MONO_SMALL, fill=DIM)
    draw.text((768, 505), "v1.1.0", font=MONO_SMALL, fill=CORAL)
    return image


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames = [render_frame(index) for index in range(FRAME_COUNT)]
    palette_frames = [frame.quantize(colors=112, method=Image.Quantize.MEDIANCUT) for frame in frames]
    palette_frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=palette_frames[1:],
        duration=76,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
