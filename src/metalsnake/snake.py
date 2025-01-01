"""
snake.py

A complete implementation of a resizable Snake game with improved architecture and visuals.
Features include:
- Proper class-based architecture with dependency injection
- Enhanced resource management and caching
- Particle system with object pooling
- Type-safe implementations using Python type hints
- Improved state management and game flow
- Comprehensive logging and error handling
- Enhanced power-up system with distinct visuals and animations
- Project structure adaptation for development and PyInstaller bundling
"""

import pygame
import sys
import random
import math
import json
import os
import logging
from typing import Tuple, Set, List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum, auto

# Ensure appdirs is installed for user-specific directories (optional but recommended)
try:
    import appdirs
except ImportError:
    print("The 'appdirs' library is required for this game to run properly.")
    print("Please install it using 'pip install appdirs'")
    sys.exit(1)

##########################
# ENUMS AND CONFIG
##########################

class GameState(Enum):
    """Represents the different states the game can be in"""
    MENU = auto()
    PLAY = auto()
    GAME_OVER = auto()
    HIGHSCORES = auto()

class Direction(Enum):
    """Represents possible movement directions with helper methods"""
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    
    @property
    def opposite(self) -> 'Direction':
        """Returns the opposite direction, used for preventing 180-degree turns"""
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT
        }
        return opposites[self]

class PowerUpType(Enum):
    """Different types of power-ups available in the game"""
    SPEED_BOOST = auto()
    INVINCIBILITY = auto()
    SCORE_MULTIPLIER = auto()

@dataclass
class GameConfig:
    """
    Centralized configuration for game settings.
    Using dataclass for automatic initialization and cleaner syntax.
    """
    # Grid settings
    GRID_COLS: int = 30
    GRID_ROWS: int = 20
    
    # Game mechanics
    FPS: int = 60
    BASE_GAME_SPEED: int = 10  # Base speed to reset to
    GAME_SPEED: int = 10
    OBSTACLE_COUNT: int = 20
    OBSTACLE_BONUS: int = 2
    
    # Particle system
    PARTICLE_COUNT: int = 12
    PARTICLE_SPEED: float = 3.0
    PARTICLE_LIFETIME: int = 30
    
    # Scoring
    MAX_SCORES: int = 5
    
    # Power-up system
    POWERUP_TYPES: List[PowerUpType] = (
        PowerUpType.SPEED_BOOST,
        PowerUpType.INVINCIBILITY,
        PowerUpType.SCORE_MULTIPLIER,
    )
    POWERUP_SPAWN_INTERVAL: int = 500  # Frames between power-up spawns
    POWERUP_DURATION: int = 300  # Frames power-up effect lasts
    POWERUP_COUNT: int = 3  # Maximum number of active power-ups
    
    # Colors (as RGBA tuples)
    WHITE: Tuple[int, ...] = (255, 255, 255)
    BLACK: Tuple[int, ...] = (0, 0, 0)
    RED: Tuple[int, ...] = (200, 0, 0)
    GRAY: Tuple[int, ...] = (100, 100, 100)
    BLUE: Tuple[int, ...] = (0, 0, 200)
    GREEN: Tuple[int, ...] = (0, 200, 0)
    YELLOW: Tuple[int, ...] = (200, 200, 0)
    CYAN: Tuple[int, ...] = (0, 200, 200)
    MAGENTA: Tuple[int, ...] = (200, 0, 200)
    ORANGE: Tuple[int, ...] = (255, 165, 0)

##########################
# RESOURCE MANAGEMENT
##########################

class ResourceManager:
    def __init__(self, config: GameConfig):
        """Initialize the resource manager and load initial resources"""
        self.config = config
        self._background: Optional[pygame.Surface] = None
        self._font_cache: Dict[int, pygame.font.Font] = {}
        self.logger = logging.getLogger(__name__)

        # Determine base paths
        self.base_path = self.get_base_path()

        # Load and start background music
        music_path = self.resource_path(os.path.join("audio", "MidnightCarnage.mp3"))
        if not os.path.exists(music_path):
            self.logger.error(f"Background music file not found at {music_path}")
        try:
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(-1)  # -1 means loop indefinitely
            self.logger.info("Background music loaded and playing.")
        except Exception as e:
            self.logger.warning(f"Could not load 'MidnightCarnage.mp3': {e}")

    def get_base_path(self) -> str:
        """Determine the base path for resources"""
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            return sys._MEIPASS
        else:
            # Development path: project_root/
            # Assuming snake.py is in src/metalsnake/
            return os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))

    def get_background(self) -> Optional[pygame.Surface]:
        """Lazy load the background image when first requested"""
        if self._background is None:
            path = self.resource_path(os.path.join("images", "snake.png"))
            if not os.path.exists(path):
                self.logger.error(f"Background image not found at {path}")
                # Create a default background
                self._background = pygame.Surface((self.config.GRID_COLS * 20, self.config.GRID_ROWS * 20))
                self._background.fill(self.config.BLACK)
                return self._background
            try:
                self._background = pygame.image.load(path).convert()
                self.logger.info("Background image loaded successfully")
            except Exception as e:
                self.logger.warning(f"Could not load background: {e}")
                self._background = None
        return self._background

    def get_font(self, size: int) -> pygame.font.Font:
        """Get or create a font of the specified size"""
        if size not in self._font_cache:
            try:
                self._font_cache[size] = pygame.font.SysFont(None, size)
            except Exception as e:
                self.logger.error(f"Failed to load font size {size}: {e}")
                # Fallback to default font
                self._font_cache[size] = pygame.font.Font(None, size)
        return self._font_cache[size]

    def resource_path(self, relative_path: str) -> str:
        """Get absolute path to resource for both dev and PyInstaller modes"""
        return os.path.join(self.base_path, "resources", relative_path)

    def get_data_path(self, relative_path: str) -> str:
        """Get path for data files using appdirs for user-specific directories"""
        app_name = "MetalSnake"
        app_author = "YourName"  # Replace with your name or organization
        data_dir = appdirs.user_data_dir(app_name, app_author)
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, relative_path)

    def get_log_path(self, relative_path: str) -> str:
        """Get path for log files using appdirs for user-specific directories"""
        app_name = "MetalSnake"
        app_author = "YourName"  # Replace with your name or organization
        log_dir = appdirs.user_log_dir(app_name, app_author)
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, relative_path)

    def cleanup(self) -> None:
        """Release all loaded resources"""
        pygame.mixer.music.stop()
        self._background = None
        self._font_cache.clear()
        self.logger.info("Resources cleaned up")

