import os
from PIL import Image, ImageTk
import pygame


class AssetManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AssetManager, cls).__new__(cls)
            cls._instance.assets = {}
            cls._instance.sounds = {}
            cls._instance.loaded = False
            cls._instance.music_volume = 0.5
            cls._instance.sfx_volume = 0.5

            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                print("Pygame mixer initialized successfully.")
            except Exception as e:
                print(f"Failed to initialize pygame mixer: {e}")

        return cls._instance

    def load_assets(self):
        if self.loaded:
            return

        asset_dir = os.path.join(os.path.dirname(__file__), "assets")
        if not os.path.exists(asset_dir):
            print(f"Asset directory not found: {asset_dir}")
            return

        for root, dirs, files in os.walk(asset_dir):
            for filename in files:
                if filename.endswith(".png"):
                    name = os.path.splitext(filename)[0]
                    path = os.path.join(root, filename)
                    try:
                        pil_image = Image.open(path).convert("RGBA")
                        self.assets[name] = pil_image
                        print(f"Loaded asset: {name}")
                    except Exception as e:
                        print(f"Failed to load asset {filename}: {e}")

        self.loaded = True

    def load_sounds(self):
        sound_dir = os.path.join(os.path.dirname(__file__), "assets", "sounds")
        if not os.path.exists(sound_dir):
            print(f"Sound directory not found: {sound_dir}")
            return

        for filename in os.listdir(sound_dir):
            if filename.endswith(".wav") or filename.endswith(".mp3"):
                name = os.path.splitext(filename)[0]
                path = os.path.join(sound_dir, filename)
                try:
                    sound = pygame.mixer.Sound(path)
                    sound.set_volume(self.sfx_volume)
                    self.sounds[name] = sound
                    print(f"Loaded sound: {name}")
                except Exception as e:
                    print(f"Failed to load sound {filename}: {e}")

    def get_image(self, name):
        return self.assets.get(name)

    def play_sound(self, name):
        sound = self.sounds.get(name)
        if sound:
            try:
                sound.play()
            except Exception as e:
                print(f"Failed to play sound {name}: {e}")

    def play_music(self, name, loops=-1):
        sound_dir = os.path.join(os.path.dirname(__file__), "assets", "sounds")
        path = os.path.join(sound_dir, f"{name}.mp3")
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play(loops=loops)
                print(f"Playing music: {name}")
            except Exception as e:
                print(f"Failed to play music {name}: {e}")

    def set_music_volume(self, volume):
        self.music_volume = max(0.0, min(1.0, volume))
        try:
            pygame.mixer.music.set_volume(self.music_volume)
        except Exception as e:
            print(f"Failed to set music volume: {e}")

    def set_sfx_volume(self, volume):
        self.sfx_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.sfx_volume)

    def get_music_volume(self):
        return getattr(self, "music_volume", 1.0)

    def get_sfx_volume(self):
        return getattr(self, "sfx_volume", 1.0)


# 전역 접근자
def get_asset(name):
    return AssetManager().get_image(name)


def play_sound(name):
    AssetManager().play_sound(name)
