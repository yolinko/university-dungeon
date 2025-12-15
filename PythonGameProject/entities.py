import math
import json
import os
import random
from assets import get_asset, play_sound
import pygame
from i18n import i18n


MONSTER_DATA = {}
try:
    with open(os.path.join(os.path.dirname(__file__), "data/monsters.json"), "r") as f:
        MONSTER_DATA = json.load(f)
except Exception as e:
    print(f"Failed to load monster data: {e}")


PLAYER_STATS = {}
try:
    with open(
        os.path.join(os.path.dirname(__file__), "data/player_stats.json"), "r"
    ) as f:
        PLAYER_STATS = json.load(f)
except Exception as e:
    print(f"Failed to load player stats: {e}")


class Entity:
    def __init__(self, x, y, width, height, color, image_name=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.image_name = image_name
        self.vx = 0
        self.vy = 0
        self.speed = 200
        self.friction = 0.85
        self.is_dead = False
        self.animation = None

    def update(self, dt, walls):
        self.x += self.vx * dt
        self.check_collision_x(walls)
        self.y += self.vy * dt
        self.check_collision_y(walls)
        self.vx *= self.friction
        self.vy *= self.friction

        if abs(self.vx) < 1:
            self.vx = 0
        if abs(self.vy) < 1:
            self.vy = 0

        if self.animation:
            self.animation.update(dt)

    def check_collision_x(self, walls):
        # 벽과의 간단한 AABB 충돌
        my_rect = self.get_rect()
        for wall in walls:
            if self.rect_overlap(my_rect, wall):
                if self.vx > 0:
                    self.x = wall[0] - self.width
                elif self.vx < 0:
                    self.x = wall[0] + wall[2]
                self.vx = 0
                break

    def check_collision_y(self, walls):
        my_rect = self.get_rect()
        for wall in walls:
            if self.rect_overlap(my_rect, wall):
                if self.vy > 0:
                    self.y = wall[1] - self.height
                elif self.vy < 0:
                    self.y = wall[1] + wall[3]
                self.vy = 0
                break

    def get_rect(self):
        return (self.x, self.y, self.width, self.height)

    def rect_overlap(self, r1, r2):
        return not (
            r1[0] + r1[2] <= r2[0]
            or r1[0] >= r2[0] + r2[2]
            or r1[1] + r1[3] <= r2[1]
            or r1[1] >= r2[1] + r2[3]
        )

    def draw(self, renderer):
        # 그림자 그리기
        shadow_h = self.height * 0.4
        shadow_y = self.y + self.height - shadow_h * 0.7
        renderer.draw_shadow(self.x, shadow_y, self.width, shadow_h, alpha=0.3)

        renderer.draw_rect(self.x, self.y, self.width, self.height, self.color)

        if self.animation:
            frame = self.animation.get_frame()
            if frame:
                # 중앙에 그리기
                renderer.draw_image(
                    frame, self.x + self.width / 2, self.y + self.height / 2
                )
                return

        # 사용 가능한 경우 텍스처 그리기
        if self.image_name:
            img = get_asset(self.image_name)
            if img:
                renderer.draw_image(
                    img, self.x + self.width / 2, self.y + self.height / 2
                )
                return

        renderer.draw_rect(self.x, self.y, self.width, self.height, self.color)


class Weapon:
    def __init__(self, owner, cooldown):
        self.owner = owner
        self.cooldown = cooldown
        self.current_cooldown = 0

    def update(self, dt):
        if self.current_cooldown > 0:
            self.current_cooldown -= dt

    def attack(self, target_x, target_y, camera):
        raise NotImplementedError


class Gun(Weapon):
    def __init__(self, owner):
        super().__init__(owner, 0.15)  # 기본 발사 속도
        self.name = i18n.get("weapons.gun")

    def attack(self, target_x, target_y, camera):
        if self.current_cooldown > 0:
            return None

        play_sound("bullet_shoot")
        self.current_cooldown = self.owner.stats["fire_rate"]

        # 각도 계산
        center_x = self.owner.x + self.owner.width / 2
        center_y = self.owner.y + self.owner.height / 2

        world_mouse_x = target_x + camera.x
        world_mouse_y = target_y + camera.y

        angle = math.atan2(world_mouse_y - center_y, world_mouse_x - center_x)

        # 유물 및 능력치 적용
        bullets_to_fire = [angle]

        # 멀티샷
        for relic in self.owner.relics:
            if relic.effect_type == "multishot":
                if random.random() < 0.3:
                    bullets_to_fire.append(angle + 0.15)
                    bullets_to_fire.append(angle - 0.15)

        created_bullets = []
        for a in bullets_to_fire:
            b = Bullet(center_x, center_y, a, "player")

            # 총알 능력치 적용
            b.speed += self.owner.stats.get("bullet_speed", 0)
            b.vx = math.cos(a) * b.speed
            b.vy = math.sin(a) * b.speed

            size_mod = self.owner.stats.get("bullet_size", 0)
            if size_mod != 0:
                b.width += size_mod
                b.height += size_mod

            dmg = self.owner.stats["damage"]

            # 치명타 계산
            if random.random() < self.owner.stats["crit_chance"] / 100.0:
                dmg *= self.owner.stats["crit_damage"]
                b.color = "#FF00FF"  # 치명타 시 보라색

            # 데미지 계수
            if self.owner.skill_active:
                dmg *= 2

            b.damage = dmg
            b.knockback = self.owner.stats["knockback"]

            # 총알에 유물 적용
            for relic in self.owner.relics:
                if relic.effect_type == "ricochet":
                    b.bounces = relic.value
                elif relic.effect_type == "homing":
                    b.homing = True
                    b.homing_strength += relic.value
                elif relic.effect_type == "piercing":
                    b.penetration += 1
                elif relic.effect_type == "poison":
                    b.status_effects.append("poison")
                elif relic.effect_type == "freeze":
                    b.status_effects.append("freeze")
                elif relic.effect_type == "burn":
                    b.status_effects.append("burn")

            created_bullets.append(b)

        return created_bullets


class Sword(Weapon):
    def __init__(self, owner):
        super().__init__(owner, 0.5)  # 더 느린 공격 속도
        self.name = i18n.get("weapons.sword")

    def attack(self, target_x, target_y, camera):
        if self.current_cooldown > 0:
            return None

        self.current_cooldown = 0.5

        center_x = self.owner.x + self.owner.width / 2
        center_y = self.owner.y + self.owner.height / 2

        world_mouse_x = target_x + camera.x
        world_mouse_y = target_y + camera.y

        angle = math.atan2(world_mouse_y - center_y, world_mouse_x - center_x)

        # 검 베기 생성
        slash = SwordSlash(center_x, center_y, angle, self.owner)
        return slash


class SwordSlash(Entity):
    def __init__(self, x, y, angle, owner):
        super().__init__(x, y, 64, 64, "#FFFFFF", None)
        self.owner = owner
        self.base_angle = angle
        self.life = 0.2
        self.max_life = 0.2
        self.damage = owner.stats["damage"] * 1.5
        self.hit_entities = []
        self.knockback = 400
        self.penetration = 999

        # 휘두르기 메커니즘
        self.swing_arc = math.radians(360)  # 360도 휘두르기
        self.start_angle = self.base_angle
        self.end_angle = self.base_angle + self.swing_arc

    def update(self, dt, walls, enemies=None):
        self.life -= dt
        if self.life <= 0:
            self.is_dead = True
            return

        # 진행 상황에 따라 현재 각도 계산
        progress = 1.0 - (self.life / self.max_life)
        current_angle = (
            self.start_angle + (self.end_angle - self.start_angle) * progress
        )

        # 소유자를 따르고 휘두르도록 위치 업데이트
        offset = 40
        center_x = self.owner.x + self.owner.width / 2
        center_y = self.owner.y + self.owner.height / 2

        # 히트박스 중심 위치 지정
        self.x = center_x + math.cos(current_angle) * offset - self.width / 2
        self.y = center_y + math.sin(current_angle) * offset - self.height / 2

    def draw(self, renderer):
        # 그리기를 위한 현재 각도 계산
        progress = 1.0 - (self.life / self.max_life)
        current_angle = (
            self.start_angle + (self.end_angle - self.start_angle) * progress
        )

        # 검 시각 효과 그리기
        pcx = self.owner.x + self.owner.width / 2
        pcy = self.owner.y + self.owner.height / 2

        # 검 기하학
        inner_radius = 20
        outer_radius = 90

        start_x = pcx + math.cos(current_angle) * inner_radius
        start_y = pcy + math.sin(current_angle) * inner_radius

        end_x = pcx + math.cos(current_angle) * outer_radius
        end_y = pcy + math.sin(current_angle) * outer_radius

        # 칼날 그리기
        renderer.draw_line(start_x, start_y, end_x, end_y, "#FFFFFF", width=4)


class Player(Entity):

    def __init__(self, x, y, char_type="default"):
        img = "character_1"
        super().__init__(x, y, 32, 32, "#00FF00", img)
        self.char_type = char_type
        self.relics = []

        # 기본 능력치
        # 기본 능력치 로드
        self.stats = PLAYER_STATS.get("default", {}).copy()

        # 캐릭터 타입별 덮어쓰기
        type_stats = PLAYER_STATS.get(char_type, {})
        for k, v in type_stats.items():
            if k == "color":
                self.color = v
            else:
                self.stats[k] = v

        self.hp = self.stats["max_hp"]
        self.gold = 0

        self.is_dashing = False
        self.dash_timer = 0
        self.dash_cooldown_timer = 0

        self.skill_active = False
        self.skill_timer = 0
        self.skill_cooldown_timer = 0

        self.shoot_cooldown = 0

        self.weapons = []
        self.current_weapon_index = 0

        # 오디오
        self.footstep_sound = None
        self.footstep_channel = None

        self.shield_hp = 0  # 보호막 체력

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            sound_path = os.path.join(
                os.path.dirname(__file__),
                "assets/sounds/footsteps-stairs-fast-90220.mp3",
            )
            if os.path.exists(sound_path):
                self.footstep_sound = pygame.mixer.Sound(sound_path)
                self.footstep_sound.set_volume(0.5)  # 필요에 따라 볼륨 조절
            else:
                print(f"Footstep sound not found at: {sound_path}")
        except Exception as e:
            print(f"Failed to init pygame mixer or load sound: {e}")

    def draw(self, renderer):
        # 렌더링 크기 1/2로 조절
        scale_factor = 0.5

        draw_width = self.width * scale_factor
        draw_height = self.height * scale_factor

        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        # 그림자
        shadow_h = draw_height * 0.4
        visual_bottom = center_y + draw_height / 2
        shadow_y = visual_bottom - shadow_h * 0.7
        shadow_x = center_x - draw_width / 2

        renderer.draw_shadow(shadow_x, shadow_y, draw_width, shadow_h, alpha=0.3)

        # 이미지 캐싱 및 리사이징
        if self.image_name:
            if (
                not hasattr(self, "_cached_image")
                or getattr(self, "_cached_image_name", None) != self.image_name
            ):
                img = get_asset(self.image_name)
                if img:
                    target_w = int(img.width * scale_factor)
                    target_h = int(img.height * scale_factor)
                    self._cached_image = img.resize((target_w, target_h))
                    self._cached_image_name = self.image_name
                else:
                    self._cached_image = None

            if hasattr(self, "_cached_image") and self._cached_image:
                renderer.draw_image(self._cached_image, center_x, center_y)
                return

        # 이미지가 없으면 사각형 그리기
        renderer.draw_rect(
            center_x - draw_width / 2,
            center_y - draw_height / 2,
            draw_width,
            draw_height,
            self.color,
        )

    def equip_weapon(self, weapon):
        if len(self.weapons) < 2:
            self.weapons.append(weapon)

    def switch_weapon(self, index):
        if 0 <= index < len(self.weapons):
            self.current_weapon_index = index
            print(f"Switched to weapon {index + 1}")

    def update(self, dt, input_handler, camera, walls):
        # 쿨다운
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt

        # 무기 업데이트
        for weapon in self.weapons:
            weapon.update(dt)

        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= dt
        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= dt
        if self.skill_cooldown_timer > 0:
            self.skill_cooldown_timer -= dt

        if self.skill_active:
            self.skill_timer -= dt
            if self.skill_timer <= 0:
                self.skill_active = False
                print("Skill Deactivated")

        if self.is_dashing:
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.color = "#00FF00"

            # 대시 이동 (마찰 없음)
            self.x += self.vx * dt
            self.check_collision_x(walls)
            self.y += self.vy * dt
            self.check_collision_y(walls)
            return

        # 이동
        ax = 0
        ay = 0
        if input_handler.is_key_pressed("w"):
            ay -= 1
        if input_handler.is_key_pressed("s"):
            ay += 1
        if input_handler.is_key_pressed("a"):
            ax -= 1
        if input_handler.is_key_pressed("d"):
            ax += 1

        if ax != 0 and ay != 0:
            length = math.sqrt(ax * ax + ay * ay)
            ax /= length
            ay /= length

        # 속도 능력치 적용
        move_speed = self.stats["speed"]
        self.vx += ax * move_speed * 10 * dt
        self.vy += ay * move_speed * 10 * dt

        # 속도 제한
        current_speed = math.sqrt(self.vx**2 + self.vy**2)
        if current_speed > move_speed:
            scale = move_speed / current_speed
            self.vx *= scale
            self.vy *= scale

        # 대시
        if input_handler.is_key_pressed("shift_l") or input_handler.is_key_pressed(
            "shift_r"
        ):
            if self.dash_cooldown_timer <= 0 and (ax != 0 or ay != 0):
                self.start_dash(ax, ay)

        # 스킬
        if input_handler.is_key_pressed("r"):
            if self.skill_cooldown_timer <= 0:
                self.activate_skill()

        # 발소리 로직
        if self.footstep_sound:
            # 이동 중인지 확인
            is_moving = (self.vx**2 + self.vy**2) > 100

            if is_moving:
                if (
                    self.footstep_channel is None
                    or not self.footstep_channel.get_busy()
                ):
                    self.footstep_channel = self.footstep_sound.play(loops=-1)
            else:
                if (
                    self.footstep_channel is not None
                    and self.footstep_channel.get_busy()
                ):
                    self.footstep_channel.stop()

        scale = self.stats.get("size_scale", 1.0)
        target_size = 32 * scale
        if abs(self.width - target_size) > 0.1:
            self.width = target_size
            self.height = target_size

        super().update(dt, walls)

    def start_dash(self, ax, ay):
        play_sound("dash")
        self.is_dashing = True
        self.dash_timer = self.stats["dash_duration"]
        self.dash_cooldown_timer = self.stats["dash_cooldown"]
        self.vx = ax * self.stats["dash_speed"]
        self.vy = ay * self.stats["dash_speed"]
        self.color = "#00FFFF"
        self.dash_hit_entities = []

    def activate_skill(self):
        self.skill_active = True
        self.skill_timer = self.stats["skill_duration"]
        self.skill_cooldown_timer = self.stats["skill_cooldown"]
        print("Skill Activated! Damage Boost!")

    def shoot(self, target_x, target_y, camera):
        if self.is_dashing:
            return None

        if not self.weapons:
            return None

        return self.weapons[self.current_weapon_index].attack(
            target_x, target_y, camera
        )


class Bullet(Entity):
    def __init__(self, x, y, angle, owner):
        img = "proj_bullet_lead_player" if owner == "player" else "proj_bullet_enemy"
        super().__init__(x, y, 8, 8, "#FFFF00", img)
        self.owner = owner
        self.speed = 600
        self.angle = angle
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.life = 2.0  # 초
        self.damage = 1
        self.bounces = 0
        self.homing = False
        self.homing_strength = 0
        self.penetration = 0
        self.hit_entities = []
        self.knockback = 0
        self.status_effects = []

    def draw(self, renderer):
        # 이미지 캐싱 및 회전 적용
        if self.image_name:
            if (
                not hasattr(self, "_cached_image")
                or getattr(self, "_cached_image_name", None) != self.image_name
            ):
                img = get_asset(self.image_name)
                if img:
                    degrees = math.degrees(self.angle)
                    self._cached_image = img.rotate(-degrees, expand=True)
                    self._cached_image_name = self.image_name
                else:
                    self._cached_image = None

            if hasattr(self, "_cached_image") and self._cached_image:
                renderer.draw_image(
                    self._cached_image,
                    self.x + self.width / 2,
                    self.y + self.height / 2,
                )
                return

        super().draw(renderer)

    def update(self, dt, walls, enemies=None):
        # 유도 로직 - 이동 전 적용
        if (
            self.homing
            and self.homing_strength > 0
            and enemies
            and self.owner == "player"
        ):
            # 가장 가까운 적 찾기
            nearest_enemy = None
            min_dist = float("inf")

            bx = self.x + self.width / 2
            by = self.y + self.height / 2

            for enemy in enemies:
                ex = enemy.x + enemy.width / 2
                ey = enemy.y + enemy.height / 2
                dist = ((ex - bx) ** 2 + (ey - by) ** 2) ** 0.5

                if dist < min_dist:
                    min_dist = dist
                    nearest_enemy = enemy

            # 가장 가까운 적을 향해 부드럽게 조종
            if nearest_enemy and min_dist > 0:
                ex = nearest_enemy.x + nearest_enemy.width / 2
                ey = nearest_enemy.y + nearest_enemy.height / 2

                # 적 방향 계산
                dx = ex - bx
                dy = ey - by
                dist = (dx**2 + dy**2) ** 0.5

                if dist > 0:
                    dx /= dist
                    dy /= dist

                    # 현재 속도 방향 가져오기
                    current_speed = (self.vx**2 + self.vy**2) ** 0.5

                    # 약한 유도력 적용
                    homing_force = self.homing_strength * 500 * dt  # 약한 힘
                    self.vx += dx * homing_force
                    self.vy += dy * homing_force

                    # 원래 속도 유지
                    new_speed = (self.vx**2 + self.vy**2) ** 0.5
                    if new_speed > 0:
                        self.vx = (self.vx / new_speed) * current_speed
                        self.vy = (self.vy / new_speed) * current_speed

                        # 유도 시 각도 업데이트 (회전 효과를 위해)
                        self.angle = math.atan2(self.vy, self.vx)
                        # 이미지가 변경될 수 있으므로 캐시 초기화 필요할 수 있으나
                        # 현재 구현은 _cached_image_name만 체크하므로
                        # 각도가 바뀌면 이미지를 다시 생성해야 함을 인지시켜야 함.
                        # 간단히 _cached_image_name 말고 다른 플래그를 쓰거나
                        # 그냥 여기서 캐시를 날림
                        if hasattr(self, "_cached_image"):
                            delattr(self, "_cached_image")

        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

        if self.life <= 0:
            self.is_dead = True
            return

        # 벽 충돌 확인
        my_rect = self.get_rect()
        for wall in walls:
            if self.rect_overlap(my_rect, wall):
                if self.bounces > 0:
                    self.bounces -= 1
                    # 간단한 반사
                    prev_x = self.x - self.vx * dt
                    prev_y = self.y - self.vy * dt
                    if prev_x + self.width <= wall[0] or prev_x >= wall[0] + wall[2]:
                        self.vx *= -1
                    else:
                        self.vy *= -1

                    # 반사 시 각도 업데이트
                    self.angle = math.atan2(self.vy, self.vx)
                    if hasattr(self, "_cached_image"):
                        delattr(self, "_cached_image")

                else:
                    self.is_dead = True
                break


class Enemy(Entity):
    def __init__(self, x, y, monster_type="default"):
        data = MONSTER_DATA.get(monster_type, MONSTER_DATA.get("default", {}))
        w = data.get("width", 32)
        h = data.get("height", 32)
        color = data.get("color", "#FF0000")

        img = f"enemy_{monster_type}"
        super().__init__(x, y, w, h, color, img)

        self.monster_type = monster_type
        self.hp = data.get("hp", 3)
        self.max_hp = self.hp
        self.speed = data.get("speed", 100)
        self.behavior = data.get("behavior", "chase")
        self.shoot_interval = data.get("shoot_interval", 1.5)
        self.projectile_speed = data.get("projectile_speed", 300)
        self.projectile_color = data.get("projectile_color", "#FF4444")
        self.score = data.get("score", 10)

        self.shoot_timer = 0
        self.drop_chance = 0.3
        self.loot_table = [("gold", 0.7), ("health_potion", 0.2), ("power_potion", 0.1)]

        if self.behavior == "spiral":
            self.angle_offset = 0
            self.burst_count = 0
            self.max_burst = 20
            self.reloading = False
            self.reload_timer = 2.0

    def update(self, dt, player, walls):
        if self.is_dead:
            return

        if self.behavior == "spiral" and self.reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.reloading = False
                self.burst_count = 0

        # 간단한 추격 AI
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 0:
            dx /= dist
            dy /= dist

        # 행동 기반 이동
        if self.behavior == "sniper":
            # 거리 유지
            if dist < 300:
                self.vx -= dx * self.speed * 5 * dt
                self.vy -= dy * self.speed * 5 * dt
            else:
                self.vx += dx * self.speed * 5 * dt
                self.vy += dy * self.speed * 5 * dt
        else:
            self.vx += dx * self.speed * 5 * dt
            self.vy += dy * self.speed * 5 * dt

        # 속도 제한
        current_speed = math.sqrt(self.vx**2 + self.vy**2)
        if current_speed > self.speed:
            scale = self.speed / current_speed
            self.vx *= scale
            self.vy *= scale

        super().update(dt, walls)

        # 사격
        self.shoot_timer -= dt
        if self.shoot_timer <= 0 and dist < 500:  # 사거리 증가
            self.shoot_timer = self.shoot_interval
            return self.shoot(player)
        return None

    def draw(self, renderer):
        super().draw(renderer)
        # 체력 바 그리기
        if self.hp < self.max_hp:
            bar_w = self.width
            bar_h = 4
            bar_x = self.x
            bar_y = self.y - 8

            pct = max(0, self.hp / self.max_hp)

            renderer.draw_rect(bar_x, bar_y, bar_w, bar_h, "#550000")
            renderer.draw_rect(bar_x, bar_y, bar_w * pct, bar_h, "#FF0000")

    def shoot(self, player):
        if self.behavior == "shotgun":
            return self.shoot_shotgun(player)
        elif self.behavior == "spiral":
            return self.shoot_spiral(player)
        elif self.behavior == "sniper":
            return self.shoot_sniper(player)
        elif self.behavior == "mage":
            return self.shoot_mage(player)
        elif self.behavior == "bomber":
            return self.shoot_bomber(player)
        elif self.behavior == "boss_slime":
            return self.shoot_boss_slime(player)

        # 기본 사격
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        p_center_x = player.x + player.width / 2
        p_center_y = player.y + player.height / 2

        angle = math.atan2(p_center_y - center_y, p_center_x - center_x)

        b = Bullet(center_x, center_y, angle, "enemy")
        b.color = self.projectile_color
        b.speed = self.projectile_speed
        b.vx = math.cos(angle) * b.speed
        b.vy = math.sin(angle) * b.speed
        return b

    def shoot_shotgun(self, player):
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        p_center_x = player.x + player.width / 2
        p_center_y = player.y + player.height / 2
        base_angle = math.atan2(p_center_y - center_y, p_center_x - center_x)

        bullets = []
        for i in range(-1, 2):
            angle = base_angle + i * 0.2
            b = Bullet(center_x, center_y, angle, "enemy")
            b.color = self.projectile_color
            b.speed = self.projectile_speed
            b.vx = math.cos(angle) * b.speed
            b.vy = math.sin(angle) * b.speed
            bullets.append(b)
        return bullets

    def shoot_sniper(self, player):
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        p_center_x = player.x + player.width / 2
        p_center_y = player.y + player.height / 2
        angle = math.atan2(p_center_y - center_y, p_center_x - center_x)

        b = Bullet(center_x, center_y, angle, "enemy")
        b.color = self.projectile_color
        b.speed = self.projectile_speed
        b.vx = math.cos(angle) * b.speed
        b.vy = math.sin(angle) * b.speed
        b.damage = 2
        return b

    def shoot_spiral(self, player):
        if self.reloading:
            return None

        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        self.angle_offset += 0.5
        angle = self.angle_offset

        b = Bullet(center_x, center_y, angle, "enemy")
        b.color = self.projectile_color
        b.speed = self.projectile_speed
        b.vx = math.cos(angle) * b.speed
        b.vy = math.sin(angle) * b.speed

        self.burst_count += 1
        if self.burst_count >= self.max_burst:
            self.reloading = True
            self.reload_timer = 2.0

        return b

    def shoot_mage(self, player):
        ez = ExplosionZone(player.x + player.width / 2, player.y + player.height / 2)
        ez.owner = "enemy"
        ez.vx = 0
        ez.vy = 0
        return ez

    def shoot_bomber(self, player):
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        p_center_x = player.x + player.width / 2
        p_center_y = player.y + player.height / 2
        angle = math.atan2(p_center_y - center_y, p_center_x - center_x)

        b = Bullet(center_x, center_y, angle, "enemy")
        b.color = self.projectile_color
        b.width = 16
        b.height = 16
        b.speed = self.projectile_speed
        b.vx = math.cos(angle) * b.speed
        b.vy = math.sin(angle) * b.speed
        b.damage = 2
        b.is_bomb = True
        b.image_name = "proj_bomb"
        return b

    def shoot_boss_slime(self, player):
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        bullets = []
        count = 12
        for i in range(count):
            angle = (i / count) * math.pi * 2
            b = Bullet(center_x, center_y, angle, "enemy")
            b.color = self.projectile_color
            b.speed = self.projectile_speed
            b.vx = math.cos(angle) * b.speed
            b.vy = math.sin(angle) * b.speed
            bullets.append(b)
        return bullets


class Crate(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 32, 32, "#8B4513", "obj_crate")
        self.hp = 3
        self.is_dead = False
        self.loot_table = [("gold", 0.5), ("health_potion", 0.3), ("power_potion", 0.2)]

    def update(self, dt, walls):
        self.vx = 0
        self.vy = 0
        pass


class Gold(Entity):
    def __init__(self, x, y, value=10):
        super().__init__(x, y, 16, 16, "#FFD700", "item_gold")
        self.value = value
        self.life = 10.0  # 10초 후 사라짐

    def update(self, dt, walls):
        self.life -= dt
        if self.life <= 0:
            self.is_dead = True


class HealthPotion(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 16, 16, "#FF0000", "item_potion_health")
        self.life = 15.0
        self.heal_amount = 30

    def update(self, dt, walls):
        self.life -= dt
        if self.life <= 0:
            self.is_dead = True

    def draw(self, renderer):
        super().draw(renderer)
        renderer.draw_text(self.x + 8, self.y + 8, "+", "white", ("Arial", 10))


class PowerPotion(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 16, 16, "#0000FF", "item_potion_power")
        self.life = 15.0
        self.damage_boost = 5

    def update(self, dt, walls):
        self.life -= dt
        if self.life <= 0:
            self.is_dead = True

    def draw(self, renderer):
        super().draw(renderer)
        renderer.draw_text(self.x + 8, self.y + 8, "P", "white", ("Arial", 10))


class Door(Entity):
    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h, "#555555", "obj_door_open")
        self.is_closed = False
        self.is_dead = False

    def close(self):
        self.is_closed = True
        self.color = "#884400"
        self.image_name = "obj_door_closed"

    def open(self):
        self.is_closed = False
        self.color = "#555555"
        self.image_name = "obj_door_open"

    def update(self, dt, walls):
        pass

    def draw(self, renderer):
        if self.is_closed:
            renderer.draw_rect(self.x, self.y, self.width, self.height, self.color)
        else:
            super().draw(renderer)