##########################
# PARTICLE SYSTEM
##########################

class Particle:
    """
    Individual particle with physics-based movement.
    Represents a single particle in the particle effect system.
    """
    def __init__(self, x: float, y: float, config: GameConfig):
        self.config = config
        self.reset(x, y)
        
    def reset(self, x: float, y: float) -> None:
        """Reset particle to initial state with new position"""
        self.x = float(x)
        self.y = float(y)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(self.config.PARTICLE_SPEED * 0.5,
                             self.config.PARTICLE_SPEED)
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.life = self.config.PARTICLE_LIFETIME
        
    def update(self) -> None:
        """Update particle position and lifetime"""
        self.x += self.dx
        self.y += self.dy
        self.life -= 1
        
    def draw(self, surface: pygame.Surface) -> None:
        """Draw particle with size based on remaining lifetime"""
        radius = max(1, self.life // 6)
        color = (random.randint(100, 255),
                random.randint(200, 255), 0)
        pygame.draw.circle(surface, color,
                         (int(self.x), int(self.y)), radius)

class ParticleSystem:
    """
    Manages particle effects for visual feedback.
    Uses object pooling to reduce garbage collection.
    """
    def __init__(self, config: GameConfig):
        self.config = config
        self.particles: List[Particle] = []
        self.particle_pool: List[Particle] = []
        
    def emit(self, x: float, y: float, count: int) -> None:
        """Emit a burst of particles at the specified position"""
        for _ in range(count):
            if self.particle_pool:
                particle = self.particle_pool.pop()
                particle.reset(x, y)
            else:
                particle = Particle(x, y, self.config)
            self.particles.append(particle)
            
    def update_and_draw(self, surface: pygame.Surface) -> None:
        """Update particle positions and draw them"""
        dead_particles = []
        for particle in self.particles:
            particle.update()
            particle.draw(surface)
            if particle.life <= 0:
                dead_particles.append(particle)
                
        for dead in dead_particles:
            self.particles.remove(dead)
            self.particle_pool.append(dead)

##########################
# SCORE MANAGEMENT
##########################

class ScoreManager:
    """
    Handles score tracking and persistence.
    Manages high scores for different game modes.
    """
    def __init__(self, config: GameConfig, resource_manager: ResourceManager):
        self.config = config
        self.resource_manager = resource_manager
        self.highscores: Dict[str, List[Dict[str, Any]]] = {
            "classic": [],
            "obstacles": []
        }
        self.load_scores()
        
    def load_scores(self) -> None:
        """Load high scores from file"""
        highscores_path = self.resource_manager.get_data_path("highscores.json")
        if os.path.exists(highscores_path):
            try:
                with open(highscores_path, 'r') as f:
                    self.highscores = json.load(f)
                logging.info("High scores loaded successfully.")
            except Exception as e:
                logging.error(f"Error loading highscores: {e}")
        else:
            # Initialize empty highscores file
            self.save_scores()
    
    def save_scores(self) -> None:
        """Save high scores to file"""
        highscores_path = self.resource_manager.get_data_path("highscores.json")
        try:
            with open(highscores_path, 'w') as f:
                json.dump(self.highscores, f, indent=4)
            logging.info("High scores saved successfully.")
        except Exception as e:
            logging.error(f"Error saving highscores: {e}")
            
    def add_score(self, name: str, score: int, mode: str) -> None:
        """Add new score and maintain sorted order"""
        if mode not in self.highscores:
            self.highscores[mode] = []
        self.highscores[mode].append({"name": name, "score": score})
        self.highscores[mode].sort(key=lambda x: x["score"], reverse=True)
        self.highscores[mode] = self.highscores[mode][:self.config.MAX_SCORES]
        self.save_scores()

##########################
# POWER-UP SYSTEM
##########################

class PowerUp:
    """
    Represents a power-up entity in the game.
    Handles power-up type, position, and visual representation.
    """
    def __init__(self, x: int, y: int, powerup_type: PowerUpType, config: GameConfig):
        self.x = x
        self.y = y
        self.type = powerup_type
        self.config = config
        self.active = False
        self.duration = self.config.POWERUP_DURATION
        self.remaining_duration = self.duration  # New attribute
    
    def position(self) -> Tuple[int, int]:
        """Returns the current position of the power-up"""
        return (self.x, self.y)
    
    def apply(self, game: 'Game') -> None:
        """Apply the power-up effect to the game"""
        if self.type == PowerUpType.SPEED_BOOST:
            game.config.GAME_SPEED += 5  # Increase game speed
            game.active_powerups[self.type] = self.duration
            logging.info("Speed Boost activated!")
        elif self.type == PowerUpType.INVINCIBILITY:
            game.snake.invincible = True
            game.active_powerups[self.type] = self.duration
            logging.info("Invincibility activated!")
        elif self.type == PowerUpType.SCORE_MULTIPLIER:
            game.score_multiplier += 1  # Increment multiplier
            game.active_powerups[self.type] = self.duration
            logging.info(f"Score Multiplier activated! Current multiplier: x{game.score_multiplier}")
    
    def expire(self, game: 'Game') -> None:
        """Expire the power-up effect from the game"""
        if self.type == PowerUpType.SPEED_BOOST:
            game.config.GAME_SPEED -= 5  # Revert game speed
            logging.info("Speed Boost expired!")
        elif self.type == PowerUpType.INVINCIBILITY:
            game.snake.invincible = False
            logging.info("Invincibility expired!")
        elif self.type == PowerUpType.SCORE_MULTIPLIER:
            game.score_multiplier = max(1, game.score_multiplier - 1)  # Decrement multiplier but not below 1
            logging.info(f"Score Multiplier expired! Current multiplier: x{game.score_multiplier}")
    
    def update_timer(self) -> None:
        """Update the remaining duration of the power-up"""
        if self.remaining_duration > 0:
            self.remaining_duration -= 1

class PowerUpManager:
    """
    Manages power-up spawning, active power-ups, and their effects.
    """
    def __init__(self, config: GameConfig):
        self.config = config
        self.active_powerups: Dict[PowerUpType, int] = {}
        self.powerups: List[PowerUp] = []
        self.spawn_timer = 0
    
    def spawn_powerup(self, game: 'Game') -> None:
        """Spawn a new power-up at a random position"""
        if len(self.powerups) >= self.config.POWERUP_COUNT:
            return  # Maximum active power-ups reached

        x, y = game.get_random_position(include_powerups=True)
        powerup_type = random.choice(self.config.POWERUP_TYPES)
        powerup = PowerUp(x, y, powerup_type, self.config)
        self.powerups.append(powerup)
        logging.info(f"Spawned power-up: {powerup.type.name} at ({x}, {y})")
    
    def update(self, game: 'Game') -> None:
        """Update power-ups, spawn new ones, and handle expiration"""
        self.spawn_timer += 1
        if self.spawn_timer >= self.config.POWERUP_SPAWN_INTERVAL:
            self.spawn_powerup(game)
            self.spawn_timer = 0

        # Update power-up timers and expire if necessary
        for powerup in self.powerups[:]:
            powerup.update_timer()
            if powerup.remaining_duration <= 0:
                powerup.expire(game)
                self.powerups.remove(powerup)
                logging.info(f"Power-up {powerup.type.name} expired.")
        
        # Check for power-up collection
        head = game.snake.head_position()
        for powerup in self.powerups[:]:
            if head == (powerup.x, powerup.y):
                powerup.apply(game)
                self.powerups.remove(powerup)
                game.score += 5 * game.score_multiplier  # Bonus for collecting power-up
                game.particles.emit(
                    powerup.x * game.cell_size + game.cell_size // 2,
                    powerup.y * game.cell_size + game.cell_size // 2,
                    game.config.PARTICLE_COUNT
                )
                logging.info(f"Power-up {powerup.type.name} collected by player.")
    
    def draw(self, surface: pygame.Surface, cell_size: int, frame_count: int) -> None:
        """Draw all active power-ups with enhanced visuals and animations"""
        for powerup in self.powerups:
            center_x = powerup.x * cell_size + cell_size // 2
            center_y = powerup.y * cell_size + cell_size // 2
            base_radius = max(cell_size // 2 - 4, 2)
            
            # Define colors and shapes based on power-up type
            if powerup.type == PowerUpType.SPEED_BOOST:
                color = self.config.YELLOW
                shape = "triangle"
            elif powerup.type == PowerUpType.INVINCIBILITY:
                color = self.config.CYAN
                shape = "shield"  # Changed to 'shield' for clarity
            elif powerup.type == PowerUpType.SCORE_MULTIPLIER:
                color = self.config.MAGENTA
                shape = "star"
            else:
                color = self.config.WHITE
                shape = "circle"

            # Calculate pulsating scale
            pulse = (math.sin(frame_count * 0.05) + 1) / 2  # Pulsate between 0 and 1
            scale = 0.8 + 0.4 * pulse  # Scale between 0.8 and 1.2
            pulsate_radius = int(base_radius * scale)

            # Calculate bobbing offset
            bob = math.sin(frame_count * 0.02) * 2  # Bob up and down by 2 pixels

            # Glow effect
            glow_radius = pulsate_radius + 6
            glow_color = (*color[:3], 100)  # Semi-transparent glow
            pygame.draw.circle(surface, glow_color, (center_x, int(center_y + bob)), glow_radius)

            # Draw distinct shape with outline
            if shape == "circle":
                pygame.draw.circle(surface, color, (center_x, int(center_y + bob)), pulsate_radius)
                pygame.draw.circle(surface, self.config.WHITE, (center_x, int(center_y + bob)), pulsate_radius, 2)
            elif shape == "square":
                rect = pygame.Rect(
                    center_x - pulsate_radius,
                    int(center_y + bob) - pulsate_radius,
                    pulsate_radius * 2,
                    pulsate_radius * 2
                )
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, self.config.WHITE, rect, 2)
            elif shape == "triangle":
                points = [
                    (center_x, int(center_y + bob) - pulsate_radius),
                    (center_x - pulsate_radius, int(center_y + bob) + pulsate_radius),
                    (center_x + pulsate_radius, int(center_y + bob) + pulsate_radius)
                ]
                pygame.draw.polygon(surface, color, points)
                pygame.draw.polygon(surface, self.config.WHITE, points, 2)
            elif shape == "shield":
                # Draw a simple shield shape
                shield_points = [
                    (center_x, int(center_y + bob) - pulsate_radius),
                    (center_x - pulsate_radius, int(center_y + bob)),
                    (center_x, int(center_y + bob) + pulsate_radius),
                    (center_x + pulsate_radius, int(center_y + bob))
                ]
                pygame.draw.polygon(surface, color, shield_points)
                pygame.draw.polygon(surface, self.config.WHITE, shield_points, 2)
            elif shape == "star":
                # Draw a 5-pointed star
                points = []
                for i in range(10):
                    angle = i * (math.pi / 5) - math.pi / 2
                    r = pulsate_radius if i % 2 == 0 else pulsate_radius // 2
                    x = center_x + r * math.cos(angle)
                    y = int(center_y + bob) + r * math.sin(angle)
                    points.append((x, y))
                pygame.draw.polygon(surface, color, points)
                pygame.draw.polygon(surface, self.config.WHITE, points, 2)

    ##########################
    # GAME ENTITIES
    ##########################

class Snake:
    """
    Represents the snake entity with its movement logic and collision detection.
    Handles snake movement, growth, and collision checking.
    Implements conditional wrap-around movement based on invincibility.
    """
    def __init__(self, config: GameConfig):
        self.config = config
        self.body: List[Tuple[int, int]] = [(5, 5), (4, 5), (3, 5)]
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.invincible = False  # Attribute for invincibility

    def set_direction(self, new_direction: Direction) -> None:
        """Update direction ensuring no 180-degree turns"""
        if new_direction != self.direction.opposite:
            self.next_direction = new_direction
                
    def move(self, food_pos: Tuple[int, int],
             obstacles: Set[Tuple[int, int]]) -> bool:
        """
        Move snake and check for collisions.
        Returns False if move results in death.
        Implements conditional wrap-around based on invincibility.
        """
        self.direction = self.next_direction
        head_x, head_y = self.body[0]
        
        # Calculate new head position based on direction
        if self.direction == Direction.UP:
            head_y -= 1
        elif self.direction == Direction.DOWN:
            head_y += 1
        elif self.direction == Direction.LEFT:
            head_x -= 1
        elif self.direction == Direction.RIGHT:
            head_x += 1
        
        # Handle wall collision
        if not self.invincible:
            # If out of bounds, die
            if head_x < 0 or head_x >= self.config.GRID_COLS or head_y < 0 or head_y >= self.config.GRID_ROWS:
                return False
        else:
            # If invincible, wrap around
            head_x %= self.config.GRID_COLS
            head_y %= self.config.GRID_ROWS
        
        new_head = (head_x, head_y)
        self.body.insert(0, new_head)
        
        # Check collision with self or obstacles
        if new_head in self.body[1:] or new_head in obstacles:
            if not self.invincible:
                return False
                
        # Remove tail if no food eaten
        if new_head != food_pos:
            self.body.pop()
            
        return True

    def head_position(self) -> Tuple[int, int]:
        """Returns the current head position of the snake"""
        return self.body[0]
    
    def draw(self, surface: pygame.Surface, cell_size: int,
             frame_count: int) -> None:
        """Draw snake with animated effects"""
        for i, (sx, sy) in enumerate(self.body):
            center_x = sx * cell_size + cell_size // 2
            center_y = sy * cell_size + cell_size // 2

            # Calculate wave effect
            phase = (frame_count * 0.1) + i * 0.3
            wave = 2 * math.sin(phase)

            if i == 0:  # Head
                base_r = cell_size // 2
                radius = max(base_r + int(wave), 2)
                
                # Add glow effect to head
                glow_color = (0, 255, 0, 100) if not self.invincible else (0, 255, 255, 150)
                pygame.draw.circle(surface, glow_color,
                                 (center_x, center_y), radius + 4)
                pygame.draw.circle(surface, self.config.BLACK,
                                 (center_x, center_y), radius + 2)
                head_color = self.config.GREEN if not self.invincible else self.config.CYAN
                pygame.draw.circle(surface, head_color,
                                 (center_x, center_y), radius)
                
                # Draw eyes with glow
                eye_offset = radius // 2
                eye_pos1 = (center_x - eye_offset // 2,
                           center_y - eye_offset)
                eye_pos2 = (center_x + eye_offset // 2,
                           center_y - eye_offset)
                eye_r = eye_offset // 3
                
                # Eye glow
                pygame.draw.circle(surface, (*self.config.WHITE[:3], 128),
                                 eye_pos1, eye_r + 2)
                pygame.draw.circle(surface, (*self.config.WHITE[:3], 128),
                                 eye_pos2, eye_r + 2)
                
                # Eyes
                pygame.draw.circle(surface, self.config.WHITE,
                                 eye_pos1, eye_r)
                pygame.draw.circle(surface, self.config.WHITE,
                                 eye_pos2, eye_r)
            else:  # Body
                base_r = max(cell_size // 2 - 2, 2)
                radius = max(base_r + int(wave), 2)
                pygame.draw.circle(surface, self.config.BLACK,
                                 (center_x, center_y), radius + 2)
                seg_color = self.config.GREEN if not self.invincible else self.config.CYAN
                pygame.draw.circle(surface, seg_color,
                                 (center_x, center_y), radius)

##########################
# RENDERING
##########################

class Renderer:
    """
    Handles all game rendering operations.
    Centralizes drawing logic and screen management.
    """
    def __init__(self, config: GameConfig, resources: ResourceManager):
        self.config = config
        self.resources = resources
        
    def draw_background(self, surface: pygame.Surface,
                       width: int, height: int) -> None:
        """Draw background with overlay"""
        background = self.resources.get_background()
        if background:
            bg_scaled = pygame.transform.scale(background, (width, height))
            surface.blit(bg_scaled, (0, 0))
        else:
            surface.fill(self.config.BLACK)
            
    def draw_overlay(self, surface: pygame.Surface,
                    width: int, height: int, alpha: int = 80) -> None:
        """Draw semi-transparent overlay"""
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        surface.blit(overlay, (0, 0))
        
    def draw_text(self, surface: pygame.Surface, text: str,
                  x: int, y: int, size: int = 24,
                  color: Tuple[int, ...] = None,
                  center: bool = False,
                  shadow_color: Tuple[int, ...] = None,
                  glow: bool = False) -> None:
        """Draw text with optional effects"""
        if color is None:
            color = self.config.WHITE
        if shadow_color is None:
            shadow_color = self.config.BLACK
            
        font = self.resources.get_font(size)
        
        # Create shadow effect
        shadow_offsets = [(2, 2), (2, -2), (-2, 2), (-2, -2)] if glow else [(2, 2)]

        # Handle glowing text effect
        if glow:
            glow_surface = pygame.Surface((size * len(text), size), pygame.SRCALPHA)
            glow_color = (*color[:3], 128)
            rendered_glow = font.render(text, True, glow_color)
            for offset in range(3, 0, -1):
                glow_rect = rendered_glow.get_rect()
                if center:
                    glow_rect.center = (x + offset, y + offset)
                else:
                    glow_rect.topleft = (x + offset, y + offset)
                glow_surface.blit(rendered_glow, glow_rect)
            # Position glow_surface correctly
            if center:
                surface.blit(glow_surface, (x - size * len(text) // 2, y - size // 2))
            else:
                surface.blit(glow_surface, (x, y))
        
        # Draw shadows
        rendered_shadow = font.render(text, True, shadow_color)
        for offset_x, offset_y in shadow_offsets:
            shadow_rect = rendered_shadow.get_rect()
            if center:
                shadow_rect.center = (x + offset_x, y + offset_y)
            else:
                shadow_rect.topleft = (x + offset_x, y + offset_y)
            surface.blit(rendered_shadow, shadow_rect)

        # Draw main text
        rendered_text = font.render(text, True, color)
        text_rect = rendered_text.get_rect()
        if center:
            text_rect.center = (x, y)
        else:
            text_rect.topleft = (x, y)
        surface.blit(rendered_text, text_rect)
    
    def draw_food(self, surface: pygame.Surface, x: int, y: int,
                  cell_size: int, frame_count: int) -> None:
        """Draw food with pulsing glow effect"""
        center_x = x * cell_size + cell_size // 2
        center_y = y * cell_size + cell_size // 2
        base_radius = max(cell_size // 2 - 2, 2)

        # Create pulsing effect
        pulse = abs(math.sin(frame_count * 0.1)) * 0.3 + 0.7

        # Draw outer glow layers
        for radius in range(base_radius + 4, base_radius - 1, -1):
            alpha = int(100 * pulse * (radius - base_radius + 4) / 4)
            glow_color = (255, 0, 0, alpha)
            glow_surface = pygame.Surface((radius * 2 + 2, radius * 2 + 2),
                                        pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, glow_color,
                             (radius + 1, radius + 1), radius)
            surface.blit(glow_surface,
                        (center_x - radius - 1, center_y - radius - 1))

        # Draw main food body
        core_color = (200, 0, 0)
        pygame.draw.circle(surface, core_color,
                         (center_x, center_y), base_radius)

        # Add highlight for depth
        highlight_pos = (center_x - base_radius // 3,
                        center_y - base_radius // 3)
        highlight_radius = max(base_radius // 3, 1)
        pygame.draw.circle(surface, (255, 128, 128),
                         highlight_pos, highlight_radius)

    def draw_obstacles(self, surface: pygame.Surface,
                      obstacles: Set[Tuple[int, int]],
                      cell_size: int, frame_count: int) -> None:
        """Draw obstacles with magical appearance"""
        for ox, oy in obstacles:
            cx = ox * cell_size + cell_size // 2
            cy = oy * cell_size + cell_size // 2

            # Animate obstacles
            pulse = abs(math.sin(frame_count * 0.1)) * 0.3 + 0.7
            bob = math.sin(frame_count * 0.08) * cell_size * 0.15

            # Create color pulsing
            color_pulse = abs(math.sin(frame_count * 0.05))
            base_blue = int(200 + (55 * color_pulse))
            base_red = int(100 + (40 * color_pulse))
            base_color = (base_red, 0, base_blue)

            # Calculate size with pulse effect
            r = max(cell_size // 2 - 2, 2)
            pulse_radius = int(r * pulse)

            # Draw glow layers
            for offset in range(4, 0, -1):
                glow_radius = pulse_radius + offset
                glow_surface = pygame.Surface((glow_radius * 2 + 2,
                                             glow_radius * 2 + 2),
                                        pygame.SRCALPHA)
                alpha = int(128 * (5 - offset) / 4)
                glow_color = (60, 130, 255, alpha)

                pygame.draw.circle(glow_surface, glow_color,
                                 (glow_radius + 1, glow_radius + 1),
                                 glow_radius)
                surface.blit(glow_surface,
                            (cx - glow_radius - 1,
                             cy - glow_radius - 1 + bob))

            # Draw main obstacle
            pygame.draw.circle(surface, base_color,
                             (cx, cy + bob), pulse_radius)

            # Add highlight
            highlight_color = (130, 200, 255)
            highlight_pos = (cx - pulse_radius // 3,
                           cy - pulse_radius // 3 + bob)
            highlight_radius = max(pulse_radius // 3, 1)
            pygame.draw.circle(surface, highlight_color,
                             highlight_pos, highlight_radius)
    
    def draw_powerups(self, surface: pygame.Surface, powerup_manager: 'PowerUpManager',
                     cell_size: int, frame_count: int) -> None:
        """Draw all active power-ups with enhanced visuals and animations"""
        for powerup in powerup_manager.powerups:
            center_x = powerup.x * cell_size + cell_size // 2
            center_y = powerup.y * cell_size + cell_size // 2
            base_radius = max(cell_size // 2 - 4, 2)
            
            # Define colors and shapes based on power-up type
            if powerup.type == PowerUpType.SPEED_BOOST:
                color = self.config.YELLOW
                shape = "triangle"
            elif powerup.type == PowerUpType.INVINCIBILITY:
                color = self.config.CYAN
                shape = "shield"  # Changed to 'shield' for clarity
            elif powerup.type == PowerUpType.SCORE_MULTIPLIER:
                color = self.config.MAGENTA
                shape = "star"
            else:
                color = self.config.WHITE
                shape = "circle"

            # Calculate pulsating scale
            pulse = (math.sin(frame_count * 0.05) + 1) / 2  # Pulsate between 0 and 1
            scale = 0.8 + 0.4 * pulse  # Scale between 0.8 and 1.2
            pulsate_radius = int(base_radius * scale)

            # Calculate bobbing offset
            bob = math.sin(frame_count * 0.02) * 2  # Bob up and down by 2 pixels

            # Glow effect
            glow_radius = pulsate_radius + 6
            glow_color = (*color[:3], 100)  # Semi-transparent glow
            pygame.draw.circle(surface, glow_color, (center_x, int(center_y + bob)), glow_radius)

            # Draw distinct shape with outline
            if shape == "circle":
                pygame.draw.circle(surface, color, (center_x, int(center_y + bob)), pulsate_radius)
                pygame.draw.circle(surface, self.config.WHITE, (center_x, int(center_y + bob)), pulsate_radius, 2)
            elif shape == "square":
                rect = pygame.Rect(
                    center_x - pulsate_radius,
                    int(center_y + bob) - pulsate_radius,
                    pulsate_radius * 2,
                    pulsate_radius * 2
                )
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, self.config.WHITE, rect, 2)
            elif shape == "triangle":
                points = [
                    (center_x, int(center_y + bob) - pulsate_radius),
                    (center_x - pulsate_radius, int(center_y + bob) + pulsate_radius),
                    (center_x + pulsate_radius, int(center_y + bob) + pulsate_radius)
                ]
                pygame.draw.polygon(surface, color, points)
                pygame.draw.polygon(surface, self.config.WHITE, points, 2)
            elif shape == "shield":
                # Draw a simple shield shape
                shield_points = [
                    (center_x, int(center_y + bob) - pulsate_radius),
                    (center_x - pulsate_radius, int(center_y + bob)),
                    (center_x, int(center_y + bob) + pulsate_radius),
                    (center_x + pulsate_radius, int(center_y + bob))
                ]
                pygame.draw.polygon(surface, color, shield_points)
                pygame.draw.polygon(surface, self.config.WHITE, shield_points, 2)
            elif shape == "star":
                # Draw a 5-pointed star
                points = []
                for i in range(10):
                    angle = i * (math.pi / 5) - math.pi / 2
                    r = pulsate_radius if i % 2 == 0 else pulsate_radius // 2
                    x = center_x + r * math.cos(angle)
                    y = int(center_y + bob) + r * math.sin(angle)
                    points.append((x, y))
                pygame.draw.polygon(surface, color, points)
                pygame.draw.polygon(surface, self.config.WHITE, points, 2)

    def draw_active_powerups(self, surface: pygame.Surface, powerup_manager: 'PowerUpManager',
                            score_multiplier: int, cell_size: int, frame_count: int, w: int, h: int) -> None:
        """Draw active power-ups with timers"""
        y_offset = 10  # Starting Y position
        for powerup_type, remaining in powerup_manager.active_powerups.items():
            # Define icon and label based on power-up type
            if powerup_type == PowerUpType.SPEED_BOOST:
                label = "Speed Boost"
                color = self.config.YELLOW
            elif powerup_type == PowerUpType.INVINCIBILITY:
                label = "Invincibility"
                color = self.config.CYAN
            elif powerup_type == PowerUpType.SCORE_MULTIPLIER:
                label = f"Score x{score_multiplier}"
                color = self.config.MAGENTA
            else:
                label = "Unknown"
                color = self.config.WHITE
            
            # Draw the power-up icon
            icon_radius = 10
            pygame.draw.circle(surface, color, (10 + icon_radius, y_offset + icon_radius), icon_radius)
            pygame.draw.circle(surface, self.config.WHITE, (10 + icon_radius, y_offset + icon_radius), icon_radius, 2)
            
            # Draw the label with remaining time
            time_seconds = remaining // self.config.FPS  # Convert frames to seconds
            time_label = f"{label} ({time_seconds}s)"
            # Flashing effect when less than 5 seconds
            if time_seconds <= 5:
                if frame_count % 30 < 15:
                    display_color = self.config.RED
                else:
                    display_color = color
            else:
                display_color = color
            self.draw_text(surface, time_label, 30, y_offset, size=20, color=display_color, center=False)
            
            y_offset += 30  # Increment Y position for the next power-up

##########################
# MAIN GAME
##########################

class Game:
    def __init__(self):
        """Initialize the game and all its components"""
        # Initialize Pygame modules
        pygame.init()
        pygame.mixer.init()

        # Initialize static player name for game over screen
        Game.player_name = ""  # Initialize as a class variable
        
        # Initialize configurations and managers
        self.config = GameConfig()
        self.resources = ResourceManager(self.config)
        self.score_manager = ScoreManager(self.config, self.resources)
        self.particles = ParticleSystem(self.config)
        self.renderer = Renderer(self.config, self.resources)
        self.powerup_manager = PowerUpManager(self.config)

        # Set up logging after ResourceManager to use correct log path
        log_path = self.resources.get_log_path("snake_game.log")
        logging.basicConfig(
            filename=log_path,
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.info("----- Starting Snake Game -----")

        # Initialize Pygame window
        self.screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
        pygame.display.set_caption("Metal Snake - Reign of the Digital Serpent")

        self.clock = pygame.time.Clock()
        self.state = GameState.MENU
        self.frame_count = 0
        self.obstacles_enabled = False
        
        # Initialize game-specific attributes
        self.snake = None
        self.score = 0
        self.game_tick = 0
        self.food_pos = None
        self.obstacles = set()
        self.score_multiplier = 1  # For score multiplier power-up
        self.active_powerups: Dict[PowerUpType, int] = {}
        self.cell_size = 0  # Will be set in run()

        self.reset_game()

    def reset_game(self) -> None:
        """Initialize or reset the game state"""
        self.snake = Snake(self.config)
        self.score = 0
        self.game_tick = 0
        self.food_pos = self.get_random_position()
        self.obstacles = set()
        if self.obstacles_enabled:
            self.obstacles = self.generate_obstacles()
        self.particles.particles.clear()
        self.particles.particle_pool.clear()
        self.powerup_manager.powerups.clear()
        self.powerup_manager.active_powerups.clear()
        self.score_multiplier = 1
        self.config.GAME_SPEED = self.config.BASE_GAME_SPEED  # Reset game speed
        self.snake.invincible = False  # Reset invincibility
        logging.info("Game has been reset.")

    def get_random_position(self, include_powerups: bool = False) -> Tuple[int, int]:
        """Get random grid position avoiding snake, obstacles, and existing power-ups"""
        while True:
            x = random.randint(0, self.config.GRID_COLS - 1)
            y = random.randint(0, self.config.GRID_ROWS - 1)
            pos = (x, y)
            if (pos not in self.snake.body and
                pos not in self.obstacles and
                (not include_powerups or pos not in [pu.position() for pu in self.powerup_manager.powerups])):
                return pos

    def generate_obstacles(self) -> Set[Tuple[int, int]]:
        """Generate random obstacle positions"""
        obstacles = set()
        for _ in range(self.config.OBSTACLE_COUNT):
            pos = self.get_random_position()
            obstacles.add(pos)
        logging.info(f"Generated {len(obstacles)} obstacles.")
        return obstacles

    def run(self) -> None:
        """Main game loop with state machine architecture"""
        while True:
            self.clock.tick(self.config.FPS)
            self.frame_count += 1

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.cleanup()
                    return
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode(
                        (event.w, event.h),
                        pygame.RESIZABLE
                    )

            # State machine update
            if self.state == GameState.MENU:
                self.update_menu(events)
            elif self.state == GameState.PLAY:
                self.update_game(events)
            elif self.state == GameState.GAME_OVER:
                self.update_game_over(events)
            elif self.state == GameState.HIGHSCORES:
                self.update_highscores(events)

            pygame.display.flip()

    def update_menu(self, events: List[pygame.event.Event]) -> None:
        """Handle menu state updates and rendering"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.state = GameState.PLAY
                    self.reset_game()
                elif event.key == pygame.K_h:
                    self.state = GameState.HIGHSCORES
                elif event.key == pygame.K_o:
                    self.obstacles_enabled = not self.obstacles_enabled
                    logging.info(f"Obstacles toggled to {'ON' if self.obstacles_enabled else 'OFF'}.")
                elif event.key == pygame.K_ESCAPE:
                    self.cleanup()
                    sys.exit()

        # Draw menu
        w, h = self.screen.get_size()
        self.renderer.draw_background(self.screen, w, h)
        self.renderer.draw_overlay(self.screen, w, h)

        self.renderer.draw_text(self.screen, "METAL SNAKE",
                              w//2, h//2 - 70, size=48,
                              center=True, glow=True)
        self.renderer.draw_text(self.screen, "[P] Play Game",
                              w//2, h//2 - 10, size=30, center=True)
        self.renderer.draw_text(self.screen, "[H] Highscores",
                              w//2, h//2 + 30, size=30, center=True)
        self.renderer.draw_text(self.screen,
                              f"[O] Obstacles: {'ON' if self.obstacles_enabled else 'OFF'}",
                              w//2, h//2 + 70, size=30, center=True)
        self.renderer.draw_text(self.screen, "[ESC] Quit",
                              w//2, h//2 + 110, size=30, center=True)

    def update_game(self, events: List[pygame.event.Event]) -> None:
        """Handle game state updates and collisions"""
        w, h = self.screen.get_size()
        self.cell_size = min(w // self.config.GRID_COLS, h // self.config.GRID_ROWS)

        # Handle input
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.snake.set_direction(Direction.UP)
                elif event.key == pygame.K_DOWN:
                    self.snake.set_direction(Direction.DOWN)
                elif event.key == pygame.K_LEFT:
                    self.snake.set_direction(Direction.LEFT)
                elif event.key == pygame.K_RIGHT:
                    self.snake.set_direction(Direction.RIGHT)
                elif event.key == pygame.K_ESCAPE:
                    self.state = GameState.MENU

        # Update game logic at fixed rate
        should_update = self.frame_count % (self.config.FPS // self.config.GAME_SPEED) == 0
        if should_update:
            self.game_tick += 1

            # Move snake and check collisions
            if not self.snake.move(self.food_pos, self.obstacles):
                self.TEMP_SCORE = self.score
                self.TEMP_MODE = "obstacles" if self.obstacles_enabled else "classic"
                self.state = GameState.GAME_OVER
                logging.info(f"Game Over! Score: {self.TEMP_SCORE}, Mode: {self.TEMP_MODE}")
                return

            # Check food collection
            head = self.snake.body[0]
            if head == self.food_pos:
                bonus = (1 + self.config.OBSTACLE_BONUS) if self.obstacles_enabled else 1
                self.score += bonus * self.score_multiplier
                px = head[0] * self.cell_size + self.cell_size//2
                py = head[1] * self.cell_size + self.cell_size//2
                self.particles.emit(px, py, self.config.PARTICLE_COUNT)
                self.food_pos = self.get_random_position()
                logging.info(f"Food collected! New score: {self.score}")

        # Update power-ups
        self.powerup_manager.update(self)

        # Draw game state
        self.renderer.draw_background(self.screen, w, h)
        self.renderer.draw_overlay(self.screen, w, h, alpha=50)
        self.renderer.draw_obstacles(self.screen, self.obstacles, self.cell_size, self.frame_count)
        self.renderer.draw_food(self.screen, self.food_pos[0], self.food_pos[1],
                              self.cell_size, self.frame_count)
        self.renderer.draw_powerups(self.screen, self.powerup_manager, self.cell_size, self.frame_count)
        self.snake.draw(self.screen, self.cell_size, self.frame_count)
        self.particles.update_and_draw(self.screen)
        # Pass score_multiplier to the renderer
        self.renderer.draw_active_powerups(self.screen, self.powerup_manager, self.score_multiplier, self.cell_size, self.frame_count, w, h)
        self.renderer.draw_text(self.screen, f"Score: {self.score}", 10, 10, size=24)
        self.renderer.draw_text(self.screen, f"Multiplier: x{self.score_multiplier}", 10, 40, size=24)

    def update_game_over(self, events: List[pygame.event.Event]) -> None:
        """Handle game over state updates with name entry"""
        w, h = self.screen.get_size()
        
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    final_name = Game.player_name.strip() or "Player"
                    self.score_manager.add_score(final_name, self.TEMP_SCORE, self.TEMP_MODE)
                    logging.info(f"High score added: {final_name} - {self.TEMP_SCORE} in {self.TEMP_MODE} mode.")
                    Game.player_name = ""
                    self.state = GameState.MENU
                elif event.key == pygame.K_h:
                    final_name = Game.player_name.strip() or "Player"
                    self.score_manager.add_score(final_name, self.TEMP_SCORE, self.TEMP_MODE)
                    logging.info(f"High score added: {final_name} - {self.TEMP_SCORE} in {self.TEMP_MODE} mode.")
                    Game.player_name = ""
                    self.state = GameState.HIGHSCORES
                elif event.key == pygame.K_ESCAPE:
                    Game.player_name = ""
                    self.state = GameState.MENU
                elif event.key == pygame.K_BACKSPACE:
                    Game.player_name = Game.player_name[:-1]
                else:
                    if len(Game.player_name) < 15 and event.unicode.isprintable():
                        Game.player_name += event.unicode

        # Draw game over screen
        self.renderer.draw_background(self.screen, w, h)
        self.renderer.draw_overlay(self.screen, w, h, alpha=80)

        self.renderer.draw_text(self.screen, "GAME OVER!", 
                              w//2, h//2 - 80, size=40, 
                              color=self.config.RED, center=True)
        self.renderer.draw_text(self.screen, f"Score: {self.TEMP_SCORE}", 
                              w//2, h//2 - 40, size=30, 
                              color=self.config.WHITE, center=True)
        self.renderer.draw_text(self.screen, "Enter your name:", 
                              w//2, h//2, size=24, 
                              color=self.config.WHITE, center=True)
        self.renderer.draw_text(self.screen, Game.player_name, 
                              w//2, h//2 + 30, size=24, 
                              color=self.config.BLUE, center=True)
        self.renderer.draw_text(self.screen, "[ENTER] Submit | [H] Highscores | [ESC] Menu",
                              w//2, h//2 + 70, size=20, 
                              color=self.config.WHITE, center=True)

    def update_highscores(self, events: List[pygame.event.Event]) -> None:
        """Handle highscores state updates and rendering"""
        w, h = self.screen.get_size()

        # Handle input
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = GameState.MENU
                    return

        # Draw background and overlay
        self.renderer.draw_background(self.screen, w, h)
        self.renderer.draw_overlay(self.screen, w, h)

        # Draw "HIGH SCORES" title
        self.renderer.draw_text(self.screen, "HIGH SCORES",
                              w//2, 40, size=40,
                              color=self.config.BLUE,
                              center=True, glow=True)

        # Get scores for both modes
        classic_scores = self.score_manager.highscores.get("classic", [])
        obstacle_scores = self.score_manager.highscores.get("obstacles", [])

        # Draw Classic Mode scores
        y_offset = 100
        self.renderer.draw_text(self.screen, "Classic Mode:",
                              w//2, y_offset, size=28, center=True)
        y_offset += 40
        
        for i, entry in enumerate(classic_scores):
            score_text = f"{i+1}. {entry['name']} - {entry['score']}"
            self.renderer.draw_text(self.screen, score_text,
                                  w//2, y_offset, size=24, center=True)
            y_offset += 30

        # Draw Obstacle Mode scores
        y_offset += 20  # Reduced extra space to prevent overlap
        self.renderer.draw_text(self.screen, "Obstacle Mode:",
                              w//2, y_offset, size=28, center=True)
        y_offset += 40
        
        for i, entry in enumerate(obstacle_scores):
            score_text = f"{i+1}. {entry['name']} - {entry['score']}"
            self.renderer.draw_text(self.screen, score_text,
                                  w//2, y_offset, size=24, center=True)
            y_offset += 30

        # Draw return instruction
        self.renderer.draw_text(self.screen, "[ESC] Return to Menu",
                              w//2, h - 30, size=24, center=True)

    def cleanup(self) -> None:
        """Clean up resources before exit"""
        self.resources.cleanup()
        pygame.quit()
        logging.info("----- Game cleanup completed -----")

##########################
# MAIN ENTRY POINT
##########################

def main():
    """
    Main entry point for the game.
    Initializes and runs the game instance.
    """
    try:
        # Create and run game instance
        game = Game()
        game.run()
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()
