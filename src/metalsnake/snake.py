"""
snake.py

An enhanced implementation of the Snake game using Pygame.
Features include:
- Background music integration
- Magnet power-up functionality
- Advanced glow and shine visual effects
- Additional power-ups for varied gameplay
- Improved particle system with object pooling
- Responsive design adjustments for window resizing
- Comprehensive logging and error handling
- Sound synthesis and management with programmatically generated sounds
"""

import pygame
import sys
import random
import math
import json
import os
import logging
from typing import Tuple, Set, List, Optional, Dict, Any
from dataclasses import dataclass, field
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
    SETTINGS = auto()

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
    MAGNET = auto()
    SHRINK = auto()

@dataclass
class GameConfig:
    """
    Centralized configuration for game settings.
    Using dataclass for automatic initialization and cleaner syntax.
    """
    # Grid settings (will be dynamically calculated based on window size)
    GRID_COLS: int = 30
    GRID_ROWS: int = 20
    cell_size: int = 20  # Default cell size, will be updated based on window size
    
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
    SCORE_THRESHOLD: int = 50  # Points needed to increase speed
    SPEED_INCREMENT: int = 2    # How much to increase speed each threshold
    
    # Power-up system
    POWERUP_TYPES: List[PowerUpType] = field(default_factory=lambda: [
        PowerUpType.SPEED_BOOST,
        PowerUpType.INVINCIBILITY,
        PowerUpType.SCORE_MULTIPLIER,
        PowerUpType.MAGNET,
        PowerUpType.SHRINK
    ])
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
    CYAN: Tuple[int, ...] = (0, 255, 255)
    MAGENTA: Tuple[int, ...] = (200, 0, 200)
    ORANGE: Tuple[int, ...] = (255, 165, 0)
    GOLD: Tuple[int, ...] = (255, 215, 0)
    PURPLE: Tuple[int, ...] = (128, 0, 128)
    BROWN: Tuple[int, ...] = (165, 42, 42)
    SKY_BLUE: Tuple[int, ...] = (135, 206, 235)


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
            path = self.resource_path(os.path.join("images", "snake.png"))  # Updated to 'snake.png'
            if not os.path.exists(path):
                self.logger.error(f"Background image not found at {path}")
                # Create a default background
                self._background = pygame.Surface((self.config.GRID_COLS * 20, self.config.GRID_ROWS * 20))
                self._background.fill(self.config.BLACK)
                return self._background
            try:
                self._background = pygame.image.load(path).convert_alpha()  # Use convert_alpha to preserve transparency
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
        elif self.type == PowerUpType.MAGNET:
            game.powerup_manager.magnet_active = True
            game.powerup_manager.active_powerups[self.type] = self.duration
            game.sound_manager.play_powerup_sound(self.type)
            logging.info("Magnet activated!")
        elif self.type == PowerUpType.SHRINK:
            if len(game.snake.body) > 3:
                game.snake.body = game.snake.body[:-2]  # Remove two segments
                game.score = max(0, game.score - 5)  # Penalize score slightly
                game.powerup_manager.active_powerups[self.type] = self.duration
                game.sound_manager.play_powerup_sound(self.type)
                logging.info("Shrink activated! Snake size reduced.")
    
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
        elif self.type == PowerUpType.MAGNET:
            game.powerup_manager.magnet_active = False
            if self.type in game.powerup_manager.active_powerups:
                del game.powerup_manager.active_powerups[self.type]
            logging.info("Magnet expired!")
        elif self.type == PowerUpType.SHRINK:
            if self.type in game.powerup_manager.active_powerups:
                del game.powerup_manager.active_powerups[self.type]
            logging.info("Shrink expired!")
    
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
        self.magnet_active: bool = False  # Tracks if magnet is active
    
    def spawn_powerup(self, game: 'Game') -> None:
        """Spawn a new power-up at a random position"""
        if len(self.powerups) >= self.config.POWERUP_COUNT:
            return  # Maximum active power-ups reached

        powerup_type = random.choice(self.config.POWERUP_TYPES)
        x, y = game.get_random_position(include_powerups=True)
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
                    powerup.x * game.cell_size + game.cell_size // 2 + game.renderer.x_offset,
                    powerup.y * game.cell_size + game.cell_size // 2 + game.renderer.y_offset,
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
        elif powerup_type == PowerUpType.MAGNET:
            return (0, 255, 0)    # Green
        elif powerup_type == PowerUpType.SHRINK:
            return (255, 165, 0)  # Orange
        else:
            return (255, 255, 255)  # White
    
    def draw(self, surface: pygame.Surface, cell_size: int, frame_count: int, particle_system: ParticleSystem) -> None:
        """Draw all active power-ups with enhanced visuals and animations"""
        for powerup in self.powerups:
            center_x, center_y = surface.get_size()
            center_x, center_y = 0, 0  # Placeholders; actual positions are handled by Renderer
            # Drawing is handled by Renderer
            pass  # No action needed here as Renderer handles drawing


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
        return np.sin(2 * math.pi * frequency * t)
    
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
        main_tone = np.sin(2 * math.pi * frequency * t)
        
        # Add harmonics for richness
        harmonic1 = 0.5 * np.sin(4 * math.pi * frequency * t)
        harmonic2 = 0.25 * np.sin(6 * math.pi * frequency * t)
        
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
        tone = 0.3 * np.sin(2 * math.pi * 200 * t)
        
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
        main_tone = np.sin(2 * math.pi * frequency * t)
        
        # Add lower octave
        low_tone = 0.5 * np.sin(math.pi * frequency * t)
        
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
            # Reusing 'powerup' sound for selection
            self.play_sound('powerup', self.ui_channel, volume=0.4)
        elif action == 'move':
            # Reusing 'food_pickup' sound for navigation
            self.play_sound('food_pickup', self.ui_channel, volume=0.2)
    
    def resume_music(self) -> None:
        """Resume background music playback"""
        pygame.mixer.music.unpause()
        pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
    
    def set_master_volume(self, volume: float) -> None:
        """Set master volume level and update all active sounds"""
        self.master_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
    
    def set_music_volume(self, volume: float) -> None:
        """Set background music volume"""
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.master_volume * self.music_volume)
        logging.info(f"Background music volume set to {self.music_volume}")
    
    def set_sfx_volume(self, volume: float) -> None:
        """Set sound effects volume"""
        self.sfx_volume = max(0.0, min(1.0, volume))
        logging.info(f"Sound effects volume set to {self.sfx_volume}")
    
    def toggle_music(self) -> None:
        """Toggle background music on or off"""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            logging.info("Background music paused")
        else:
            pygame.mixer.music.unpause()
            logging.info("Background music resumed")
    
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
        self.x_offset = 0
        self.y_offset = 0
        
    def update_offsets(self, window_width: int, window_height: int) -> None:
        """Calculate and update the top-left offset to center the grid"""
        grid_width = self.config.GRID_COLS * self.config.cell_size
        grid_height = self.config.GRID_ROWS * self.config.cell_size
        self.x_offset = max((window_width - grid_width) // 2, 0)
        self.y_offset = max((window_height - grid_height) // 2, 0)
        
    def grid_to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """Convert grid coordinates to screen coordinates based on offsets"""
        screen_x = x * self.config.cell_size + self.x_offset
        screen_y = y * self.config.cell_size + self.y_offset
        return (screen_x, screen_y)
    
    def draw_background(self, surface: pygame.Surface,
                       width: int, height: int) -> None:
        """Draw background scaled to grid size and centered"""
        background = self.resources.get_background()
        if background:
            bg_scaled = pygame.transform.scale(background, (self.config.GRID_COLS * self.config.cell_size,
                                                           self.config.GRID_ROWS * self.config.cell_size))
            surface.blit(bg_scaled, (self.x_offset, self.y_offset))
        else:
            # Fill the grid area with black
            pygame.draw.rect(surface, self.config.BLACK,
                             (self.x_offset, self.y_offset,
                              self.config.GRID_COLS * self.config.cell_size,
                              self.config.GRID_ROWS * self.config.cell_size))
            
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
        screen_x, screen_y = self.grid_to_screen(x, y)
        center_x = screen_x + cell_size // 2
        center_y = screen_y + cell_size // 2
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
                      obstacles: Set['Obstacle'],
                      cell_size: int, frame_count: int) -> None:
        """Draw obstacles with magical appearance"""
        for obstacle in obstacles:
            obstacle.draw(surface, self)
    
    def draw_powerups(self, surface: pygame.Surface, powerup_manager: 'PowerUpManager',
                     cell_size: int, frame_count: int, particle_system: ParticleSystem) -> None:
        """Draw all active power-ups with enhanced visuals and animations"""
        powerup_manager.draw(surface, cell_size, frame_count, particle_system)
    
    def draw_snake(self, surface: pygame.Surface, snake_body: List[Tuple[int, int]], frame_count: int, invincible: bool) -> None:
        """Draw snake with animated effects"""
        for i, (sx, sy) in enumerate(snake_body):
            screen_x, screen_y = self.grid_to_screen(sx, sy)
            center_x = screen_x + self.config.cell_size // 2
            center_y = screen_y + self.config.cell_size // 2

            # Calculate wave effect
            phase = (frame_count * 0.1) + i * 0.3
            wave = 2 * math.sin(phase)

            if i == 0:  # Head
                base_r = self.config.cell_size // 2 - 2
                radius = max(base_r + int(wave), 2)
                
                # Add glow effect to head
                glow_color = (0, 255, 0, 100) if not invincible else (0, 255, 255, 150)
                glow_surface = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, glow_color,
                                 (radius + 4, radius + 4), radius + 4)
                surface.blit(glow_surface, (center_x - radius - 4, center_y - radius - 4))
                
                pygame.draw.circle(surface, self.config.BLACK,
                                 (center_x, center_y), radius + 2)
                head_color = self.config.GREEN if not invincible else self.config.CYAN
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
                base_r = max(self.config.cell_size // 2 - 4, 2)
                radius = max(base_r + int(wave), 2)
                
                # Add glow effect to body segments
                glow_color = (0, 200, 0, 80) if not invincible else (0, 200, 200, 120)
                glow_surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, glow_color,
                                 (radius + 2, radius + 2), radius + 2)
                surface.blit(glow_surface, (center_x - radius - 2, center_y - radius - 2))
                
                pygame.draw.circle(surface, self.config.BLACK,
                                 (center_x, center_y), radius + 2)
                seg_color = self.config.GREEN if not invincible else self.config.CYAN
                pygame.draw.circle(surface, seg_color,
                                 (center_x, center_y), radius)
    
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
        
        # Removed the empty draw method as rendering is handled by Renderer.draw_snake