class Relic(Entity):
    def __init__(self, x, y, name, effect_type, value=0, cost=50, description=""):
        super().__init__(x, y, 24, 24, "#0000AA", "item_relic")
        self.name = name
        self.effect_type = effect_type
        self.value = value
        self.cost = cost
        self.description = description
        self.player = None

    def update(self, dt, walls):
        pass

    def draw(self, renderer):
        super().draw(renderer)

        # 위에 아이템 이름 그리기
        renderer.draw_text(
            self.x, self.y - 35, self.name, "#FFFFFF", ("Arial", 12, "bold")
        )

        # 배경과 함께 가격 그리기
        price_text = f"${self.cost}"
        renderer.draw_rect(self.x - 5, self.y - 25, 40, 15, "#000000")
        renderer.draw_text(
            self.x + 10, self.y - 20, price_text, "#FFD700", ("Arial", 12, "bold")
        )

        # 플레이어가 근처에 있으면 설명
        renderer.draw_text(self.x + 8, self.y + 8, "R", "white", ("Arial", 14, "bold"))


class Companion(Entity):
    def __init__(self, x, y, player):
        super().__init__(x, y, 24, 24, "#00FFFF", "companion")
        self.player = player
        self.speed = 180
        self.shoot_timer = 0
        self.shoot_interval = 2.0

    def update(self, dt, walls, enemies):
        # 플레이어 따라가기
        target_x = self.player.x - 40
        target_y = self.player.y - 40

        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist > 10:
            dx /= dist
            dy /= dist
            self.vx = dx * self.speed
            self.vy = dy * self.speed
        else:
            self.vx = 0
            self.vy = 0

        super().update(dt, walls)

        # 가장 가까운 적 사격
        self.shoot_timer -= dt
        if self.shoot_timer <= 0 and enemies:
            # 가장 가까운 적 찾기
            nearest = None
            min_dist = 9999
            for e in enemies:
                d = math.sqrt((e.x - self.x) ** 2 + (e.y - self.y) ** 2)
                if d < min_dist:
                    min_dist = d
                    nearest = e

            if nearest and min_dist < 400:
                self.shoot_timer = self.shoot_interval
                return self.shoot(nearest)
        return None

    def shoot(self, target):
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        t_x = target.x + target.width / 2
        t_y = target.y + target.height / 2
        angle = math.atan2(t_y - center_y, t_x - center_x)

        b = Bullet(center_x, center_y, angle, "player")
        b.color = "#00FFFF"
        b.speed = 400
        return b


