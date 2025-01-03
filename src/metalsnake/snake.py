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
- Robust sound system with programmatically generated sound effects and background music
- Responsive design accommodating window resizing
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
import numpy as np
import io

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
    # Grid settings (will be dynamically calculated based on window size)
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
    POWERUP_SPAWN_INTERVAL: int = 400  # Frames between power-up spawns
    POWERUP_DURATION: int = 500  # Frames power-up effect lasts
    POWERUP_COUNT: int = 3  # Maximum number of active power-ups
    
    # Colors (as RGB tuples)
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

        # Load and start background music (if any)
        # For this implementation, we'll omit background music as sound effects are synthesized
        # If you wish to add background music, you can implement it similarly to sound effects

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
    def __init__(self, x: float, y: float, color: Tuple[int, int, int], config: GameConfig):
        self.config = config
        self.color = color
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
        pygame.draw.circle(surface, self.color,
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
        
    def emit(self, x: float, y: float, count: int, color: Tuple[int, int, int]) -> None:
        """Emit a burst of particles at the specified position with given color"""
        for _ in range(count):
            if self.particle_pool:
                particle = self.particle_pool.pop()
                particle.color = color  # Update color to match power-up
                particle.reset(x, y)
            else:
                particle = Particle(x, y, color, self.config)
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
            game.powerup_manager.active_powerups[self.type] = self.duration  # Correct reference
            game.sound_manager.play_powerup_sound(self.type)
            logging.info("Speed Boost activated!")
        elif self.type == PowerUpType.INVINCIBILITY:
            game.snake.invincible = True
            game.powerup_manager.active_powerups[self.type] = self.duration  # Correct reference
            game.sound_manager.play_powerup_sound(self.type)
            logging.info("Invincibility activated!")
        elif self.type == PowerUpType.SCORE_MULTIPLIER:
            game.score_multiplier += 1  # Increment multiplier
            game.powerup_manager.active_powerups[self.type] = self.duration  # Correct reference
            game.sound_manager.play_powerup_sound(self.type)
            logging.info(f"Score Multiplier activated! Current multiplier: x{game.score_multiplier}")
    
    def expire(self, game: 'Game') -> None:
        """Expire the power-up effect from the game"""
        if self.type == PowerUpType.SPEED_BOOST:
            game.config.GAME_SPEED -= 5  # Revert game speed
            if self.type in game.powerup_manager.active_powerups:
                del game.powerup_manager.active_powerups[self.type]
            logging.info("Speed Boost expired!")
        elif self.type == PowerUpType.INVINCIBILITY:
            game.snake.invincible = False
            if self.type in game.powerup_manager.active_powerups:
                del game.powerup_manager.active_powerups[self.type]
            logging.info("Invincibility expired!")
        elif self.type == PowerUpType.SCORE_MULTIPLIER:
            game.score_multiplier = max(1, game.score_multiplier - 1)  # Decrement multiplier but not below 1
            if self.type in game.powerup_manager.active_powerups:
                del game.powerup_manager.active_powerups[self.type]
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
        # Update spawn timer
        self.spawn_timer += 1
        if self.spawn_timer >= self.config.POWERUP_SPAWN_INTERVAL:
            self.spawn_powerup(game)
            self.spawn_timer = 0

        # Update active power-up durations
        for powerup_type in list(self.active_powerups.keys()):  # Create a copy of keys to modify dict during iteration
            self.active_powerups[powerup_type] -= 1
            if self.active_powerups[powerup_type] <= 0:
                # Create a temporary PowerUp object to handle expiration
                temp_powerup = PowerUp(0, 0, powerup_type, self.config)
                temp_powerup.expire(game)
                logging.info(f"Power-up {powerup_type.name} expired.")
    
        # Check for power-up collection
        head = game.snake.head_position()
        for powerup in self.powerups[:]:  # Use slice copy to safely modify during iteration
            if head == powerup.position():
                powerup.apply(game)
                self.powerups.remove(powerup)
                game.score += 5 * game.score_multiplier  # Bonus for collecting power-up
                # Emit particles at power-up location upon collection
                game.particles.emit(
                    powerup.x * game.cell_size + game.cell_size // 2,
                    powerup.y * game.cell_size + game.cell_size // 2,
                    game.config.PARTICLE_COUNT,
                    self.get_powerup_particle_color(powerup.type)
                )
                logging.info(f"Power-up {powerup.type.name} collected by player.")
    
    def get_powerup_particle_color(self, powerup_type: PowerUpType) -> Tuple[int, int, int]:
        """Return the color for particles emitted from a power-up"""
        if powerup_type == PowerUpType.SPEED_BOOST:
            return (255, 255, 0)  # Yellow
        elif powerup_type == PowerUpType.INVINCIBILITY:
            return (0, 255, 255)  # Cyan
        elif powerup_type == PowerUpType.SCORE_MULTIPLIER:
            return (255, 0, 255)  # Magenta
        else:
            return (255, 255, 255)  # White
    
    def draw(self, surface: pygame.Surface, cell_size: int, frame_count: int, particle_system: ParticleSystem) -> None:
        """Draw all active power-ups with enhanced visuals and animations, matching food depth style"""
        for powerup in self.powerups:
            center_x = powerup.x * cell_size + cell_size // 2
            center_y = powerup.y * cell_size + cell_size // 2
            base_radius = max(cell_size // 2 - 2, 2)

            # Create pulsing effect similar to food
            pulse = abs(math.sin(frame_count * 0.1)) * 0.3 + 0.7
            bob = math.sin(frame_count * 0.08) * cell_size * 0.15

            # Get color based on power-up type
            if powerup.type == PowerUpType.SPEED_BOOST:
                core_color = (200, 200, 0)  # Darker yellow
                glow_color = (255, 255, 0)  # Bright yellow
            elif powerup.type == PowerUpType.INVINCIBILITY:
                core_color = (0, 180, 180)  # Darker cyan
                glow_color = (0, 255, 255)  # Bright cyan
            elif powerup.type == PowerUpType.SCORE_MULTIPLIER:
                core_color = (180, 0, 180)  # Darker magenta
                glow_color = (255, 0, 255)  # Bright magenta
            else:
                core_color = (255, 255, 255)  # White
                glow_color = (255, 255, 255)

            # Draw outer glow layers similar to food
            for radius in range(base_radius + 4, base_radius - 1, -1):
                alpha = int(100 * pulse * (radius - base_radius + 4) / 4)
                current_glow = (*glow_color[:3], alpha)
                glow_surface = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, current_glow,
                                 (radius + 1, radius + 1), radius)
                surface.blit(glow_surface,
                            (center_x - radius - 1, center_y - radius - 1 + bob))

            # Draw main power-up body
            pygame.draw.circle(surface, core_color,
                             (center_x, center_y + bob), base_radius)

            # Add highlight for depth
            highlight_pos = (center_x - base_radius // 3,
                           center_y - base_radius // 3 + bob)
            highlight_radius = max(base_radius // 3, 1)
            highlight_color = tuple(min(255, c + 100) for c in core_color)
            pygame.draw.circle(surface, highlight_color,
                             highlight_pos, highlight_radius)

            # Emit particles for floating effect
            if frame_count % 10 == 0:  # Reduced particle emission rate
                particle_system.emit(
                    center_x, center_y + bob, 1,
                    self.get_powerup_particle_color(powerup.type)
                )

##########################
# SOUND SYNTHESIS AND MANAGER
##########################

class SoundSynthesizer:
    """
    Generates game sound effects using digital sound synthesis.
    Creates sounds programmatically instead of loading from files.
    """
    def __init__(self):
        # Standard audio parameters
        self.sample_rate = 44100  # CD quality audio
        self.amplitude = 0.3      # Default volume (reduced to prevent clipping)
    
    def create_sine_wave(self, frequency: float, duration: float) -> np.ndarray:
        """
        Creates a sine wave of given frequency and duration.
        This is the most basic building block of sound synthesis.
        """
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        return np.sin(2 * np.pi * frequency * t)
    
    def apply_envelope(self, samples: np.ndarray, attack: float = 0.1, 
                      decay: float = 0.1, sustain: float = 0.7,
                      release: float = 0.1) -> np.ndarray:
        """
        Applies an ADSR envelope to a sound.
        This shapes the amplitude over time to create more natural sounds.
        """
        total_length = len(samples)
        envelope = np.ones(total_length)
        
        # Calculate segment lengths
        attack_len = int(attack * total_length)
        decay_len = int(decay * total_length)
        release_len = int(release * total_length)
        sustain_len = total_length - attack_len - decay_len - release_len
        
        # Create envelope segments
        envelope[:attack_len] = np.linspace(0, 1, attack_len)
        envelope[attack_len:attack_len + decay_len] = np.linspace(1, sustain, decay_len)
        envelope[attack_len + decay_len:-release_len] = sustain
        envelope[-release_len:] = np.linspace(sustain, 0, release_len)
        
        return samples * envelope
    
    def create_noise(self, duration: float) -> np.ndarray:
        """
        Creates white noise, useful for percussive and texture sounds.
        """
        samples = np.random.uniform(-1, 1, int(self.sample_rate * duration))
        return samples
    
    def apply_lowpass_filter(self, samples: np.ndarray, cutoff: float) -> np.ndarray:
        """
        Applies a simple lowpass filter to smooth out harsh frequencies.
        """
        # Simple moving average filter
        window_size = int(self.sample_rate / cutoff)
        window = np.ones(window_size) / window_size
        return np.convolve(samples, window, mode='same')
    
    def create_powerup_sound(self) -> pygame.mixer.Sound:
        """
        Creates an ascending magical sound for power-up collection.
        Combines multiple frequencies with pitch modulation.
        """
        duration = 0.5
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        # Create ascending frequency
        freq_start = 220
        freq_end = 880
        frequency = np.linspace(freq_start, freq_end, len(t))
        
        # Generate main tone with frequency modulation
        main_tone = np.sin(2 * np.pi * frequency * t)
        
        # Add harmonics for richness
        harmonic1 = 0.5 * np.sin(4 * np.pi * frequency * t)
        harmonic2 = 0.25 * np.sin(6 * np.pi * frequency * t)
        
        # Combine waves
        combined = main_tone + harmonic1 + harmonic2
        
        # Apply envelope for smooth start/end
        sound = self.apply_envelope(combined, attack=0.1, decay=0.1, sustain=0.6, release=0.2)
        
        return self.create_pygame_sound(sound)
    
    def create_movement_sound(self) -> pygame.mixer.Sound:
        """
        Creates a soft swooshing sound for snake movement.
        Uses filtered noise with frequency modulation.
        """
        duration = 0.15
        
        # Create noise base
        noise = self.create_noise(duration)
        
        # Apply bandpass filtering to create swoosh effect
        filtered_noise = self.apply_lowpass_filter(noise, 1000)
        
        # Add subtle sine wave for tone
        t = np.linspace(0, duration, len(filtered_noise), False)
        tone = 0.3 * np.sin(2 * np.pi * 200 * t)
        
        # Combine and shape
        combined = filtered_noise + tone
        sound = self.apply_envelope(combined, attack=0.05, decay=0.05, sustain=0.5, release=0.4)
        
        return self.create_pygame_sound(combined)
    
    def create_food_pickup_sound(self) -> pygame.mixer.Sound:
        """
        Creates a bright, short sound for food collection.
        Uses multiple harmonics for a rich, pleasant tone.
        """
        duration = 0.2
        frequencies = [440, 880, 1320]  # Root note and harmonics
        amplitudes = [1.0, 0.5, 0.25]   # Decreasing amplitude for harmonics
        
        combined = np.zeros(int(self.sample_rate * duration))
        
        # Add harmonics
        for freq, amp in zip(frequencies, amplitudes):
            wave = self.create_sine_wave(freq, duration)
            combined += amp * wave
        
        # Shape the sound with quick attack and decay
        sound = self.apply_envelope(combined, attack=0.05, decay=0.15, sustain=0.6, release=0.2)
        
        return self.create_pygame_sound(sound)
    
    def create_game_over_sound(self) -> pygame.mixer.Sound:
        """
        Creates a dramatic descending sound for game over.
        Combines multiple descending tones with reverb effect.
        """
        duration = 1.0
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        # Create descending frequencies
        freq_start = 440
        freq_end = 110
        frequency = np.linspace(freq_start, freq_end, len(t))
        
        # Generate main tone
        main_tone = np.sin(2 * np.pi * frequency * t)
        
        # Add lower octave
        low_tone = 0.5 * np.sin(np.pi * frequency * t)
        
        # Add noise for texture
        noise = 0.1 * self.create_noise(duration)
        
        # Combine everything
        combined = main_tone + low_tone + noise
        
        # Apply dramatic envelope
        sound = self.apply_envelope(combined, attack=0.1, decay=0.3, sustain=0.4, release=0.2)
        
        return self.create_pygame_sound(combined)
    
    def create_pygame_sound(self, samples: np.ndarray) -> pygame.mixer.Sound:
        """
        Converts numpy samples to a Pygame sound object.
        Handles audio scaling and conversion to the correct format.
        """
        # Normalize to prevent clipping
        samples = np.int16(samples * 32767 * self.amplitude)
        
        # Create a Python bytes buffer
        buffer = samples.tobytes()
        
        # Create Pygame sound from buffer
        sound = pygame.mixer.Sound(buffer=buffer)
        return sound

class SoundManager:
    """
    Manages all game audio including sound effects and background music.
    Uses channel-based mixing for simultaneous sound playback.
    Provides volume control and audio mixing between different sound types.
    """
    def __init__(self, config: GameConfig, resource_manager: ResourceManager):
        self.config = config
        self.resource_manager = resource_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize sound mixing with multiple channels
        pygame.mixer.set_num_channels(32)  # Allow many simultaneous sounds
        
        # Create dedicated channels for different sound types
        self.movement_channel = pygame.mixer.Channel(0)  # Snake movement sounds
        self.pickup_channel = pygame.mixer.Channel(1)    # Food and power-up collection
        self.effect_channel = pygame.mixer.Channel(2)    # Power-up active effects
        self.ui_channel = pygame.mixer.Channel(3)        # UI and menu sounds
        
        # Create synthesizer for effects
        self.synthesizer = SoundSynthesizer()
        
        # Create and cache sound effects
        self._sound_cache = {
            'move': self.synthesizer.create_movement_sound(),
            'food_pickup': self.synthesizer.create_food_pickup_sound(),
            'powerup': self.synthesizer.create_powerup_sound(),
            'game_over': self.synthesizer.create_game_over_sound()
        }
        
        # Volume settings (keeping music quieter than effects)
        self.master_volume = 0.7
        self.music_volume = 0.3  # Reduced music volume
        self.sfx_volume = 0.5
        
        # Movement sound timer to prevent too frequent sounds
        self.last_movement_sound = 0
        self.movement_sound_interval = 150  # Milliseconds between movement sounds
        
        # Start background music
        self._init_background_music()
    
    def _init_background_music(self) -> None:
        """Initialize and start background music playback"""
        try:
            music_path = self.resource_manager.resource_path(os.path.join("audio", "MidnightCarnage.mp3"))
            if os.path.exists(music_path):
                pygame.mixer.music.load(music_path)
                pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
                pygame.mixer.music.play(-1)  # Loop indefinitely
                self.logger.info("Background music started successfully")
            else:
                self.logger.warning("Background music file not found")
        except Exception as e:
            self.logger.error(f"Failed to initialize background music: {e}")
    
    def play_sound(self, sound_name: str, channel: Optional[pygame.mixer.Channel] = None,
                  volume: float = 1.0) -> None:
        """Play a sound effect with volume adjustment"""
        sound = self._sound_cache.get(sound_name)
        if sound is None:
            return
        
        # Apply volume settings
        final_volume = self.master_volume * self.sfx_volume * volume
        sound.set_volume(final_volume)
        
        # Play on specified channel or any free one
        if channel and not channel.get_busy():
            channel.play(sound)
        elif not channel:
            free_channel = pygame.mixer.find_channel(True)
            if free_channel:
                free_channel.play(sound)
    
    def play_movement_sound(self, speed: float) -> None:
        """
        Play movement sound with rate limiting.
        Prevents sound overlap at high speeds.
        """
        current_time = pygame.time.get_ticks()
        if current_time - self.last_movement_sound >= self.movement_sound_interval:
            # Calculate volume based on speed but keep it subtle
            volume = min(0.3, 0.2 * (speed / self.config.BASE_GAME_SPEED))
            self.play_sound('move', self.movement_channel, volume=volume)
            self.last_movement_sound = current_time
    
    def play_powerup_sound(self, powerup_type: PowerUpType) -> None:
        """Play power-up collection sound"""
        self.play_sound('powerup', self.pickup_channel, volume=0.6)
    
    def play_game_over_sound(self) -> None:
        """Play game over sound and pause background music"""
        pygame.mixer.music.pause()  # Pause background music
        self.play_sound('game_over', self.effect_channel, volume=0.7)
    
    def play_menu_sound(self, action: str) -> None:
        """Play UI sound for menu interactions"""
        if action == 'select':
            # You can create and add more sounds as needed
            self.play_sound('powerup', self.ui_channel, volume=0.4)
        elif action == 'move':
            self.play_sound('food_pickup', self.ui_channel, volume=0.2)
    
    def resume_music(self) -> None:
        """Resume background music playback"""
        pygame.mixer.music.unpause()
        pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
    
    def set_master_volume(self, volume: float) -> None:
        """Set master volume level and update all active sounds"""
        self.master_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
    
    def cleanup(self) -> None:
        """Clean up sound resources"""
        pygame.mixer.music.stop()
        self._sound_cache.clear()
        pygame.mixer.stop()
        self.logger.info("Sound system cleaned up")

##########################
# RENDERER CLASS
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
            glow_surface = pygame.Surface((radius * 2 + 2, radius * 2 + 2), pygame.SRCALPHA)
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
                glow_surface = pygame.Surface((glow_radius * 2 + 2, glow_radius * 2 + 2), pygame.SRCALPHA)
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
                     cell_size: int, frame_count: int, particle_system: ParticleSystem) -> None:
        """Draw all active power-ups with enhanced visuals and animations, matching food depth style"""
        powerup_manager.draw(surface, cell_size, frame_count, particle_system)
    
    def draw_active_powerups_status(self, surface: pygame.Surface,
                                  powerup_manager: 'PowerUpManager',
                                  score_multiplier: int,
                                  frame_count: int) -> None:
        """Draw active power-ups status display in top right corner"""
        screen_width = surface.get_width()
        padding = 10
        y_offset = padding
        status_height = 30
        icon_size = status_height - 4

        for powerup_type, remaining in powerup_manager.active_powerups.items():
            # Calculate position for status bar
            x_pos = screen_width - 220 - padding  # Adjusted to accommodate icon and text

            # Get power-up properties
            if powerup_type == PowerUpType.SPEED_BOOST:
                label = "Speed Boost"
                color = (255, 255, 0)  # Yellow
                dark_color = (200, 200, 0)
            elif powerup_type == PowerUpType.INVINCIBILITY:
                label = "Invincibility"
                color = (0, 255, 255)  # Cyan
                dark_color = (0, 180, 180)
            elif powerup_type == PowerUpType.SCORE_MULTIPLIER:
                label = f"Score x{score_multiplier}"
                color = (255, 0, 255)  # Magenta
                dark_color = (180, 0, 180)
            else:
                label = "Unknown"
                color = (255, 255, 255)  # White
                dark_color = (255, 255, 255)

            # Draw the power-up icon
            icon_x = x_pos + 10
            icon_y = y_offset + status_height // 2
            pygame.draw.circle(surface, dark_color, (icon_x, icon_y), icon_size // 2)
            pygame.draw.circle(surface, color, (icon_x, icon_y), icon_size // 2, 2)

            # Calculate and draw progress bar
            progress = remaining / self.config.POWERUP_DURATION
            progress_width = int(160 * progress)  # 160 = bar width - padding
            progress_rect = pygame.Rect(x_pos + 30, y_offset + 5,
                                      progress_width, status_height - 10)
            
            # Flashing effect when about to expire
            if remaining <= 5 * self.config.FPS:  # Last 5 seconds
                if frame_count % 30 < 15:  # Flash every half second
                    pygame.draw.rect(surface, (255, 0, 0), progress_rect)
                else:
                    pygame.draw.rect(surface, color, progress_rect)
            else:
                pygame.draw.rect(surface, color, progress_rect)

            # Draw background for progress bar
            pygame.draw.rect(surface, (100, 100, 100), pygame.Rect(x_pos + 30, y_offset + 5, 160, status_height - 10), 2)

            # Draw label with remaining time
            time_seconds = remaining // self.config.FPS  # Convert frames to seconds
            time_text = f"{label} ({time_seconds}s)"
            self.draw_text(surface, time_text,
                          x_pos + 30, y_offset + 5,
                          size=16, color=(255, 255, 255))
            
            y_offset += status_height + 5  # Space between status bars

##########################
# SNAKE CLASS
##########################

class Snake:
    """
    Represents the snake entity with its movement logic and collision detection.
    Handles snake movement, growth, and collision checking.
    Implements conditional wrap-around movement based on invincibility.
    """
    def __init__(self, config: GameConfig):
        self.config = config
        self.body: List[Tuple[int, int]] = [(15, 10), (14, 10), (13, 10)]
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
                glow_surface = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, glow_color,
                                 (radius + 4, radius + 4), radius + 4)
                surface.blit(glow_surface, (center_x - radius - 4, center_y - radius - 4))
                
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
                eye_glow_color = (*self.config.WHITE[:3], 128)
                eye_glow_surface = pygame.Surface((eye_r * 2 + 4, eye_r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(eye_glow_surface, eye_glow_color,
                                 (eye_r + 2, eye_r + 2), eye_r + 2)
                surface.blit(eye_glow_surface, (eye_pos1[0] - eye_r - 2, eye_pos1[1] - eye_r - 2))
                surface.blit(eye_glow_surface, (eye_pos2[0] - eye_r - 2, eye_pos2[1] - eye_r - 2))
                
                # Eyes
                pygame.draw.circle(surface, self.config.WHITE,
                                 eye_pos1, eye_r)
                pygame.draw.circle(surface, self.config.WHITE,
                                 eye_pos2, eye_r)
            else:  # Body
                base_r = max(cell_size // 2 - 2, 2)
                radius = max(base_r + int(wave), 2)
                
                # Add glow effect to body segments
                glow_color = (0, 200, 0, 80) if not self.invincible else (0, 200, 200, 120)
                glow_surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, glow_color,
                                 (radius + 2, radius + 2), radius + 2)
                surface.blit(glow_surface, (center_x - radius - 2, center_y - radius - 2))
                
                pygame.draw.circle(surface, self.config.BLACK,
                                 (center_x, center_y), radius + 2)
                seg_color = self.config.GREEN if not self.invincible else self.config.CYAN
                pygame.draw.circle(surface, seg_color,
                                 (center_x, center_y), radius)

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
        self.sound_manager = SoundManager(self.config, self.resources)  # Initialize SoundManager

        # Set up logging after ResourceManager to use correct log path
        log_path = self.resources.get_log_path("snake_game.log")
        logging.basicConfig(
            filename=log_path,
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.info("----- Starting Snake Game -----")

        # Initialize Pygame window with default size 800x600
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
        pygame.mixer.music.unpause()  # Ensure music is playing
        self.sound_manager.resume_music()
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
                    # Recalculate cell size based on new window size
                    self.cell_size = min(event.w // self.config.GRID_COLS, event.h // self.config.GRID_ROWS)
                    logging.info(f"Window resized to {event.w}x{event.h}. Cell size set to {self.cell_size}.")

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
                    self.sound_manager.play_menu_sound('select')
                elif event.key == pygame.K_h:
                    self.state = GameState.HIGHSCORES
                    self.sound_manager.play_menu_sound('select')
                elif event.key == pygame.K_o:
                    self.obstacles_enabled = not self.obstacles_enabled
                    logging.info(f"Obstacles toggled to {'ON' if self.obstacles_enabled else 'OFF'}.")
                    self.sound_manager.play_menu_sound('move')
                elif event.key == pygame.K_ESCAPE:
                    self.cleanup()
                    sys.exit()

        # Draw menu
        w, h = self.screen.get_size()
        self.cell_size = min(w // self.config.GRID_COLS, h // self.config.GRID_ROWS)  # Ensure cell size is set
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
                    self.sound_manager.play_menu_sound('select')

        # Update game logic at fixed rate
        should_update = self.frame_count % (self.config.FPS // self.config.GAME_SPEED) == 0
        if should_update:
            self.game_tick += 1

            # Move snake and check collisions
            if not self.snake.move(self.food_pos, self.obstacles):
                self.TEMP_SCORE = self.score
                self.TEMP_MODE = "obstacles" if self.obstacles_enabled else "classic"
                self.state = GameState.GAME_OVER
                self.sound_manager.play_game_over_sound()
                logging.info(f"Game Over! Score: {self.TEMP_SCORE}, Mode: {self.TEMP_MODE}")
                return

            # Play movement sound
            self.sound_manager.play_movement_sound(self.config.GAME_SPEED)

            # Check food collection
            head = self.snake.body[0]
            if head == self.food_pos:
                bonus = (1 + self.config.OBSTACLE_BONUS) if self.obstacles_enabled else 1
                self.score += bonus * self.score_multiplier
                px = head[0] * self.cell_size + self.cell_size//2
                py = head[1] * self.cell_size + self.cell_size//2
                self.particles.emit(px, py, self.config.PARTICLE_COUNT, (255, 0, 0))  # Red particles for food
                self.food_pos = self.get_random_position()
                self.sound_manager.play_sound('food_pickup', self.sound_manager.pickup_channel)
                logging.info(f"Food collected! New score: {self.score}")

        # Update power-ups
        self.powerup_manager.update(self)

        # Draw game state
        self.renderer.draw_background(self.screen, w, h)
        self.renderer.draw_overlay(self.screen, w, h, alpha=50)
        self.renderer.draw_obstacles(self.screen, self.obstacles, self.cell_size, self.frame_count)
        self.renderer.draw_food(self.screen, self.food_pos[0], self.food_pos[1],
                              self.cell_size, self.frame_count)
        self.renderer.draw_powerups(self.screen, self.powerup_manager, self.cell_size, self.frame_count, self.particles)
        self.snake.draw(self.screen, self.cell_size, self.frame_count)
        self.particles.update_and_draw(self.screen)
        # Pass score_multiplier to the renderer
        self.renderer.draw_active_powerups_status(self.screen, self.powerup_manager, self.score_multiplier, self.frame_count)
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
                    self.sound_manager.play_menu_sound('select')
                    self.sound_manager.resume_music()
                elif event.key == pygame.K_h:
                    final_name = Game.player_name.strip() or "Player"
                    self.score_manager.add_score(final_name, self.TEMP_SCORE, self.TEMP_MODE)
                    logging.info(f"High score added: {final_name} - {self.TEMP_SCORE} in {self.TEMP_MODE} mode.")
                    Game.player_name = ""
                    self.state = GameState.HIGHSCORES
                    self.sound_manager.play_menu_sound('select')
                elif event.key == pygame.K_ESCAPE:
                    Game.player_name = ""
                    self.state = GameState.MENU
                    self.sound_manager.play_menu_sound('select')
                    self.sound_manager.resume_music()
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
                    self.sound_manager.play_menu_sound('select')
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
        self.sound_manager.cleanup()
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
