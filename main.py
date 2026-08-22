import math
import random
import sys
import pygame

# ==============================================================================
# SUBTITLE DATA (Hasil Rekaman Presisi)
# ==============================================================================
SUBTITLE_DATA = [
    ("You know it's true", 0.85),
    ("Yeah, I miss you", 5.03),
    ("You know it's true", 9.22),
    ("So, what if I call", 13.9),
    ("And you pick up the phone?", 18.4),
    ("And I use this holiday", 23.24),
    ("To make my way to your ghost", 26.54),
    ("Oh, what if you're lonely", 32.23),
]

FINE_OFFSET = 0.0

# ==============================================================================
# KONFIGURASI LAYAR & WARNA
# ==============================================================================
WIDTH, HEIGHT = 1100, 600
FPS = 60

HITAM_PEKAT = (2, 2, 4)
PUTIH_TERANG = (255, 255, 255)
ABU_REDUP = (150, 155, 175)

# Warna dasar oranye untuk planet & cincin (dulu putih/monokrom).
# Bintang latar belakang tetap putih supaya terasa seperti langit malam biasa.
STAR_WHITE = (255, 255, 255)
ORANGE_BASE = (255, 140, 30)


def shade(base, factor):
    """Menggelapkan/menerangkan warna dasar sesuai faktor (0..1+)."""
    factor = max(0.0, factor)
    return (
        min(255, int(base[0] * factor)),
        min(255, int(base[1] * factor)),
        min(255, int(base[2] * factor)),
    )


