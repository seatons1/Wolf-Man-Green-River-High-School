import asyncio
import math
import random
from pathlib import Path
import sys
from array import array

import pygame

END_MESSAGE_DURATION = 10.0  # Seconds to show the final result before accepting a choice.

MAX_TIGERS = 10  # Fixed number of tigers; eaten tigers do not respawn.


# ============================================================
# WOLF-MAN
# Pygame + Pygbag browser edition
#
# Features:
#   - Title screen
#   - Green River High School wolf mascot image as the player
#   - Sound effects
#   - Procedural background music
#   - Browser-persistent high score via localStorage
#   - Async game loop required by Pygbag
#
# No external image/audio assets are required.
# ============================================================

pygame.init()

TILE = 28
COLS = 25
ROWS = 23
HUD_HEIGHT = 70
WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + HUD_HEIGHT
FPS = 60

BLACK = (5, 5, 10)
NAVY = (4, 8, 8)
BLUE = (40, 210, 70)
LIGHT_BLUE = (120, 255, 90)
WHITE = (245, 245, 245)
YELLOW = (255, 220, 40)
RED = (235, 65, 65)
PINK = (255, 130, 180)
CYAN = (70, 230, 255)
ORANGE = (255, 160, 50)
GRAY = (150, 150, 160)
DARK_GRAY = (45, 45, 55)
GREEN = (90, 230, 130)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Wolf-Man")

clock = pygame.time.Clock()

font = pygame.font.SysFont("arial", 24, bold=True)
title_font = pygame.font.SysFont("arial", 52, bold=True)
subtitle_font = pygame.font.SysFont("arial", 22, bold=True)
small_font = pygame.font.SysFont("arial", 16, bold=True)


# ============================================================
# ROCK SPRINGS TIGER MASCOT
# ============================================================

ASSET_DIR = Path(__file__).resolve().parent / "assets"
TIGER_PATH = ASSET_DIR / "tiger_mascot.png"

try:
    tiger_image = pygame.image.load(str(TIGER_PATH)).convert_alpha()
    tiger_image = pygame.transform.smoothscale(tiger_image, (56, 56))
except Exception:
    tiger_image = None


WOLF_PATH = ASSET_DIR / "wolf_character.png"

try:
    wolf_character_image = pygame.image.load(str(WOLF_PATH)).convert_alpha()
    wolf_character_image = pygame.transform.smoothscale(wolf_character_image, (82, 82))
except Exception:
    wolf_character_image = None

# Green River High School arcade title artwork.
TITLE_ART_PATH = ASSET_DIR / "wolfman_arcade_title.png"

try:
    title_art = pygame.image.load(str(TITLE_ART_PATH)).convert()
except Exception:
    title_art = None



# ============================================================
# MAZE
# ============================================================

MAZE = [
    "#########################",
    "#o.........#.........o.#",
    "#.###.####.#.####.###.#",
    "#.....#.........#.....#",
    "#.###.#.#######.#.###.#",
    "#.....#...###...#.....#",
    "#####.###.#.#.###.#####",
    "    #.#...#...#...#.#    ",
    "#####.#.##     ##.#.#####",
    "    #...#   G   #...#    ",
    "#####.#.##     ##.#.#####",
    "    #.#...#####...#.#    ",
    "#####.#.###...###.#.#####",
    "#.........#.#.#.........#",
    "#.###.###.#.#.#.###.###.#",
    "#...#.....#...#.....#...#",
    "###.#.###.#####.###.#.###",
    "#.....#.........#.....#",
    "#.###.#.#######.#.###.#",
    "#o....#....P....#....o.#",
    "#########################",
    "#########################",
    "#########################",
]

MAZE = [row.ljust(COLS, "#")[:COLS] for row in MAZE]
grid = [list(row) for row in MAZE]

player_start = None
ghost_starts = []

for row in range(ROWS):
    for col in range(COLS):
        if grid[row][col] == "P":
            player_start = (col, row)
            grid[row][col] = " "
        elif grid[row][col] == "G":
            ghost_starts.append((col, row))
            grid[row][col] = " "

