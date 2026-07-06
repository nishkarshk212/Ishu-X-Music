# Copyright (c) 2025 TheHamkerAlone 
# Licensed under the MIT License.
# This file is part of AloneX

import os
import asyncio
import random
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from collections import Counter
from ishu import config
from ishu.helpers import Track

try:
    from unidecode import unidecode
except ImportError:
    def unidecode(text):
        return text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_TITLE_PATH = os.path.join(BASE_DIR, "font.ttf")
FONT_INFO_PATH = os.path.join(BASE_DIR, "font2.ttf")
TEMPLATE_PATH = os.path.join(BASE_DIR, "..", "assets", "template.png")


def safe_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


class Thumbnail:
    def __init__(self):
        self.size = (1280, 720)
        self.font_title = safe_font(FONT_TITLE_PATH, 42)
        self.font_info = safe_font(FONT_INFO_PATH, 32)

    async def start(self):
        os.makedirs("cache", exist_ok=True)

        if not os.path.exists(FONT_TITLE_PATH):
            print(f"Missing font: {FONT_TITLE_PATH}")

        if not os.path.exists(FONT_INFO_PATH):
            print(f"Missing font: {FONT_INFO_PATH}")

        if not os.path.exists(TEMPLATE_PATH):
            print(f"Missing template: {TEMPLATE_PATH}")

        return True

    async def save_thumb(self, output_path: str, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        for attempt in range(3):
            try:
                if url.startswith("http"):
                    async with aiohttp.ClientSession(headers=headers) as session:
                        async with session.get(url, timeout=15) as resp:
                            if resp.status == 200:
                                content = await resp.read()
                                with open(output_path, "wb") as f:
                                    f.write(content)
                                return output_path
            except Exception as e:
                if attempt == 2:
                    print(f"Error saving thumb: {e}")
                await asyncio.sleep(1)
        return output_path

    def get_dominant_colors(self, img, n=3):
        # Resize for performance
        small_img = img.resize((50, 50), Image.Resampling.LANCZOS)
        pixels = list(small_img.getdata())
        # Ignore fully transparent pixels
        pixels = [p[:3] for p in pixels if len(p) < 4 or p[3] > 50]
        count = Counter(pixels)
        return [c[0] for c in count.most_common(n)]

    def create_simple_waveform(self, width, height, color):
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Generate symmetric waveform bars (mirrored from center)
        bar_count = 40
        bar_width = 6
        gap = 4
        total_width = bar_count * (bar_width + gap)
        start_x = (width - total_width) // 2
        
        for i in range(bar_count):
            x = start_x + i * (bar_width + gap)
            # Symmetric height (short in center, tall at ends)
            dist_from_center = abs(i - bar_count // 2)
            max_height = height - 10
            min_height = height // 4
            bar_height = max(min_height, max_height - (dist_from_center / (bar_count // 2)) * (max_height - min_height))
            bar_height = int(bar_height + random.randint(-5, 5))
            y_top = (height - bar_height) // 2
            y_bottom = y_top + bar_height
            draw.rectangle([x, y_top, x + bar_width, y_bottom], fill=(*color, 220))
        
        # Blur slightly
        img = img.filter(ImageFilter.GaussianBlur(0.5))
        return img

    async def generate(self, song: Track) -> str:
        try:
            os.makedirs("cache", exist_ok=True)
            temp = f"cache/temp_{song.id}.jpg"
            final_path = f"cache/{song.id}.jpg"
            if os.path.exists(final_path):
                return final_path

            await self.save_thumb(temp, song.thumbnail)
            
            try:
                src = Image.open(temp).convert("RGBA")
            except Exception:
                try:
                    src = Image.new("RGBA", (1280, 720), (30, 30, 30, 255))
                except Exception:
                    return config.DEFAULT_THUMB

            W, H = self.size

            # --- 1. ENHANCED ALBUM ART ---
            enhancer = ImageEnhance.Sharpness(src)
            src_enhanced = enhancer.enhance(1.1)
            color_enhancer = ImageEnhance.Color(src_enhanced)
            src_enhanced = color_enhancer.enhance(1.15)
            contrast_enhancer = ImageEnhance.Contrast(src_enhanced)
            src_enhanced = contrast_enhancer.enhance(1.05)

            # --- 2. DARK BLURRED BACKGROUND ---
            bg_ratio = W / H
            src_ratio = src.width / src.height
            if src_ratio > bg_ratio:
                new_w = int(src.height * bg_ratio)
                offset = (src.width - new_w) // 2
                bg = src.crop((offset, 0, offset + new_w, src.height))
            else:
                new_h = int(src.width / bg_ratio)
                offset = (src.height - new_h) // 2
                bg = src.crop((0, offset, src.width, offset + new_h))

            bg = bg.resize((W, H), Image.Resampling.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(45))
            bg = bg.convert("RGBA")
            # Dark overlay
            bg_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 150))
            bg = Image.alpha_composite(bg, bg_overlay)

            # Add vignette
            vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw_vignette = ImageDraw.Draw(vignette)
            draw_vignette.ellipse([-200, -200, W + 200, H + 200], fill=(0, 0, 0, 0))
            draw_vignette.ellipse([300, 150, W - 300, H - 150], fill=(0, 0, 0, 160))
            vignette = vignette.filter(ImageFilter.GaussianBlur(150))
            bg = Image.alpha_composite(bg, vignette)

            # --- 3. COVER ART (LEFT SIDE) ---
            cover_x, cover_y = 100, 110
            cover_w, cover_h = 500, 500
            cover_radius = 60

            # Large soft shadow for cover
            shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_layer)
            shadow_draw.rounded_rectangle(
                (cover_x + 15, cover_y + 15, cover_x + cover_w + 15, cover_y + cover_h + 15),
                radius=cover_radius + 10,
                fill=(0, 0, 0, 220),
            )
            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(35))
            bg = Image.alpha_composite(bg, shadow_layer)

            # Cover art
            cover_resized = src_enhanced.resize((cover_w, cover_h), Image.Resampling.LANCZOS)
            cover_mask = Image.new("L", (cover_w, cover_h), 0)
            ImageDraw.Draw(cover_mask).rounded_rectangle(
                (0, 0, cover_w, cover_h), radius=cover_radius, fill=255
            )
            bg.paste(cover_resized, (cover_x, cover_y), cover_mask)

            # --- 4. TEXT (RIGHT SIDE) ---
            draw = ImageDraw.Draw(bg)
            text_x = 680
            text_max_w = 500

            def ellipsize(s, font, max_w):
                if draw.textbbox((0, 0), s, font=font)[2] <= max_w:
                    return s
                lo, hi = 1, len(s)
                best = "…"
                while lo <= hi:
                    mid = (lo + hi) // 2
                    cand = s[:mid].rstrip() + "…"
                    if draw.textbbox((0, 0), cand, font=font)[2] <= max_w:
                        best = cand
                        lo = mid + 1
                    else:
                        hi = mid - 1
                return best

            # Get dominant color for accent
            dominant_colors = self.get_dominant_colors(src_enhanced)
            dominant_color = dominant_colors[0]

            # Title
            title_str = ellipsize(unidecode(str(song.title)), self.font_title, text_max_w)
            title_y = 180
            # Text shadow
            draw.text((text_x + 3, title_y + 3), title_str, fill=(0, 0, 0, 180), font=self.font_title)
            draw.text((text_x, title_y), title_str, fill=(255, 255, 255, 255), font=self.font_title)

            # Artist/Channel
            artist_str = ellipsize(unidecode(str(song.channel_name)), self.font_info, text_max_w + 40)
            artist_y = title_y + 70
            # Text shadow
            draw.text((text_x + 2, artist_y + 2), artist_str, fill=(0, 0, 0, 130), font=self.font_info)
            draw.text((text_x, artist_y), artist_str, fill=(235, 235, 235, 255), font=self.font_info)

            # --- 5. SIMPLE WAVEFORM (BOTTOM RIGHT) ---
            waveform_x = 680
            waveform_y = H - 180
            waveform_w = 500
            waveform_h = 80
            waveform = self.create_simple_waveform(waveform_w, waveform_h, dominant_color)
            bg.paste(waveform, (waveform_x, waveform_y), waveform)

            out = bg.convert("RGB")
            out.save(final_path, "JPEG", quality=92, optimize=True)

            try:
                if os.path.exists(temp):
                    os.remove(temp)
            except Exception:
                pass

            return final_path

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return config.DEFAULT_THUMB