##########################
# OBSTACLE CLASS
##########################

class Obstacle:
    """
    Represents an obstacle in the game.
    Handles movement and rendering with enhanced collision detection.
    """
    def __init__(self, x: int, y: int, direction: Direction, config: GameConfig):
        self.x = x
        self.y = y
        self.direction = direction
        self.config = config
        self.color = self.config.GRAY
        self.size = self.config.cell_size - 4  # Padding for visual appeal
    
    def move(self):
        """Move obstacle based on its direction"""
        if self.direction == Direction.UP:
            self.y -= 1
        elif self.direction == Direction.DOWN:
            self.y += 1
        elif self.direction == Direction.LEFT:
            self.x -= 1
        elif self.direction == Direction.RIGHT:
            self.x += 1
        
        # Wrap around the grid
        self.x %= self.config.GRID_COLS
        self.y %= self.config.GRID_ROWS
    
    def get_rect(self) -> pygame.Rect:
        """Get obstacle rectangle"""
        return pygame.Rect(self.x * self.config.cell_size + 2, self.y * self.config.cell_size + 2, self.size, self.size)
    
    def draw(self, surface: pygame.Surface, renderer: Renderer):
        """Draw obstacle as a rectangle with rounded corners"""
        screen_x, screen_y = renderer.grid_to_screen(self.x, self.y)
        rect = pygame.Rect(screen_x + 2, screen_y + 2, self.size, self.size)
        pygame.draw.rect(surface, self.color, rect, border_radius=8)