if player_start is None:
    player_start = (COLS // 2, ROWS - 2)

# Multiple safe starting locations spread around the maze.
# The wolf hunts these tigers, while the player can steer the wolf.
TIGER_STARTS = [
    (1, 1), (11, 1), (21, 1),
    (3, 5), (12, 5), (19, 5),
    (5, 11), (17, 11),
    (3, 19), (19, 19),
]

# Extra power pellets: spread around the playable maze so the wolf has
# frequent opportunities to turn the tables on the tigers.
POWER_TILES = [
    (1, 1), (11, 1), (21, 1),
    (5, 3), (19, 3),
    (5, 5), (19, 5),
    (3, 13), (21, 13),
    (11, 19),
]

# Keep only open tiles; fall back to the original ghost location if needed.
TIGER_STARTS = [pos for pos in TIGER_STARTS if not is_wall(*pos)] if 'is_wall' in globals() else TIGER_STARTS
if not TIGER_STARTS:
    TIGER_STARTS = ghost_starts or [(COLS // 2, ROWS // 2)]


# ============================================================
# DIRECTIONS
# ============================================================

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

DIRECTIONS = {
    pygame.K_UP: UP,
    pygame.K_DOWN: DOWN,
    pygame.K_LEFT: LEFT,
    pygame.K_RIGHT: RIGHT,
    pygame.K_w: UP,
    pygame.K_s: DOWN,
    pygame.K_a: LEFT,
    pygame.K_d: RIGHT,
}

ALL_DIRECTIONS = [UP, DOWN, LEFT, RIGHT]


# ============================================================
# BROWSER HIGH SCORE
# ============================================================

HIGH_SCORE_KEY = "wolf_man_high_score"


GAME_BACKGROUND = (12, 70, 32)  # Dark green game background
def load_high_score():
    """Load the high score from browser localStorage when running under Pygbag."""
    if sys.platform == "emscripten":
        try:
            from platform import window
            value = window.localStorage.getItem(HIGH_SCORE_KEY)
            if value is not None:
                return int(str(value))
        except Exception:
            pass
    return 0


def save_high_score(value):
    """Save the high score to browser localStorage when available."""
    if sys.platform == "emscripten":
        try:
            from platform import window
            window.localStorage.setItem(HIGH_SCORE_KEY, str(int(value)))
        except Exception:
            pass


high_score = load_high_score()


# ============================================================
# AUDIO
#
# We generate simple PCM sounds in memory, so there are no
# external audio files to package. The first keypress/click
# starts the game and unlocks browser audio.
# ============================================================

audio_ready = False
music_enabled = True
sound_enabled = True

eat_sound = None
power_sound = None
ghost_sound = None
death_sound = None
start_sound = None

ON_WISCONSIN_PATH = (
    ASSET_DIR / "on_wisconsin.ogg"
    if sys.platform == "emscripten"
    else ASSET_DIR / "on_wisconsin.mp3"
)


def make_tone(frequency, duration, volume=0.20, wave_type="square"):
    """Create a small pygame Sound entirely in memory."""
    sample_rate = 22050
    count = max(1, int(sample_rate * duration))
    samples = array("h")

    for i in range(count):
        t = i / sample_rate

        if wave_type == "sine":
            value = math.sin(2 * math.pi * frequency * t)
        else:
            value = 1.0 if math.sin(2 * math.pi * frequency * t) >= 0 else -1.0

        attack = min(1.0, i / max(1, int(sample_rate * 0.01)))
        release = min(1.0, (count - i) / max(1, int(sample_rate * 0.04)))
        envelope = min(attack, release)

        samples.append(int(32767 * volume * value * envelope))

    return pygame.mixer.Sound(buffer=samples.tobytes())


def init_audio():
    """Initialize audio after the user has interacted with the page."""
    global audio_ready
    global eat_sound, power_sound, ghost_sound
    global death_sound, start_sound

    if audio_ready:
        return

    try:
        pygame.mixer.init(
            frequency=22050,
            size=-16,
            channels=2,
            buffer=512,
        )

        eat_sound = make_tone(760, 0.055, 0.16)
        power_sound = make_tone(330, 0.16, 0.20, "sine")
        ghost_sound = make_tone(110, 0.20, 0.22, "square")
        death_sound = make_tone(95, 0.50, 0.25, "sine")
        start_sound = make_tone(520, 0.16, 0.18, "square")

        # User supplied the recording. It is loaded as the game's
        # looping background music after browser interaction.
        try:
            pygame.mixer.music.load(str(ON_WISCONSIN_PATH))
            pygame.mixer.music.set_volume(0.32)
        except Exception:
            pass

        audio_ready = True

    except Exception:
        audio_ready = False


def play_sound(sound):
    if sound_enabled and audio_ready and sound is not None:
        try:
            sound.play()
        except Exception:
            pass


def update_music(now):
    """Keep the supplied On Wisconsin recording looping."""
    if not audio_ready or not music_enabled:
        return

    try:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1)
    except Exception:
        pass


# ============================================================
# GAME STATE
# ============================================================

score = 0
lives = 3
power_mode = False
power_timer = 0

game_state = "title"
end_message_timer = 0.0
new_record = False
invulnerable_timer = 0


# ============================================================
# UTILITY
# ============================================================

def tile_center(col, row):
    return (
        col * TILE + TILE // 2,
        HUD_HEIGHT + row * TILE + TILE // 2,
    )


def get_tile(x, y):
    col = int((x % WIDTH) // TILE)
    row = int((y - HUD_HEIGHT) // TILE)
    row = max(0, min(ROWS - 1, row))
    return col, row


def is_wall(col, row):
    if col < 0 or col >= COLS or row < 0 or row >= ROWS:
        return True
    return grid[row][col] == "#"


def can_move(col, row, direction):
    dx, dy = direction
    return not is_wall(col + dx, row + dy)


# Validate the planned tiger spawn tiles now that is_wall exists.
TIGER_STARTS = [pos for pos in TIGER_STARTS if not is_wall(*pos)]
if not TIGER_STARTS:
    TIGER_STARTS = ghost_starts or [(COLS // 2, ROWS // 2)]


def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


# ============================================================
# PROCEDURAL WOLF SPRITES
# ============================================================

wolf_sprites = {}


def make_wolf_sprite(direction, frame):
    """Use the supplied Green River wolf artwork as the player sprite."""
    key = (direction, frame)
    if key in wolf_sprites:
        return wolf_sprites[key]

    if wolf_character_image is None:
        # Fallback if the image asset cannot be loaded.
        size = 64
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surface, GREEN, (size // 2, size // 2), 27, 4)
        pygame.draw.circle(surface, GRAY, (size // 2, size // 2), 20)
        wolf_sprites[key] = surface
        return surface

    # Keep the mascot front-facing so the distinctive school wolf
    # remains recognizable while it hunts through the maze.
    bob = [-2, 0, 2, 0][frame]
    sprite = pygame.Surface((92, 92), pygame.SRCALPHA)
    center = (46, 46 + bob)

    # Green glow makes the wolf easy to see against the maze.
    pygame.draw.circle(sprite, GREEN, center, 44, 3)
    pygame.draw.circle(sprite, (40, 255, 90, 55), center, 40, 6)

    rect = wolf_character_image.get_rect(center=center)
    sprite.blit(wolf_character_image, rect)

    wolf_sprites[key] = sprite
    return sprite



def draw_wolf(x, y, direction, animation_frame):
    sprite = make_wolf_sprite(direction, animation_frame)
    rect = sprite.get_rect(center=(int(x), int(y)))
    screen.blit(sprite, rect)


# ============================================================
# DRAW MAZE
# ============================================================

def draw_maze():
    screen.fill(BLACK)

    pygame.draw.rect(
        screen,
        NAVY,
        (0, 0, WIDTH, HUD_HEIGHT),
    )

    score_text = font.render(
        f"SCORE: {score}",
        True,
        WHITE,
    )
    high_text = small_font.render(
        f"BEST: {high_score}",
        True,
        LIGHT_BLUE,
    )
    lives_text = font.render(
        f"LIVES: {lives}",
        True,
        WHITE,
    )
    tiger_text = small_font.render(
        f"TIGERS TO HUNT: {len(ghosts)}",
        True,
        ORANGE,
    )

    screen.blit(score_text, (18, 14))
    screen.blit(tiger_text, (190, 22))
    screen.blit(
        high_text,
        (20, 45),
    )
    screen.blit(
        lives_text,
        (WIDTH - lives_text.get_width() - 18, 24),
    )

    # Show the wolf's remaining lives as small mascot icons.
    if wolf_character_image is not None:
        icon = pygame.transform.smoothscale(wolf_character_image, (24, 24))
        for i in range(lives):
            screen.blit(icon, (WIDTH - 28 - i * 28, 46))

    if invulnerable_timer > 0:
        safe_text = small_font.render("WOLF RECOVERING!", True, CYAN)
        screen.blit(safe_text, (WIDTH // 2 - safe_text.get_width() // 2, 45))

    # Walls
    for row in range(ROWS):
        for col in range(COLS):
            if grid[row][col] == "#":
                rect = pygame.Rect(
                    col * TILE,
                    HUD_HEIGHT + row * TILE,
                    TILE,
                    TILE,
                )

                pygame.draw.rect(
                    screen,
                    NAVY,
                    rect,
                )

                pygame.draw.rect(
                    screen,
                    BLUE,
                    rect.inflate(-4, -4),
                    2,
                    border_radius=5,
                )

    # Pellets
    for row in range(ROWS):
        for col in range(COLS):
            x, y = tile_center(col, row)

            if grid[row][col] == ".":
                pygame.draw.circle(
                    screen,
                    YELLOW,
                    (x, y),
                    3,
                )

            elif grid[row][col] == "o":
                radius = (
                    7
                    + int(
                        2
                        * math.sin(
                            pygame.time.get_ticks() * 0.008
                        )
                    )
                )

                pygame.draw.circle(
                    screen,
                    YELLOW,
                    (x, y),
                    radius,
                )


# ============================================================
# ENEMY DRAWING
# ============================================================

def draw_tiger(x, y, frightened=False, animation_frame=0):
    """Draw the uploaded Rock Springs Tiger mascot as an enemy."""
    if tiger_image is None:
        # Fallback if the image asset cannot be loaded.
        pygame.draw.circle(
            screen,
            CYAN if frightened else RED,
            (int(x), int(y)),
            14,
        )
        return

    bob = (-2, -1, 1, 0)[animation_frame % 4]
    sprite = tiger_image

    if frightened:
        tinted = sprite.copy()
        overlay = pygame.Surface(
            tinted.get_size(),
            pygame.SRCALPHA,
        )
        overlay.fill((40, 210, 255, 70))
        tinted.blit(
            overlay,
            (0, 0),
            special_flags=pygame.BLEND_RGBA_ADD,
        )
        sprite = tinted

    rect = sprite.get_rect(
        center=(int(x), int(y + bob))
    )

    screen.blit(sprite, rect)

    if frightened:
        pygame.draw.circle(
            screen,
            CYAN,
            (int(x), int(y)),
            29,
            2,
        )


def draw_ghost(x, y, color, frightened=False):
    # Compatibility wrapper for the existing game code.
    draw_tiger(
        x,
        y,
        frightened=frightened,
        animation_frame=(pygame.time.get_ticks() // 110) % 4,
    )


# ============================================================
# WOLF
# ============================================================

class Wolf:
    def __init__(self):
        self.reset()

    def reset(self):
        col, row = player_start

        self.x, self.y = tile_center(col, row)
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.speed = 3.2
        self.auto_hunt = True
        self.manual_override = 0
        self.animation_timer = 0

    def set_direction(self, direction):
        # Keyboard input always takes priority over automatic hunting.
        self.next_direction = direction
        self.manual_override = FPS * 3

    def choose_hunt_direction(self):
        if not ghosts:
            return

        col, row = get_tile(self.x, self.y)
        target = min(ghosts, key=lambda g: distance(self.x, self.y, g.x, g.y))
        options = [d for d in ALL_DIRECTIONS if can_move(col, row, d)]
        if not options:
            return

        reverse = (-self.direction[0], -self.direction[1])
        non_reverse = [d for d in options if d != reverse]
        choices = non_reverse or options

        self.next_direction = min(
            choices,
            key=lambda d: distance(
                self.x + d[0] * TILE,
                self.y + d[1] * TILE,
                target.x,
                target.y,
            ),
        )

    def update(self):
        self.animation_timer += 1

        if self.manual_override > 0:
            self.manual_override -= 1

        col, row = get_tile(self.x, self.y)
        center_x, center_y = tile_center(col, row)
        at_center = (
            abs(self.x - center_x) <= 1.0
            and abs(self.y - center_y) <= 1.0
        )

        if at_center:
            self.x, self.y = center_x, center_y

            # Player input gets first choice. Once the player stops steering,
            # the wolf automatically hunts the nearest tiger.
            if self.manual_override <= 0 and self.auto_hunt:
                self.choose_hunt_direction()

            if can_move(col, row, self.next_direction):
                self.direction = self.next_direction
            elif not can_move(col, row, self.direction):
                options = [d for d in ALL_DIRECTIONS if can_move(col, row, d)]
                if options:
                    self.direction = random.choice(options)
                    self.next_direction = self.direction

        dx, dy = self.direction

        # Move only if the current direction has an open tile.
        if can_move(col, row, self.direction):
            target_col = col + dx
            target_row = row + dy
            target_x, target_y = tile_center(target_col, target_row)

            new_x = self.x + dx * self.speed
            new_y = self.y + dy * self.speed

            if dx > 0 and new_x >= target_x:
                self.x, self.y = target_x, target_y
            elif dx < 0 and new_x <= target_x:
                self.x, self.y = target_x, target_y
            elif dy > 0 and new_y >= target_y:
                self.x, self.y = target_x, target_y
            elif dy < 0 and new_y <= target_y:
                self.x, self.y = target_x, target_y
            else:
                self.x, self.y = new_x, new_y
        else:
            # At a wall, stop at the tile center and wait for a valid turn.
            self.x, self.y = center_x, center_y
            if self.manual_override <= 0:
                self.choose_hunt_direction()
                if can_move(col, row, self.next_direction):
                    self.direction = self.next_direction

        if self.x < -TILE:
            self.x = WIDTH + TILE
        elif self.x > WIDTH + TILE:
            self.x = -TILE

        self.collect()

    def collect(self):
        global score, power_mode, power_timer, high_score

        col, row = get_tile(self.x, self.y)

        if grid[row][col] == ".":
            grid[row][col] = " "
            score += 10
            play_sound(eat_sound)

        elif grid[row][col] == "o":
            grid[row][col] = " "
            score += 50
            power_mode = True
            power_timer = FPS * 8
            play_sound(power_sound)

        if score > high_score:
            high_score = score

    def draw(self):
        animation_frame = (self.animation_timer // 7) % 4
        draw_wolf(self.x, self.y, self.direction, animation_frame)


# ============================================================
# GHOST
# ============================================================

class Ghost:
    """Tiger that moves deliberately from tile center to tile center."""
    COLORS = [RED, PINK, ORANGE, CYAN]

    def __init__(self, index, start):
        self.index = index
        self.color = self.COLORS[index % len(self.COLORS)]
        self.reset(start)

    def reset(self, start):
        col, row = start
        if is_wall(col, row):
            open_tiles = [
                (c, r)
                for r in range(ROWS)
                for c in range(COLS)
                if not is_wall(c, r)
            ]
            col, row = random.choice(open_tiles)

        self.col, self.row = col, row
        self.direction = RIGHT
        self.progress = 0.0

        # All tigers use a controlled speed.  They differ only slightly.
        # This is deliberately much slower than the wolf.
        self.speed = 0.009 + (self.index % 4) * 0.0007
        self.animation_timer = random.randint(0, 30)

        valid = self.valid_directions()
        self.direction = random.choice(valid) if valid else RIGHT

        # Force a decision regularly so tigers travel throughout the maze
        # instead of remaining on a single horizontal corridor.
        self.decision_tiles = random.randint(1, 3)

        self.x, self.y = tile_center(col, row)

    def valid_directions(self):
        # Tigers are strictly confined to the visible maze corridors.
        # Edge columns are reserved for the decorative tunnel openings, so
        # tigers are never allowed to enter those off-board spaces.
        valid = []
        for dx, dy in ALL_DIRECTIONS:
            nc, nr = self.col + dx, self.row + dy
            if 1 <= nc <= COLS - 2 and 0 <= nr < ROWS and not is_wall(nc, nr):
                valid.append((dx, dy))
        return valid

    def choose_direction(self):
        possible = self.valid_directions()
        if not possible:
            self.direction = (0, 0)
            return

        reverse = (-self.direction[0], -self.direction[1])
        non_reverse = [d for d in possible if d != reverse]
        choices = non_reverse or possible

        # At intersections, deliberately mix roaming and fleeing behavior.
        # This prevents every tiger from following the same row.
        if len(choices) > 1 and random.random() < 0.55:
            self.direction = random.choice(choices)
            return

        # Otherwise prefer a direction that increases distance from the wolf.
        self.direction = max(
            choices,
            key=lambda d: self.target_distance(d) + random.uniform(-TILE * 2, TILE * 2),
        )

    def target_distance(self, direction):
        dx, dy = direction
        nc = self.col + dx
        nr = self.row + dy

        if nc < 1 or nc > COLS - 2 or nr < 0 or nr >= ROWS or is_wall(nc, nr):
            return -99999

        tx, ty = tile_center(nc, nr)
        return distance(tx, ty, wolf.x, wolf.y)

    def advance_one_tile(self):
        dx, dy = self.direction
        nc = self.col + dx
        nr = self.row + dy

        if nc < 1 or nc > COLS - 2 or nr < 0 or nr >= ROWS or is_wall(nc, nr):
            self.progress = 0.0
            self.choose_direction()
            return

        self.col, self.row = nc, nr
        self.progress = 0.0

        self.decision_tiles -= 1
        valid = self.valid_directions()

        # Turn at intersections or after a short corridor segment.
        if len(valid) > 2 or self.decision_tiles <= 0:
            self.choose_direction()
            self.decision_tiles = random.randint(1, 3)
        elif self.direction not in valid:
            self.choose_direction()
            self.decision_tiles = random.randint(1, 3)

    def update(self):
        self.animation_timer += 1

        # Progress is always a fraction of exactly one tile.
        self.progress += self.speed

        while self.progress >= 1.0:
            self.progress -= 1.0
            self.advance_one_tile()

        dx, dy = self.direction
        nc = self.col + dx
        nr = self.row + dy

        if nc < 1 or nc > COLS - 2 or nr < 0 or nr >= ROWS or is_wall(nc, nr):
            self.x, self.y = tile_center(self.col, self.row)
            self.progress = 0.0
            self.choose_direction()
            return

        cx, cy = tile_center(self.col, self.row)

        if 1 <= nc <= COLS - 2 and 0 <= nr < ROWS and not is_wall(nc, nr):
            nx, ny = tile_center(nc, nr)
            self.x = cx + (nx - cx) * self.progress
            self.y = cy + (ny - cy) * self.progress
        else:
            self.x, self.y = cx, cy
            self.progress = 0.0
            self.choose_direction()

        # Hard safety clamp: the tiger can never leave the playable board.
        self.x = max(1 * TILE + TILE // 2, min((COLS - 2) * TILE + TILE // 2, self.x))
        self.y = max(HUD_HEIGHT + TILE // 2, min(HEIGHT - TILE // 2, self.y))

    def draw(self):
        animation_frame = (self.animation_timer // 8) % 4
        draw_tiger(
            self.x,
            self.y,
            frightened=power_mode,
            animation_frame=animation_frame,
        )


# ============================================================
# OBJECTS
# ============================================================

wolf = Wolf()

# Eight tigers give the wolf plenty to hunt and eat.
ghosts = [
    Ghost(i, TIGER_STARTS[i % len(TIGER_STARTS)])
    for i in range(10)
]


# ============================================================
# GAME RESET
# ============================================================

def reset_pellets():
    # Rebuild pellets from the maze, then add a larger set of power pellets.
    # Only place power pellets on genuine open tiles.
    for row in range(ROWS):
        for col in range(COLS):
            original = MAZE[row][col]
            grid[row][col] = "." if original == "." else ("o" if original == "o" else " ")

    for col, row in POWER_TILES:
        if 0 <= col < COLS and 0 <= row < ROWS and grid[row][col] != "#":
            grid[row][col] = "o"


def reset_positions():
    wolf.reset()

    for i, ghost in enumerate(ghosts):
        ghost.reset(TIGER_STARTS[i % len(TIGER_STARTS)])


def new_game():
    global score
    global lives
    global power_mode
    global power_timer
    global game_state
    global new_record
    global invulnerable_timer
    global end_message_timer

    score = 0
    lives = 3
    power_mode = False
    power_timer = 0
    new_record = False
    invulnerable_timer = 0
    end_message_timer = 0.0

    # Recreate exactly 10 tigers at the start of every new game.
    ghosts.clear()
    for i in range(10):
        ghosts.append(Ghost(i, TIGER_STARTS[i % len(TIGER_STARTS)]))

    reset_pellets()
    reset_positions()

    game_state = "playing"

    play_sound(start_sound)


# ============================================================
# END-OF-GAME
# ============================================================

def finish_score():
    global high_score
    global new_record

    if score > high_score:
        high_score = score
        new_record = True
        save_high_score(high_score)


def remaining_pellets():
    total = 0

    for row in grid:
        total += row.count(".")
        total += row.count("o")

    return total


# ============================================================
# COLLISIONS
# ============================================================

def handle_collisions():
    global score, lives, game_state, invulnerable_timer, power_mode, power_timer, end_message_timer

    # During the short respawn period, the wolf cannot lose another life.
    if invulnerable_timer > 0:
        return

    for ghost in ghosts[:]:
        # Generous collision radius makes contact reliable.
        if distance(wolf.x, wolf.y, ghost.x, ghost.y) < TILE * 0.90:
            if power_mode:
                # POWER MODE: the wolf eats the tiger permanently.
                score += 200
                play_sound(ghost_sound)
                ghosts.remove(ghost)

                # Victory is based on eating all 10 tigers, not clearing pellets.
                if not ghosts:
                    finish_score()
                    game_state = "victory"
                    end_message_timer = END_MESSAGE_DURATION
                return

            # NORMAL MODE: a tiger catches the wolf and the wolf loses a life.
            lives -= 1
            play_sound(death_sound)
            power_mode = False
            power_timer = 0
            invulnerable_timer = FPS * 2

            if lives <= 0:
                finish_score()
                game_state = "game_over"
                end_message_timer = END_MESSAGE_DURATION
                return

            reset_positions()
            return


# ============================================================
# PLAYING UPDATE
# ============================================================

def update_game():
    global power_mode
    global power_timer
    global game_state
    global invulnerable_timer
    global end_message_timer

    if invulnerable_timer > 0:
        invulnerable_timer -= 1

    if power_mode:
        power_timer -= 1

        if power_timer <= 0:
            power_mode = False
            power_timer = 0

    wolf.update()

    for ghost in ghosts:
        ghost.update()

    handle_collisions()

    # The win condition is eating all 10 tigers.
    if not ghosts and game_state == "playing":
        finish_score()
        game_state = "victory"
        end_message_timer = END_MESSAGE_DURATION


# ============================================================
# TITLE SCREEN
# ============================================================

def draw_title_screen():
    # Branded arcade-style title screen using the new Green River artwork.
    screen.fill((12, 70, 32))

    if title_art is not None:
        # Fit artwork to the game window while preserving aspect ratio.
        scale = min(WIDTH / title_art.get_width(), HEIGHT / title_art.get_height())
        w = max(1, int(title_art.get_width() * scale))
        h = max(1, int(title_art.get_height() * scale))
        art = pygame.transform.smoothscale(title_art, (w, h))
        art_rect = art.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(art, art_rect)

        # Dark translucent panel improves readability of the interactive prompt.
        overlay = pygame.Surface((WIDTH, 105), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, HEIGHT - 105))

    else:
        pygame.draw.rect(
            screen, NAVY, (12, 12, WIDTH - 24, HEIGHT - 24),
            border_radius=18
        )

    # School branding remains visible even if the artwork cannot load.
    school = subtitle_font.render("GREEN RIVER HIGH SCHOOL", True, WHITE)
    screen.blit(school, (WIDTH // 2 - school.get_width() // 2, 18))

    # Animated wolf foreground.
    frame = (pygame.time.get_ticks() // 150) % 4
    wolf_sprite = make_wolf_sprite(RIGHT, frame)
    screen.blit(
        wolf_sprite,
        wolf_sprite.get_rect(center=(WIDTH // 2 - 145, HEIGHT - 55))
    )

    # Start button.
    button_rect = pygame.Rect(WIDTH // 2 - 170, HEIGHT - 88, 340, 52)
    pygame.draw.rect(screen, (20, 110, 35), button_rect, border_radius=12)
    pygame.draw.rect(screen, GREEN, button_rect, 3, border_radius=12)

    play_text = subtitle_font.render("▶  START WOLF-MAN", True, WHITE)
    screen.blit(
        play_text,
        (WIDTH // 2 - play_text.get_width() // 2, HEIGHT - 76)
    )

    controls = small_font.render(
        "ARROWS / WASD = STEER • TIGER CATCHES WOLF = LOSE LIFE • POWER = EAT TIGER",
        True,
        WHITE,
    )
    screen.blit(
        controls,
        (WIDTH // 2 - controls.get_width() // 2, HEIGHT - 32)
    )

    # Music status: the game supports the slot, but a licensed recording is required.
    music_status = small_font.render(
        "MUSIC: ON WISCONSIN • M = MUSIC ON/OFF",
        True,
        YELLOW,
    )
    screen.blit(
        music_status,
        (WIDTH // 2 - music_status.get_width() // 2, HEIGHT - 16)
    )


# ============================================================
# END SCREEN
# ============================================================

def draw_end_screen():
    """Display a clear, stable win/lose screen until the player chooses."""
    screen.fill(NAVY)

    won = game_state == "victory"

    # Main result message.
    result = "YOU WIN!" if won else "GAME OVER"
    result_color = GREEN if won else RED
    title = title_font.render(result, True, result_color)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 85)))

    # Explanation of what happened.
    if won:
        explanation = "ALL 10 TIGERS HAVE BEEN EATEN!"
    else:
        explanation = "THE TIGERS GOT YOU!"

    explanation_surf = subtitle_font.render(explanation, True, WHITE)
    screen.blit(explanation_surf, explanation_surf.get_rect(center=(WIDTH // 2, 150)))

    score_surf = font.render(f"FINAL SCORE: {score}", True, YELLOW)
    screen.blit(score_surf, score_surf.get_rect(center=(WIDTH // 2, 195)))

    best_surf = font.render(f"HIGH SCORE: {high_score}", True, LIGHT_BLUE)
    screen.blit(best_surf, best_surf.get_rect(center=(WIDTH // 2, 235)))

    if new_record:
        record_surf = subtitle_font.render("NEW HIGH SCORE!", True, GREEN)
        screen.blit(record_surf, record_surf.get_rect(center=(WIDTH // 2, 275)))

    # Keep the wolf visible as part of the result screen.
    frame = (pygame.time.get_ticks() // 150) % 4
    sprite = make_wolf_sprite(RIGHT, frame)
    screen.blit(sprite, sprite.get_rect(center=(WIDTH // 2, 350)))

    # The player cannot select anything during the 10-second display period.
    if end_message_timer > 0:
        seconds_left = max(1, math.ceil(end_message_timer))
        wait = subtitle_font.render("PLEASE WAIT...", True, GRAY)
        screen.blit(wait, wait.get_rect(center=(WIDTH // 2, 415)))

        countdown = font.render(
            f"{seconds_left} SECONDS",
            True,
            WHITE,
        )
        screen.blit(countdown, countdown.get_rect(center=(WIDTH // 2, 455)))

        instruction = small_font.render(
            "PLAY AGAIN OPTIONS WILL APPEAR WHEN THE TIMER REACHES ZERO",
            True,
            GRAY,
        )
        screen.blit(instruction, instruction.get_rect(center=(WIDTH // 2, 495)))
    else:
        # These are the only two choices after the 10-second display.
        question = subtitle_font.render("DO YOU WISH TO PLAY AGAIN?", True, WHITE)
        screen.blit(question, question.get_rect(center=(WIDTH // 2, 420)))

        play_again = font.render("SPACE BAR  =  PLAY AGAIN", True, GREEN)
        screen.blit(play_again, play_again.get_rect(center=(WIDTH // 2, 465)))

        exit_game = font.render("ENTER  =  EXIT GAME", True, LIGHT_BLUE)
        screen.blit(exit_game, exit_game.get_rect(center=(WIDTH // 2, 505)))


# ============================================================
# INPUT
# ============================================================

def start_from_user_action():
    """Start audio and begin a new game after browser user interaction."""
    global game_state

    init_audio()

    if game_state == "title":
        new_game()

    elif game_state in ("game_over", "victory"):
        new_game()


def handle_events():
    global game_state
    global sound_enabled

    running = True

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.KEYDOWN:

            # A keypress is also the browser audio-unlock gesture.
            init_audio()

            if event.key == pygame.K_ESCAPE:

                if game_state == "playing":
                    game_state = "title"
                else:
                    game_state = "title"

            elif event.key == pygame.K_m:

                sound_enabled = not sound_enabled

                if sound_enabled:
                    init_audio()

            elif game_state == "title":

                # Easy-start option: any normal key begins the game.
                if event.key not in (
                    pygame.K_m,
                    pygame.K_ESCAPE,
                ):
                    start_from_user_action()

            elif game_state in (
                "game_over",
                "victory",
            ):

                # The result screen remains locked for the full 10 seconds.
                if end_message_timer <= 0:
                    if event.key == pygame.K_SPACE:
                        start_from_user_action()
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        # Exit immediately.  On desktop this closes the Pygame
                        # window; in the browser/Pygbag build it stops the
                        # game loop cleanly (the browser tab itself cannot be
                        # closed by a web game).
                        return False

            elif game_state == "playing":

                if event.key in DIRECTIONS:
                    wolf.set_direction(DIRECTIONS[event.key])

        elif event.type == pygame.MOUSEBUTTONDOWN:

            # Mouse click is another browser audio-unlock gesture.
            init_audio()

            if game_state == "title":
                start_from_user_action()
            elif game_state in ("game_over", "victory") and end_message_timer <= 0:
                # Mouse is intentionally not used for the final choice;
                # SPACE plays again and ENTER exits.
                pass

    return running


# ============================================================
# ASYNC PYGBAG MAIN LOOP
# ============================================================


async def main():
    global end_message_timer

    running = True

    while running:

        running = handle_events()

        if game_state == "title":

            draw_title_screen()

        elif game_state == "playing":

            update_game()
            draw_maze()

            for ghost in ghosts:
                ghost.draw()

            wolf.draw()

            hunt_text = small_font.render(
                "WOLF HUNTING TIGERS • 10 TIGERS AT START • EAT THEM ALL TO WIN",
                True,
                GREEN,
            )
            screen.blit(
                hunt_text,
                (WIDTH // 2 - hunt_text.get_width() // 2, 8),
            )

            if power_mode:
                power_text = small_font.render(
                    "HOWL POWER!",
                    True,
                    CYAN,
                )

                screen.blit(
                    power_text,
                    (
                        WIDTH // 2
                        - power_text.get_width() // 2,
                        45,
                    ),
                )

        else:

            if end_message_timer > 0:
                end_message_timer = max(0.0, end_message_timer - (1.0 / FPS))

            draw_end_screen()

        # Update generated background music.
        update_music(
            pygame.time.get_ticks() / 1000.0
        )

        pygame.display.flip()

        clock.tick(FPS)

        # REQUIRED BY PYGBAG:
        # Yield to the browser every frame.
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