class ExplosionZone(Entity):
    def __init__(self, x, y, radius=50, delay=1.5, damage=2):
        super().__init__(x - radius, y - radius, radius * 2, radius * 2, "#550000")
        self.radius = radius
        self.timer = delay
        self.damage = damage
        self.exploded = False
        self.active_duration = 0.2
        self.is_dead = False

    def update(self, dt, walls, enemies=None):
        self.timer -= dt
        if not self.exploded:
            if self.timer <= 0:
                self.exploded = True
                self.color = "#FF0000"
        else:
            self.active_duration -= dt
            if self.active_duration <= 0:
                self.is_dead = True

    def draw(self, renderer):
        renderer.draw_oval(self.x, self.y, self.width, self.height, self.color)


class ShotgunEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "shotgun")


class SniperEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "sniper")


class SpiralEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "spiral")


class MageEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "mage")


class BomberEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "bomber")


class GhostEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "ghost")

    def check_collision_x(self, walls):
        pass

    def check_collision_y(self, walls):
        pass


class RusherEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "rusher")


class TurretEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "turret")

    def update(self, dt, player, walls):
        if self.is_dead:
            return

        # 단순 추적
        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        # 사격
        self.shoot_timer -= dt
        if self.shoot_timer <= 0 and dist < 600:
            self.shoot_timer = self.shoot_interval
            return self.shoot(player)
        return None