##########################
# SETTINGS CLASS
##########################

class Settings:
    """
    Handles game settings such as sound volumes and key bindings.
    """
    def __init__(self, config: GameConfig, resource_manager: ResourceManager):
        self.config = config
        self.resource_manager = resource_manager  # Added ResourceManager reference
        self.key_bindings = {
            'UP': pygame.K_UP,
            'DOWN': pygame.K_DOWN,
            'LEFT': pygame.K_LEFT,
            'RIGHT': pygame.K_RIGHT,
            'PLAY': pygame.K_p,
            'HIGHSCORES': pygame.K_h,
            'TOGGLE_OBSTACLES': pygame.K_o,
            'OPTIONS': pygame.K_s,
            'QUIT': pygame.K_ESCAPE,
            'PAUSE': pygame.K_ESCAPE,
            'SUBMIT': pygame.K_RETURN,
            'VIEW_HIGHSCORES': pygame.K_h
        }
        self.load_settings()
    
    def load_settings(self) -> None:
        """Load settings from file"""
        settings_path = self.resource_manager.get_data_path("settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    data = json.load(f)
                self.key_bindings = data.get("key_bindings", self.key_bindings)
                logging.info("Settings loaded successfully.")
            except Exception as e:
                logging.error(f"Error loading settings: {e}")
        else:
            # Initialize default settings if file doesn't exist
            self.save_settings()
    
    def save_settings(self) -> None:
        """Save settings to file"""
        settings_path = self.resource_manager.get_data_path("settings.json")
        try:
            with open(settings_path, 'w') as f:
                json.dump({"key_bindings": self.key_bindings}, f, indent=4)
            logging.info("Settings saved successfully.")
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
    
    def set_key_binding(self, action: str, key: int) -> None:
        """Set a new key binding for a specific action"""
        if action in self.key_bindings:
            self.key_bindings[action] = key
            self.save_settings()
            logging.info(f"Key binding for {action} set to {pygame.key.name(key)}")
    
    def get_key(self, action: str) -> int:
        """Get the key binding for a specific action"""
        return self.key_bindings.get(action, pygame.K_ESCAPE)


##########################
# MAIN GAME CLASS
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
        self.settings = Settings(self.config, self.resources)  # Passed ResourceManager to Settings
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
        self.snake: Optional[Snake] = None
        self.score = 0
        self.game_tick = 0
        self.food_pos: Optional[Tuple[int, int]] = None
        self.obstacles: Set[Obstacle] = set()
        self.score_multiplier = 1  # For score multiplier power-up
        self.active_powerups: Dict[PowerUpType, int] = {}
        self.magnet_active: bool = False  # Tracks if magnet is active
        self.cell_size = 0  # Will be set in run()
        self.settings_menu_active = False

        # Set initial offsets
        window_width, window_height = self.screen.get_size()
        self.cell_size = min(window_width // self.config.GRID_COLS, window_height // self.config.GRID_ROWS)
        self.config.cell_size = self.cell_size
        self.renderer.update_offsets(window_width, window_height)

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
        self.magnet_active = False
        self.sound_manager.resume_music()  # Ensure music is playing
        logging.info("Game has been reset.")

    def get_random_position(self, include_powerups: bool = False) -> Tuple[int, int]:
        """Get random grid position avoiding snake, obstacles, and existing power-ups"""
        while True:
            if self.powerup_manager.magnet_active:
                # Place food closer to the snake's head
                head_x, head_y = self.snake.head_position()
                # Define a range within which to spawn food
                range_x = max(head_x - 5, 0), min(head_x + 5, self.config.GRID_COLS - 1)
                range_y = max(head_y - 5, 0), min(head_y + 5, self.config.GRID_ROWS - 1)
                x = random.randint(*range_x)
                y = random.randint(*range_y)
            else:
                x = random.randint(0, self.config.GRID_COLS - 1)
                y = random.randint(0, self.config.GRID_ROWS - 1)
            pos = (x, y)
            if (pos not in self.snake.body and
                pos not in { (ob.x, ob.y) for ob in self.obstacles } and
                (not include_powerups or pos not in [pu.position() for pu in self.powerup_manager.powerups ])):
                return pos

    def generate_obstacles(self) -> Set[Obstacle]:
        """Generate moving obstacles with random directions"""
        obstacles = set()
        for _ in range(self.config.OBSTACLE_COUNT):
            pos = self.get_random_position()
            direction = random.choice(list(Direction))
            obstacle = Obstacle(pos[0], pos[1], direction, self.config)
            obstacles.add(obstacle)
        logging.info(f"Generated {len(obstacles)} moving obstacles.")
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
                    self.config.cell_size = self.cell_size
                    logging.info(f"Window resized to {event.w}x{event.h}. Cell size set to {self.cell_size}.")
                    self.renderer.update_offsets(event.w, event.h)  # Update renderer offsets

            # State machine update
            if self.state == GameState.MENU:
                self.update_menu(events)
            elif self.state == GameState.PLAY:
                self.update_game(events)
            elif self.state == GameState.GAME_OVER:
                self.update_game_over(events)
            elif self.state == GameState.HIGHSCORES:
                self.update_highscores(events)
            elif self.state == GameState.SETTINGS:
                self.update_settings(events)

            pygame.display.flip()

    def update_menu(self, events: List[pygame.event.Event]) -> None:
        """Handle menu state updates and rendering"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == self.settings.get_key('PLAY'):
                    self.state = GameState.PLAY
                    self.reset_game()
                    self.sound_manager.play_menu_sound('select')
                elif event.key == self.settings.get_key('HIGHSCORES'):
                    self.state = GameState.HIGHSCORES
                    self.sound_manager.play_menu_sound('select')
                elif event.key == self.settings.get_key('TOGGLE_OBSTACLES'):
                    self.obstacles_enabled = not self.obstacles_enabled
                    logging.info(f"Obstacles toggled to {'ON' if self.obstacles_enabled else 'OFF'}.")
                    self.sound_manager.play_menu_sound('move')
                elif event.key == self.settings.get_key('OPTIONS'):
                    self.state = GameState.SETTINGS
                    self.sound_manager.play_menu_sound('select')
                elif event.key == self.settings.get_key('QUIT'):
                    self.cleanup()
                    sys.exit()

        # Draw menu
        w, h = self.screen.get_size()
        if self.cell_size == 0:
            self.cell_size = min(w // self.config.GRID_COLS, h // self.config.GRID_ROWS)
            self.config.cell_size = self.cell_size
            self.renderer.update_offsets(w, h)
        self.renderer.draw_background(self.screen, w, h)
        self.renderer.draw_overlay(self.screen, w, h)

        self.renderer.draw_text(self.screen, "METAL SNAKE",
                              w//2, h//2 - 100, size=48,
                              center=True, glow=True)
        self.renderer.draw_text(self.screen, f"[{pygame.key.name(self.settings.get_key('PLAY')).upper()}] Play Game",
                              w//2, h//2 - 40, size=30, center=True)
        self.renderer.draw_text(self.screen, f"[{pygame.key.name(self.settings.get_key('HIGHSCORES')).upper()}] Highscores",
                              w//2, h//2, size=30, center=True)
        self.renderer.draw_text(self.screen,
                              f"[{pygame.key.name(self.settings.get_key('TOGGLE_OBSTACLES')).upper()}] Obstacles: {'ON' if self.obstacles_enabled else 'OFF'}",
                              w//2, h//2 + 40, size=30, center=True)
        self.renderer.draw_text(self.screen, f"[{pygame.key.name(self.settings.get_key('OPTIONS')).upper()}] Settings",
                              w//2, h//2 + 80, size=30, center=True)
        self.renderer.draw_text(self.screen, f"[{pygame.key.name(self.settings.get_key('QUIT')).upper()}] Quit",
                              w//2, h//2 + 120, size=30, center=True)

    def update_settings(self, events: List[pygame.event.Event]) -> None:
        """Handle settings state updates and rendering"""
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    # Toggle background music
                    self.sound_manager.toggle_music()
                elif event.key == pygame.K_UP:
                    # Increase music volume
                    new_volume = min(1.0, self.sound_manager.music_volume + 0.1)
                    self.sound_manager.set_music_volume(new_volume)
                elif event.key == pygame.K_DOWN:
                    # Decrease music volume
                    new_volume = max(0.0, self.sound_manager.music_volume - 0.1)
                    self.sound_manager.set_music_volume(new_volume)
                elif event.key == pygame.K_u:
                    # Increase sound effects volume
                    new_sfx_volume = min(1.0, self.sound_manager.sfx_volume + 0.1)
                    self.sound_manager.set_sfx_volume(new_sfx_volume)
                elif event.key == pygame.K_j:
                    # Decrease sound effects volume
                    new_sfx_volume = max(0.0, self.sound_manager.sfx_volume - 0.1)
                    self.sound_manager.set_sfx_volume(new_sfx_volume)
                elif event.key == self.settings.get_key('QUIT'):
                    self.state = GameState.MENU
                    self.sound_manager.play_menu_sound('select')

        # Draw settings menu
        w, h = self.screen.get_size()
        if self.cell_size == 0:
            self.cell_size = min(w // self.config.GRID_COLS, h // self.config.GRID_ROWS)
            self.config.cell_size = self.cell_size
            self.renderer.update_offsets(w, h)
        self.renderer.draw_background(self.screen, w, h)
        self.renderer.draw_overlay(self.screen, w, h, alpha=80)

        self.renderer.draw_text(self.screen, "SETTINGS",
                              w//2, 50, size=40,
                              center=True, glow=True)
        self.renderer.draw_text(self.screen, "[M] Toggle Music",
                              w//2, 150, size=30, center=True)
        self.renderer.draw_text(self.screen, "[UP] Volume Up | [DOWN] Volume Down (Music)",
                              w//2, 190, size=24, center=True)
        self.renderer.draw_text(self.screen, "[U] Volume Up | [J] Volume Down (SFX)",
                              w//2, 230, size=24, center=True)
        self.renderer.draw_text(self.screen, f"[{pygame.key.name(self.settings.get_key('QUIT')).upper()}] Return to Menu",
                              w//2, 270, size=30, center=True)
        self.renderer.draw_text(self.screen, f"Music: {'On' if pygame.mixer.music.get_busy() else 'Off'}",
                              w//2, 310, size=24, center=True)
        self.renderer.draw_text(self.screen, f"Music Volume: {int(self.sound_manager.music_volume * 100)}%",
                              w//2, 350, size=24, center=True)
        self.renderer.draw_text(self.screen, f"SFX Volume: {int(self.sound_manager.sfx_volume * 100)}%",
                              w//2, 390, size=24, center=True)

    def update_game(self, events: List[pygame.event.Event]) -> None:
        """Handle game state updates and collisions"""
        w, h = self.screen.get_size()
        if self.cell_size == 0:
            self.cell_size = min(w // self.config.GRID_COLS, h // self.config.GRID_ROWS)
            self.config.cell_size = self.cell_size
            self.renderer.update_offsets(w, h)

        # Handle input
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == self.settings.get_key('UP'):
                    self.snake.set_direction(Direction.UP)
                elif event.key == self.settings.get_key('DOWN'):
                    self.snake.set_direction(Direction.DOWN)
                elif event.key == self.settings.get_key('LEFT'):
                    self.snake.set_direction(Direction.LEFT)
                elif event.key == self.settings.get_key('RIGHT'):
                    self.snake.set_direction(Direction.RIGHT)
                elif event.key == self.settings.get_key('PAUSE'):
                    self.state = GameState.MENU
                    self.sound_manager.play_menu_sound('select')
                elif event.key == self.settings.get_key('QUIT'):
                    self.cleanup()
                    sys.exit()

        # Update game logic at fixed rate
        should_update = self.frame_count % (self.config.FPS // self.config.GAME_SPEED) == 0
        if should_update:
            self.game_tick += 1

            # Dynamic Difficulty: Increase speed every SCORE_THRESHOLD points
            if self.score > 0 and self.score % self.config.SCORE_THRESHOLD == 0:
                self.config.GAME_SPEED = min(30, self.config.GAME_SPEED + self.config.SPEED_INCREMENT)
                logging.info(f"Game speed increased to {self.config.GAME_SPEED}")

            # Move obstacles
            for obstacle in self.obstacles:
                obstacle.move()

            # Move snake and check collisions
            if not self.snake.move(self.food_pos, { (ob.x, ob.y) for ob in self.obstacles }):
                self.TEMP_SCORE = self.score
                self.TEMP_MODE = "obstacles" if self.obstacles_enabled else "classic"
                self.state = GameState.GAME_OVER
                self.sound_manager.play_game_over_sound()
                logging.info(f"Game Over! Score: {self.TEMP_SCORE}, Mode: {self.TEMP_MODE}")
                return

            # Play movement sound
            self.sound_manager.play_movement_sound(self.config.GAME_SPEED)

            # Check food collection
            head = self.snake.head_position()
            if head == self.food_pos:
                bonus = (1 + self.config.OBSTACLE_BONUS) if self.obstacles_enabled else 1
                self.score += bonus * self.score_multiplier
                px = head[0] * self.cell_size + self.cell_size//2 + self.renderer.x_offset
                py = head[1] * self.cell_size + self.cell_size//2 + self.renderer.y_offset
                self.particles.emit(px, py, self.config.PARTICLE_COUNT, (255, 0, 0))  # Red particles for food
                self.food_pos = self.get_random_position()
                self.sound_manager.play_sound('food_pickup', self.sound_manager.pickup_channel)
                logging.info(f"Food collected! New score: {self.score}")

        # Update power-ups
        self.powerup_manager.update(self)

        # Attract food towards snake's head if magnet is active
        if self.powerup_manager.magnet_active and self.food_pos:
            self.attract_food()

        # Draw game state
        self.renderer.draw_background(self.screen, w, h)
        self.renderer.draw_overlay(self.screen, w, h, alpha=50)
        self.renderer.draw_obstacles(self.screen, self.obstacles, self.cell_size, self.frame_count)
        self.renderer.draw_food(self.screen, self.food_pos[0], self.food_pos[1],
                              self.cell_size, self.frame_count)
        self.renderer.draw_powerups(self.screen, self.powerup_manager, self.cell_size, self.frame_count, self.particles)
        self.renderer.draw_snake(self.screen, self.snake.body, self.frame_count, self.snake.invincible)
        self.particles.update_and_draw(self.screen)
        # Pass score_multiplier to the renderer
        self.renderer.draw_active_powerups_status(self.screen, self.powerup_manager, self.score_multiplier, self.frame_count)
        self.renderer.draw_text(self.screen, f"Score: {self.score}", 10 + self.renderer.x_offset, 10 + self.renderer.y_offset, size=24)
        self.renderer.draw_text(self.screen, f"Multiplier: x{self.score_multiplier}", 10 + self.renderer.x_offset, 40 + self.renderer.y_offset, size=24)

    def attract_food(self) -> None:
        """
        Move the food one step closer to the snake's head to simulate magnet effect.
        Prioritize moving in the direction with the greater distance.
        """
        if not self.food_pos:
            return
        snake_head = self.snake.head_position()
        fx, fy = self.food_pos
        sx, sy = snake_head

        dx = sx - fx
        dy = sy - fy

        move_x, move_y = 0, 0
        if abs(dx) > abs(dy):
            move_x = 1 if dx > 0 else -1 if dx < 0 else 0
        else:
            move_y = 1 if dy > 0 else -1 if dy < 0 else 0

        new_food_pos = (fx + move_x, fy + move_y)

        # Check if the new position is valid
        if (new_food_pos not in self.snake.body and
            new_food_pos not in { (ob.x, ob.y) for ob in self.obstacles } and
            new_food_pos not in [pu.position() for pu in self.powerup_manager.powerups ]):
            self.food_pos = new_food_pos
            logging.info(f"Food attracted to {self.food_pos}")
        else:
            # If invalid, do not move
            pass

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
        self.renderer.draw_text(self.screen, f"[{pygame.key.name(self.settings.get_key('QUIT')).upper()}] Return to Menu",
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