# ==============================================================================
# BINTANG BACKGROUND — versi "warp speed" luar angkasa, tetap putih,
# jumlah diperbanyak supaya langit terasa lebih padat.
# ==============================================================================
class Star:

    def __init__(self):
        self.reset(first=True)

    def reset(self, first=False):
        self.x = random.randint(-WIDTH, WIDTH)
        self.y = random.randint(-HEIGHT, HEIGHT)
        self.z = random.randint(1, WIDTH) if first else WIDTH
        self.speed = random.uniform(1.2, 5.5)
        self.size = random.uniform(0.8, 2.4)
        self.twinkle_phase = random.uniform(0, math.tau)
        self.twinkle_speed = random.uniform(1.5, 4.0)

    def move(self):
        self.z -= self.speed
        if self.z < 1:
            self.reset()

    def draw(self, surface, time_tick):
        factor = 200 / (self.z + 1)
        px = int(self.x * factor + WIDTH // 2)
        py = int(self.y * factor + HEIGHT // 2)

        if 0 < px < WIDTH and 0 < py < HEIGHT:
            draw_size = int(self.size * factor / 50) + 1

            twinkle = 0.5 + 0.5 * math.sin(time_tick * self.twinkle_speed + self.twinkle_phase)
            col = shade(STAR_WHITE, 0.35 + 0.65 * twinkle)

            if self.speed > 3.5 and draw_size >= 1:
                prev_z = self.z + self.speed * 2
                prev_factor = 200 / (prev_z + 1)
                ppx = int(self.x * prev_factor + WIDTH // 2)
                ppy = int(self.y * prev_factor + HEIGHT // 2)
                pygame.draw.line(surface, col, (ppx, ppy), (px, py), max(1, draw_size - 1))

            pygame.draw.circle(surface, col, (px, py), draw_size)


# ==============================================================================
# PLANET SEBAGAI KUMPULAN TITIK/BINTIK (PARTICLE SPHERE) — bukan garis lagi.
# Titik-titik disebar di permukaan bola secara acak (fixed per-planet),
# lalu setiap frame diputar & diproyeksikan, dengan shading terminator
# supaya tetap terasa bervolume. Warna dasar oranye.
# ==============================================================================
class Planet3D:

    def __init__(self, radius=110, num_points=1400):
        self.radius = radius
        self.rotation = 0.0

        # Sebar titik merata di permukaan bola (metode Fibonacci sphere)
        # supaya kepadatan bintik seragam, tidak menumpuk di kutub.
        self.points = []
        golden_angle = math.pi * (3.0 - math.sqrt(5.0))
        for i in range(num_points):
            y = 1 - (i / float(num_points - 1)) * 2  # dari 1 ke -1
            radius_at_y = math.sqrt(max(0.0, 1 - y * y))
            theta = golden_angle * i
            x = math.cos(theta) * radius_at_y
            z = math.sin(theta) * radius_at_y
            size_jitter = random.uniform(0.7, 1.3)
            self.points.append([x, y, z, size_jitter])

        # Band horizontal ala Jupiter dipakai untuk memodulasi kecerahan titik.
        self.bands = []
        lat = -0.95
        while lat < 0.95:
            band_h = random.uniform(0.06, 0.16)
            brightness = random.uniform(0.35, 1.0)
            self.bands.append((lat, band_h, brightness))
            lat += band_h + random.uniform(0.01, 0.04)

        self.spots = [
            {
                "lat": random.uniform(-0.35, 0.35),
                "lon0": random.uniform(0, math.tau),
                "size": random.uniform(0.12, 0.22),
                "dark": random.uniform(0.25, 0.55),
            }
            for _ in range(3)
        ]

    def update(self, dt):
        self.rotation += dt * 0.35

    def _band_brightness_at(self, v):
        best = 0.75
        for lat, band_h, brightness in self.bands:
            dist = abs(v - lat)
            if dist < band_h:
                t = 1.0 - (dist / band_h)
                best = best * (1 - t) + brightness * t
        return best

    def draw(self, surface, cx, cy):
        r = self.radius
        cos_r, sin_r = math.cos(self.rotation), math.sin(self.rotation)
        light_dir_x, light_dir_y = -0.55, -0.55

        for (x, y, z, size_jitter) in self.points:
            # Rotasi pada sumbu Y (planet berputar pada porosnya)
            rx = x * cos_r - z * sin_r
            rz = x * sin_r + z * cos_r
            ry = y

            # Hanya gambar titik yang menghadap kamera (belahan depan bola)
            if rz < -0.02:
                continue

            px = cx + rx * r
            py = cy + ry * r

            v = ry  # posisi lintang -1..1
            band_bright = self._band_brightness_at(v)

            lon = math.atan2(rz, rx)
            flow = 0.5 + 0.5 * math.sin(lon * 3.0 + v * 6.0)
            local_bright = band_bright * (0.85 + 0.15 * flow)

            for spot in self.spots:
                dlat = v - spot["lat"]
                dlon = ((lon - spot["lon0"] + math.pi) % math.tau) - math.pi
                dist2 = (dlat / spot["size"]) ** 2 + (dlon / (spot["size"] * 2.2)) ** 2
                if dist2 < 1.0:
                    local_bright *= spot["dark"] + (1 - spot["dark"]) * dist2

            # Shading bola sederhana (terminator): titik yg menghadap cahaya lebih terang
            shading = 0.25 + 0.75 * max(0.0, rz + light_dir_x * rx + light_dir_y * (-ry))
            shading = max(0.12, min(1.15, shading))

            brightness = local_bright * shading
            col = shade(ORANGE_BASE, brightness)

            dot_size = max(1, int(round(0.8 * size_jitter * (0.6 + 0.4 * rz))))
            pygame.draw.circle(surface, col, (int(px), int(py)), dot_size)


# ==============================================================================
# CINCIN PLANET (RING) SEBAGAI BINTIK-BINTIK — setiap titik cincin adalah
# koordinat (x, y, z) nyata di ruang 3D yang diputar & diproyeksikan dengan
# perspektif, lalu digambar sebagai titik kecil (bukan garis).
# ==============================================================================
class PlanetRing:

    def __init__(self, inner_radius, outer_radius, tilt_x=0.5, num_points=2200):
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self.tilt_x = tilt_x
        self.rotation = 0.0
        self.gaps = [random.uniform(0.3, 0.9) for _ in range(4)]
        self.focal = 520.0

        # Bangkitkan titik-titik cincin sekali di awal: posisi sudut & radius
        # acak merata di antara inner_radius..outer_radius, dengan celah (gaps)
        # membuat sebagian area lebih jarang titiknya (seperti celah asli cincin).
        self.points = []
        for _ in range(num_points):
            radius = random.uniform(inner_radius, outer_radius)
            frac = (radius - inner_radius) / (outer_radius - inner_radius + 1e-6)
            skip = False
            for g in self.gaps:
                if abs(frac - g) < 0.02 and random.random() < 0.85:
                    skip = True
                    break
            if skip:
                continue
            angle0 = random.uniform(0, math.tau)
            size_jitter = random.uniform(0.6, 1.3)
            self.points.append([angle0, radius, size_jitter])

    def update(self, dt):
        self.rotation += dt * 0.6

    def _project(self, x, y, z, cx, cy):
        cos_y, sin_y = math.cos(self.rotation), math.sin(self.rotation)
        rx = x * cos_y - z * sin_y
        rz = x * sin_y + z * cos_y
        ry = y

        wobble = 0.22
        wx = rx
        wy = ry * math.cos(wobble) - rz * math.sin(wobble)
        wz = ry * math.sin(wobble) + rz * math.cos(wobble)

        cos_t, sin_t = math.cos(self.tilt_x), math.sin(self.tilt_x)
        fy = wy * cos_t - wz * sin_t
        fz = wy * sin_t + wz * cos_t

        scale = self.focal / (self.focal + fz)
        px = cx + wx * scale
        py = cy + fy * scale
        return px, py, fz, scale

    def draw_half(self, surface, cx, cy, front: bool):
        """front=True menggambar bintik cincin yang lebih dekat ke kamera
        (fz < 0, digambar di atas planet). front=False menggambar bintik yang
        lebih jauh (fz >= 0, digambar di belakang planet)."""
        for (angle0, radius, size_jitter) in self.points:
            x3 = math.cos(angle0) * radius
            z3 = math.sin(angle0) * radius
            y3 = 0.0

            px, py, fz, scale = self._project(x3, y3, z3, cx, cy)

            is_front = fz < 0
            if is_front != front:
                continue

            depth_t = max(0.0, min(1.0, (fz + self.outer_radius) / (2 * self.outer_radius)))
            brightness = 0.85 - 0.35 * depth_t
            col = shade(ORANGE_BASE, min(1.0, brightness))

            dot_size = max(1, int(round(0.9 * size_jitter * scale)))
            pygame.draw.circle(surface, col, (int(px), int(py)), dot_size)


# ==============================================================================
# PROGRAM UTAMA
# ==============================================================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("TikTok Trend - Smooth Animated Lyrics")
    clock = pygame.time.Clock()

    stars = [Star() for _ in range(600)]

    PLANET_CENTER_X = int(WIDTH * 0.70)
    PLANET_CENTER_Y = HEIGHT // 2
    LYRICS_CENTER_X = int(WIDTH * 0.30)

    planet = Planet3D(radius=105)
    ring = PlanetRing(inner_radius=140, outer_radius=230, tilt_x=0.5)

    text_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ring_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    try:
        font_aktif = pygame.font.SysFont("arial", 35, bold=True)
        font_redup = pygame.font.SysFont("arial", 25)
    except Exception:
        font_aktif = pygame.font.Font(None, 35)
        font_redup = pygame.font.Font(None, 25)

    try:
        pygame.mixer.init()
        pygame.mixer.music.load("lagu.mp3")
        pygame.mixer.music.play()
    except Exception as e:
        print(f"\n[ERROR] Gagal memuat audio: {e}")
        return

    running = True
    while running:
        dt = clock.get_time() / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        music_pos_ms = pygame.mixer.music.get_pos()
        current_audio_time = (
            (music_pos_ms / 1000.0) + FINE_OFFSET if music_pos_ms >= 0 else 0.0
        )

        active_index = -1
        for i, (teks, timestamp) in enumerate(SUBTITLE_DATA):
            if current_audio_time >= timestamp:
                active_index = i

        time_tick = pygame.time.get_ticks() / 1000.0

        screen.fill(HITAM_PEKAT)

        # 1. Background Bintang (putih + kedip + trail warp)
        for star in stars:
            star.move()
            star.draw(screen, time_tick)

        planet.update(dt if dt > 0 else 1 / FPS)
        ring.update(dt if dt > 0 else 1 / FPS)

        # 2a. Separuh cincin (bintik) di BELAKANG planet
        ring_surface.fill((0, 0, 0, 0))
        ring.draw_half(ring_surface, PLANET_CENTER_X, PLANET_CENTER_Y, front=False)
        screen.blit(ring_surface, (0, 0))

        # 2b. Planet berupa bintik-bintik oranye (particle sphere)
        planet.draw(screen, PLANET_CENTER_X, PLANET_CENTER_Y)

        # 2c. Separuh cincin (bintik) di DEPAN planet
        ring_surface.fill((0, 0, 0, 0))
        ring.draw_half(ring_surface, PLANET_CENTER_X, PLANET_CENTER_Y, front=True)
        screen.blit(ring_surface, (0, 0))

        # 3. Subtitle Lirik
        text_surface.fill((0, 0, 0, 0))
        if active_index != -1:
            start_time = SUBTITLE_DATA[active_index][1]
            elapsed = current_audio_time - start_time

            anim_duration = 0.40
            progress = min(1.0, max(0.0, elapsed / anim_duration))

            alpha_val = int(progress * 255)
            y_offset = int((1.0 - progress) * 15)

            teks_aktif = SUBTITLE_DATA[active_index][0]
            surf_aktif = font_aktif.render(teks_aktif, True, PUTIH_TERANG)
            surf_aktif.set_alpha(alpha_val)
            rect_aktif = surf_aktif.get_rect(
                center=(LYRICS_CENTER_X, PLANET_CENTER_Y + y_offset)
            )
            text_surface.blit(surf_aktif, rect_aktif)

            if active_index + 1 < len(SUBTITLE_DATA):
                teks_next = SUBTITLE_DATA[active_index + 1][0]
                surf_next = font_redup.render(teks_next, True, ABU_REDUP)
                rect_next = surf_next.get_rect(
                    center=(LYRICS_CENTER_X, PLANET_CENTER_Y + 48)
                )
                text_surface.blit(surf_next, rect_next)

            if active_index - 1 >= 0:
                teks_prev = SUBTITLE_DATA[active_index - 1][0]
                surf_prev = font_redup.render(teks_prev, True, ABU_REDUP)
                rect_prev = surf_prev.get_rect(
                    center=(LYRICS_CENTER_X, PLANET_CENTER_Y - 48)
                )
                text_surface.blit(surf_prev, rect_prev)

        screen.blit(text_surface, (0, 0))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()