class Trap(Entity):
    def __init__(self, x, y, trap_type="spikes"):
        super().__init__(x, y, 32, 32, "#888888")
        self.trap_type = trap_type
        if trap_type == "spikes":
            self.color = "#AAAAAA"
            self.damage = 1

    def update(self, dt, walls):
        pass


class Barrel(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 32, 32, "#FF4400", "obj_barrel")
        self.hp = 1
        self.is_dead = False

    def update(self, dt, walls):
        pass


class Chest(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 32, 32, "#DAA520", "obj_chest")
        self.hp = 3
        self.is_dead = False
        self.opened = False
        self.loot_table = [
            ("gold", 1.0),
            ("health_potion", 0.5),
            ("power_potion", 0.3),
            ("relic", 0.1),
        ]

    def update(self, dt, walls):
        self.vx = 0
        self.vy = 0
        pass

    def draw(self, renderer):
        super().draw(renderer)

    def interact(self, game):
        if self.opened:
            return
        self.opened = True
        self.image_name = "obj_chest_open"
        self.color = "#8B4513"

        # 전리품 지급
        game.drop_loot(self)
        print("Chest Opened!")


class NPC(Entity):
    def __init__(self, x, y, name="Villager", dialog=None, player=None):
        super().__init__(x, y, 32, 32, "#FFFFFF", "npc_villager")
        self.name = name
        self.dialog_lines = dialog if dialog else ["Hello!", "Nice weather today."]
        self.current_line = 0
        self.player = player

    def update(self, dt, walls):
        pass

    def draw(self, renderer):
        super().draw(renderer)

        # 플레이어가 가까우면 말풍선 그리기
        if self.player:
            dx = self.player.x - self.x
            dy = self.player.y - self.y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < 100:
                # 말풍선
                bubble_x = self.x + self.width / 2
                bubble_y = self.y - 20
                renderer.draw_rect(bubble_x - 15, bubble_y - 15, 30, 30, "#FFFFFF")
                renderer.draw_rect(
                    bubble_x - 15,
                    bubble_y - 15,
                    30,
                    30,
                    None,
                    outline="#000000",
                    width=1,
                )
                renderer.draw_text(
                    bubble_x, bubble_y, "F", "#000000", ("Arial", 16, "bold")
                )

    def interact(self, game):
        game.start_dialog(self.name, self.dialog_lines)


class Shrine(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 40, "#9370DB", "obj_shrine")
        self.used = False
        self.buff_type = random.choice(["heal", "damage", "speed", "max_hp"])

    def update(self, dt, walls):
        pass

    def draw(self, renderer):
        color = self.color if not self.used else "#555555"
        renderer.draw_rect(self.x, self.y, self.width, self.height, color)
        if not self.used:
            renderer.draw_text(self.x + 10, self.y + 10, "?", "white", ("Arial", 20))

    def interact(self, game):
        if self.used:
            return
        self.used = True
        # 무작위 버프 적용
        if self.buff_type == "heal":
            game.player.hp = game.player.stats["max_hp"]
            print("Shrine: Full Heal!")
        elif self.buff_type == "damage":
            game.player.stats["damage"] += 5
            print("Shrine: Damage Up!")
        elif self.buff_type == "speed":
            game.player.stats["speed"] += 20
            print("Shrine: Speed Up!")
        elif self.buff_type == "max_hp":
            game.player.stats["max_hp"] += 20
            game.player.hp += 20
            print("Shrine: Max HP Up!")
