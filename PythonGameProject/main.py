import subprocess

try:
    subprocess.check_call(["pip", "install", "-r", "requirements.txt"])
    print("Successfully installed dependencies")
except Exception as e:
    print(f"Error installing dependencies: {e}")


import tkinter as tk
import time
import random
from i18n import i18n
from engine import Game, GAME_FONT
from dungeon import DungeonGenerator
from entities import Player, Enemy, Bullet, SwordSlash
from ui import RichTextRenderer, BuffCard, ShopCard, Slider, draw_tutorial
from assets import AssetManager, play_sound
from buff_system import BuffManager
from shop_system import ShopManager


class UnivGame(Game):
    def __init__(self):
        super().__init__(width=1280, height=720)
        self.root.title("Exit the University")

        # 자산 로드
        self.asset_manager = AssetManager()
        self.asset_manager.load_assets()
        self.asset_manager.load_sounds()

        # 버프 시스템
        self.buff_manager = BuffManager()

        # 상점 시스템
        self.shop_manager = ShopManager()
        self.total_play_time = 0
        self.shop_items = []
        self.shop_start_time = 0

        # 게임 상태
        self.level = 1
        self.game_over = False
        self.paused = False
        self.state = "MAIN_MENU"  # PLAYING, BUFF_SELECT, SHOP, MAIN_MENU, SETTINGS
        self.buff_options = []
        self.stage_start_time = 0
        self.stage_start_time = 0
        self.pause_start_time = 0
        self.stage_start_time = 0
        self.pause_start_time = 0
        self.buff_select_start_time = 0
        self.tutorial_btn_rect = None  # 그리기 호출에서 버튼 rect 저장
        self.previous_state = "MAIN_MENU"  # 설정 복귀용

        # 던전 생성
        self.dungeon_generator = DungeonGenerator()
        self.dungeon = None
        self.visited_floors = []

        # 엔티티
        self.player = None
        self.enemies = []
        self.bullets = []
        self.particles = []
        self.items = []
        self.texts = []

        # UI 상태
        self.show_minimap = True
        self.message_log = []
        self.message_timer = 0
        self.damage_flash_timer = 0
        self.spike_damage_timer = 0

        # 설정 UI 컴포넌트
        slider_w = 200
        slider_h = 20
        start_x = self.width / 2 - slider_w / 2
        start_y = self.height / 3 + 40

        self.bgm_slider = Slider(
            start_x,
            start_y,
            slider_w,
            slider_h,
            0.0,
            1.0,
            self.asset_manager.music_volume,
        )
        self.sfx_slider = Slider(
            start_x,
            start_y + 80,
            slider_w,
            slider_h,
            0.0,
            1.0,
            self.asset_manager.sfx_volume,
        )

        # 초기화
        # self.start_level()  # 메인 메뉴에서 시작하므로 주석 처리

        # BGM 재생
        self.asset_manager.play_music("Evil Bodega - Adam MacDougall", loops=-1)

    def start_level(self):
        print(f"Starting Level {self.level}")
        self.stage_start_time = time.time()
        self.entities = []
        self.enemies = []
        self.bullets = []
        self.particles = []
        self.items = []
        self.texts = []

        # 맵 생성
        # 레벨에 따라 방 개수 증가
        num_rooms = 15 + self.level * 2
        self.dungeon_generator.generate(num_rooms=num_rooms)
        self.dungeon = self.dungeon_generator

        # 플레이어 스폰
        start_room = self.dungeon.rooms[0]

        # 안전한 스폰 위치 찾기
        px, py = self.find_safe_spawn_pos(start_room, 32, 32)

        if self.player is None:
            self.player = Player(px, py)
            # 기본 무기 장착 (예시)
            from entities import Gun, Sword

            self.player.equip_weapon(Gun(self.player))
            self.player.equip_weapon(Sword(self.player))
        else:
            self.player.x = px
            self.player.y = py

        self.entities.append(self.player)
        self.camera.follow(self.player)

        # 적 스폰
        for room in self.dungeon.rooms[1:]:  # 첫 번째 방은 안전지대
            if room.type == "SHOP":
                continue
            self.spawn_enemies_in_room(room)

        # 레벨 시작 시 버프 선택
        self.show_buff_selection()

        # 방문한 층 기록 초기화 (미니맵용)
        self.visited_floors = []

        # 맵 캐시 초기화
        self.dungeon.full_map_image = None

    def is_position_valid(self, x, y, w, h, room):
        # 1. 맵 범위 및 그리드(벽) 확인
        corners = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
        if hasattr(self.dungeon, "grid") and self.dungeon.grid:
            for cx, cy in corners:
                gx = int(cx // self.dungeon.grid_size)
                gy = int(cy // self.dungeon.grid_size)

                # 맵 범위 체크
                if not (
                    0 <= gy < len(self.dungeon.grid)
                    and 0 <= gx < len(self.dungeon.grid[0])
                ):
                    return False

                # 벽(1)인지 확인
                if self.dungeon.grid[gy][gx] == 1:
                    return False

        # 2. 방 내부 장애물 확인
        for obs in room.obstacles:
            if (
                x < obs[0] + obs[2]
                and x + w > obs[0]
                and y < obs[1] + obs[3]
                and y + h > obs[1]
            ):
                return False

        return True

    def find_safe_spawn_pos(self, room, w, h):
        # 1. 방 중앙 시도
        cx, cy = room.center
        x, y = cx - w / 2, cy - h / 2

        if self.is_position_valid(x, y, w, h, room):
            return x, y

        # 2. 랜덤 위치 시도 (최대 30회)
        padding = 50
        for _ in range(30):
            if room.w <= padding * 2 or room.h <= padding * 2:
                break

            rx = random.randint(room.x + padding, room.x + room.w - padding - int(w))
            ry = random.randint(room.y + padding, room.y + room.h - padding - int(h))

            if self.is_position_valid(rx, ry, w, h, room):
                print(f"Safe spawn found at check {_}")
                return rx, ry

        print("Warning: Safe spawn not found, checking center fallback")
        return x, y

    def spawn_enemies_in_room(self, room):
        # 방 크기와 레벨에 따라 적 수 결정
        area = room.w * room.h
        density = (0.00005 + (self.level * 0.00001)) * 0.7  # 30% 감소
        count = int(area * density)
        count = max(1, min(count, 10))

        monster_types = ["default", "shotgun", "sniper", "spiral", "mage", "bomber"]

        for _ in range(count):
            # 스폰 위치 검증 (최대 10회 시도)
            valid_spawn = False
            mx, my = 0, 0

            for _ in range(10):
                # 방 내부 안전 영역에서 랜덤 좌표 생성
                padding = 50
                if room.w <= padding * 2 or room.h <= padding * 2:
                    break  # 방이 너무 작음

                mx = random.randint(room.x + padding, room.x + room.w - padding)
                my = random.randint(room.y + padding, room.y + room.h - padding)

                # 1. 방 안에 있는지 논리적 확인 (이미 좌표 생성에서 보장되지만 명시적 확인)
                if not (
                    room.x < mx < room.x + room.w and room.y < my < room.y + room.h
                ):
                    continue

                # 2. 벽/타일 그리드 확인 (정확도 향상)
                # 적 크기 고려 (32x32)
                corners = [(mx, my), (mx + 32, my), (mx, my + 32), (mx + 32, my + 32)]

                on_wall = False
                if hasattr(self.dungeon, "grid") and self.dungeon.grid:
                    for cx, cy in corners:
                        gx = int(cx // self.dungeon.grid_size)
                        gy = int(cy // self.dungeon.grid_size)

                        # 맵 범위 체크
                        if not (
                            0 <= gy < len(self.dungeon.grid)
                            and 0 <= gx < len(self.dungeon.grid[0])
                        ):
                            on_wall = True
                            break

                        # 벽(1)인지 확인
                        if self.dungeon.grid[gy][gx] == 1:
                            on_wall = True
                            break

                if on_wall:
                    continue

                # 3. 방 내부 장애물 확인
                overlap = False
                for obs in room.obstacles:
                    if (
                        mx < obs[0] + obs[2]
                        and mx + 32 > obs[0]
                        and my < obs[1] + obs[3]
                        and my + 32 > obs[1]
                    ):
                        overlap = True
                        break

                if not overlap:
                    valid_spawn = True
                    break

            if not valid_spawn:
                continue

            m_type = random.choice(monster_types)
            enemy = Enemy(mx, my, monster_type=m_type)

            # 레벨 스케일링
            enemy.max_hp += self.level * 2
            enemy.hp = enemy.max_hp
            enemy.damage = 1 + self.level * 0.5

            self.enemies.append(enemy)
            self.entities.append(enemy)

    def show_buff_selection(self, on_complete=None):
        self.state = "BUFF_SELECT"
        self.buff_options = self.buff_manager.get_random_buffs(3)
        self.paused = True
        self.buff_select_start_time = time.time()
        self.on_buff_select_complete = on_complete

    def select_buff(self, index):
        if 0 <= index < len(self.buff_options):
            buff = self.buff_options[index]
            self.buff_manager.apply_buff(self.player, buff)
            self.state = "PLAYING"
            self.paused = False

            # 버프 선택 시간만큼 스테이지 시작 시간을 뒤로 미룸
            buff_select_duration = time.time() - self.buff_select_start_time
            self.stage_start_time += buff_select_duration

            self.buff_options = []

            if self.on_buff_select_complete:
                callback = self.on_buff_select_complete
                self.on_buff_select_complete = None
                callback()

    def show_shop(self, on_complete=None):
        self.state = "SHOP"
        self.shop_items = self.shop_manager.get_shop_items(self.level)
        self.paused = True
        self.shop_start_time = time.time()
        self.on_shop_complete = on_complete

    def buy_item(self, index):
        if 0 <= index < len(self.shop_items):
            item = self.shop_items[index]
            if self.shop_manager.buy_item(self.player, item):
                play_sound("pickup")  # 구매 시 픽업 사운드 사용
                # 구매 후 상점에서 아이템 제거 (선택 사항이지만 게임플레이에 좋음)
                self.shop_items.pop(index)
            else:
                # 골드 부족 사운드 또는 피드백
                pass

    def skip_shop(self):
        self.state = "PLAYING"
        self.paused = False

        # 상점 이용 시간만큼 스테이지 시작 시간을 뒤로 미룸
        shop_duration = time.time() - self.shop_start_time
        self.stage_start_time += shop_duration

        if self.on_shop_complete:
            callback = self.on_shop_complete
            self.on_shop_complete = None
            callback()

    def drop_loot(self, enemy):
        # 간단한 루팅 로직
        if random.random() < 0.5:
            self.player.gold += random.randint(10, 50)

    def restart_game(self):
        self.level = 1
        self.player = None
        self.game_over = False
        self.total_play_time = 0
        self.state = "PLAYING"
        self.start_level()

    def update(self, dt):
        if self.state == "BUFF_SELECT":
            # 버프 선택 화면 입력 처리
            if self.input.mouse_pressed:
                mx, my = self.input.mouse_x, self.input.mouse_y
                # 카드 위치 계산 (draw_buff_selection과 일치해야 함)
                card_w = 200
                card_h = 300
                gap = 20
                total_w = 3 * card_w + 2 * gap
                start_x = (self.width - total_w) / 2
                start_y = (self.height - card_h) / 2

                for i in range(len(self.buff_options)):
                    x = start_x + i * (card_w + gap)
                    y = start_y
                    if x <= mx <= x + card_w and y <= my <= y + card_h:
                        self.select_buff(i)
                        break
            return

        if self.state == "SHOP":
            if self.input.mouse_pressed:
                mx, my = self.input.mouse_x, self.input.mouse_y

                # 카드 위치 (draw_shop과 일치)
                card_w = 200
                card_h = 300
                gap = 20
                total_w = (
                    len(self.shop_items) * card_w + (len(self.shop_items) - 1) * gap
                )
                start_x = (self.width - total_w) / 2
                start_y = (self.height - card_h) / 2

                # 아이템 클릭 확인
                for i in range(len(self.shop_items)):
                    x = start_x + i * (card_w + gap)
                    y = start_y
                    if x <= mx <= x + card_w and y <= my <= y + card_h:
                        self.buy_item(i)
                        self.input.mouse_pressed = (
                            False  # 한 번 클릭에 여러 번 구매 방지
                        )
                        break

                # 건너뛰기 버튼 위치 (draw_shop과 일치)
                btn_w = 150
                btn_h = 50
                btn_x = self.width / 2 - btn_w / 2
                btn_y = (self.height - card_h) / 2 + card_h + 30

                if btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h:
                    self.skip_shop()
                    self.input.mouse_pressed = False
            return

        if self.state == "MAIN_MENU":
            if self.input.mouse_pressed:
                mx, my = self.input.mouse_x, self.input.mouse_y

                # 게임 시작 버튼
                if (
                    self.width / 2 - 100 <= mx <= self.width / 2 + 100
                    and self.height / 2 <= my <= self.height / 2 + 50
                ):
                    self.state = "TUTORIAL"
                    # self.start_level() # 튜토리얼 이후로 이동됨
                    # 즉시 발사 방지
                    self.input.mouse_pressed = False

                # 설정 버튼
                elif (
                    self.width / 2 - 100 <= mx <= self.width / 2 + 100
                    and self.height / 2 + 70 <= my <= self.height / 2 + 120
                ):
                    self.state = "SETTINGS"
                    self.previous_state = "MAIN_MENU"
                    self.input.mouse_pressed = False

                # 종료 버튼
                elif (
                    self.width / 2 - 100 <= mx <= self.width / 2 + 100
                    and self.height / 2 + 140 <= my <= self.height / 2 + 190
                ):
                    self.running = False
            return

        if self.state == "SETTINGS":
            mx, my = self.input.mouse_x, self.input.mouse_y

            # 슬라이더
            new_bgm = self.bgm_slider.update(mx, my, self.input.mouse_pressed)
            if new_bgm != self.asset_manager.get_music_volume():
                self.asset_manager.set_music_volume(new_bgm)

            new_sfx = self.sfx_slider.update(mx, my, self.input.mouse_pressed)
            if new_sfx != self.asset_manager.get_sfx_volume():
                self.asset_manager.set_sfx_volume(new_sfx)

            if self.input.mouse_pressed:
                # 언어 토글
                lang_btn_w = 200
                lang_btn_h = 40
                lang_btn_x = self.width / 2 - lang_btn_w / 2
                lang_btn_y = self.sfx_slider.y + 80

                if (
                    lang_btn_x <= mx <= lang_btn_x + lang_btn_w
                    and lang_btn_y <= my <= lang_btn_y + lang_btn_h
                ):
                    new_lang = "en" if i18n.locale == "ko" else "ko"
                    i18n.set_locale(new_lang)
                    self.input.mouse_pressed = False
                    return

                # 뒤로가기 버튼
                btn_x = self.width / 2 - 100
                btn_y = self.height - 100
                if btn_x <= mx <= btn_x + 200 and btn_y <= my <= btn_y + 50:
                    self.state = self.previous_state
                    self.input.mouse_pressed = False
            return

        if self.state == "TUTORIAL":
            if self.input.mouse_pressed:
                mx, my = self.input.mouse_x, self.input.mouse_y

                # 시작 버튼 클릭 확인
                # draw_tutorial은 버튼의 (x, y, w, h)를 반환함
                if self.tutorial_btn_rect:
                    bx, by, bw, bh = self.tutorial_btn_rect
                    if bx <= mx <= bx + bw and by <= my <= by + bh:
                        self.state = "PLAYING"
                        self.start_level()
                        self.input.mouse_pressed = False
            return

        if self.input.is_key_pressed("escape"):
            self.paused = not self.paused
            self.input.keys["escape"] = False  # 소비

            if self.paused:
                self.pause_start_time = time.time()
            else:
                # 일시정지 해제 시, 정지해 있던 시간만큼 시작 시간을 뒤로 미룸
                pause_duration = time.time() - self.pause_start_time
                self.stage_start_time += pause_duration

        if self.paused:
            # 일시정지 중 설정 버튼 처리
            if self.input.mouse_pressed:
                mx, my = self.input.mouse_x, self.input.mouse_y
                # 설정 버튼 위치 (draw 함수와 일치)
                btn_w = 200
                btn_h = 50
                btn_x = self.width / 2 - btn_w / 2
                btn_y = self.height / 2 + 50  # "Paused" 텍스트는 중앙에 있음

                if btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h:
                    self.previous_state = "PLAYING"
                    self.state = "SETTINGS"
                    self.input.mouse_pressed = False

                # 종료 버튼 (일시정지 중)
                exit_btn_y = btn_y + 70
                if (
                    btn_x <= mx <= btn_x + btn_w
                    and exit_btn_y <= my <= exit_btn_y + btn_h
                ):
                    self.running = False
            return

        # 데미지 플래시 타이머 업데이트
        if self.damage_flash_timer > 0:
            self.damage_flash_timer -= dt

        if self.spike_damage_timer > 0:
            self.spike_damage_timer -= dt

        if self.game_over:
            if self.input.is_key_pressed("r"):
                self.restart_game()
            return

        if self.state == "GAME_CLEAR":
            if self.input.is_key_pressed("r"):
                self.restart_game()
            return

        # 플레이 시간 업데이트
        if self.state == "PLAYING" and not self.paused:
            self.total_play_time += dt

        # 무기 교체 입력
        if self.input.is_key_pressed("1"):
            self.player.switch_weapon(0)
        if self.input.is_key_pressed("2"):
            self.player.switch_weapon(1)

        # 플레이어 업데이트
        self.player.update(dt, self.input, self.camera, self.dungeon.walls)

        # 맵 탈출 방지
        self.player.x = max(
            0, min(self.player.x, self.dungeon.map_width - self.player.width)
        )
        self.player.y = max(
            0, min(self.player.y, self.dungeon.map_height - self.player.height)
        )

        # 가시 함정 충돌 처리
        if self.spike_damage_timer <= 0 and hasattr(self.dungeon, "spikes"):
            player_rect = self.player.get_rect()
            for s in self.dungeon.spikes:
                # s is (x, y, w, h)
                if (
                    player_rect[0] < s[0] + s[2]
                    and player_rect[0] + player_rect[2] > s[0]
                    and player_rect[1] < s[1] + s[3]
                    and player_rect[1] + player_rect[3] > s[1]
                ):

                    self.player.hp -= 10
                    play_sound("hit")
                    self.damage_flash_timer = 1.0
                    self.spike_damage_timer = 1.0  # 1초 면역

                    if self.player.hp <= 0:
                        self.player.is_dead = True
                        self.game_over = True
                        play_sound("game_over")
                    break

        # 카메라 업데이트
        self.camera.update()

        # 적 업데이트
        for enemy in self.enemies:
            projectile = enemy.update(dt, self.player, self.dungeon.walls)
            if projectile:
                if isinstance(projectile, list):
                    self.bullets.extend(projectile)
                else:
                    self.bullets.append(projectile)

        # 총알 업데이트
        for bullet in self.bullets[:]:
            bullet.update(dt, self.dungeon.walls, self.enemies)
            if bullet.is_dead:
                self.bullets.remove(bullet)
                continue

            # 충돌 처리
            if bullet.owner == "player":
                for enemy in self.enemies:
                    if not enemy.is_dead and bullet.rect_overlap(
                        bullet.get_rect(), enemy.get_rect()
                    ):
                        enemy.hp -= bullet.damage
                        bullet.is_dead = True

                        # 적 사망 처리
                        if enemy.hp <= 0:
                            enemy.is_dead = True
                            self.drop_loot(enemy)
                            play_sound("explosion")
                        else:
                            play_sound("hit")
                        break
            elif bullet.owner == "enemy":
                if not self.player.is_dashing and bullet.rect_overlap(
                    bullet.get_rect(), self.player.get_rect()
                ):
                    self.player.hp -= bullet.damage
                    bullet.is_dead = True
                    play_sound("hit")
                    if self.player.hp <= 0:
                        self.player.is_dead = True
                        self.game_over = True
                        self.game_over = True
                        play_sound("game_over")
                    else:
                        self.damage_flash_timer = 1.0  # 1초간 플래시

        if self.input.mouse_pressed:
            attack_obj = self.player.shoot(
                self.input.mouse_x, self.input.mouse_y, self.camera
            )
            if attack_obj:
                if isinstance(attack_obj, list):
                    self.bullets.extend(attack_obj)
                elif isinstance(attack_obj, SwordSlash):
                    self.entities.append(attack_obj)
                elif isinstance(attack_obj, Bullet):
                    self.bullets.append(attack_obj)

        # SwordSlash 충돌 처리 및 업데이트
        for entity in self.entities[:]:
            if isinstance(entity, SwordSlash):
                entity.update(dt, self.dungeon.walls)
                if entity.is_dead:
                    self.entities.remove(entity)
                    continue

                # 적과 충돌
                for enemy in self.enemies:
                    if not enemy.is_dead and entity.rect_overlap(
                        entity.get_rect(), enemy.get_rect()
                    ):
                        if enemy not in entity.hit_entities:
                            enemy.hp -= entity.damage
                            entity.hit_entities.append(enemy)
                            play_sound("hit")
                            if enemy.hp <= 0:
                                enemy.is_dead = True
                                self.drop_loot(enemy)

        # 죽은 적 제거
        self.enemies = [e for e in self.enemies if not e.is_dead]
        self.entities = [e for e in self.entities if not e.is_dead]

        # 레벨 클리어 체크
        if len(self.enemies) == 0 and not self.game_over and self.state == "PLAYING":

            if self.level >= 4:
                self.state = "GAME_CLEAR"
                # TODO: play_sound("game_clear") 또는 대체제
                return

            def next_level():
                self.level += 1
                self.start_level()

            def open_shop():
                self.show_shop(on_complete=next_level)

            self.show_buff_selection(on_complete=open_shop)

        # 미니맵 업데이트 (방문한 방)
        center_x = self.player.x + self.player.width / 2
        center_y = self.player.y + self.player.height / 2

        for room in self.dungeon.rooms:
            if (
                room.x <= center_x <= room.x + room.w
                and room.y <= center_y <= room.y + room.h
            ):
                if not room.visited:
                    room.visited = True
                break

    def draw(self):
        self.renderer.clear()

        if self.state == "MAIN_MENU":
            self.draw_main_menu()
            self.draw_cursor()
            return

        if self.state == "SETTINGS":
            self.draw_settings()
            self.draw_cursor()
            return

        if self.state == "TUTORIAL":
            self.tutorial_btn_rect = draw_tutorial(
                self.renderer, self.width, self.height, None
            )
            self.draw_cursor()
            return

        # 던전 그리기
        if self.dungeon:
            self.dungeon.draw(self.renderer)

        # 엔티티 그리기 (순서 변경: 총알 -> 엔티티)
        cam_x = self.camera.x
        cam_y = self.camera.y
        cam_w = self.width
        cam_h = self.height
        padding = 100  # 여유 공간

        for bullet in self.bullets:
            # 뷰포트 컬링
            if (
                bullet.x + bullet.width < cam_x - padding
                or bullet.x > cam_x + cam_w + padding
                or bullet.y + bullet.height < cam_y - padding
                or bullet.y > cam_y + cam_h + padding
            ):
                continue
            bullet.draw(self.renderer)

        for entity in self.entities:
            # 뷰포트 컬링
            if (
                entity.x + entity.width < cam_x - padding
                or entity.x > cam_x + cam_w + padding
                or entity.y + entity.height < cam_y - padding
                or entity.y > cam_y + cam_h + padding
            ):
                continue
            entity.draw(self.renderer)

        # UI 그리기
        if self.player:
            self.draw_ui()

        if self.state == "BUFF_SELECT":
            self.draw_buff_selection()
            self.draw_cursor()

        if self.state == "SHOP":
            self.draw_shop()
            self.draw_cursor()

        if self.paused and self.state == "PLAYING":
            self.renderer.draw_overlay(0, 0, self.width, self.height, "#000000", 0.5)
            self.renderer.draw_ui_text(
                self.width / 2,
                self.height / 2,
                i18n.get("ui.paused"),
                font=(GAME_FONT, 60),
                anchor="center",
            )

            # 설정 버튼
            btn_w = 200
            btn_h = 50
            btn_x = self.width / 2 - btn_w / 2
            btn_y = self.height / 2 + 50

            mx, my = self.input.mouse_x, self.input.mouse_y
            hover = btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h

            color = "#555555" if hover else "#333333"
            self.renderer.draw_ui_rect(
                btn_x, btn_y, btn_w, btn_h, color, outline="#FFFFFF", width=2
            )
            self.renderer.draw_ui_text(
                btn_x + btn_w / 2,
                btn_y + btn_h / 2,
                i18n.get("ui.settings", "Settings"),
                font=(GAME_FONT, 24),
                anchor="center",
            )

            # 종료 버튼
            btn_y += 70
            hover = btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h

            color = "#555555" if hover else "#333333"
            self.renderer.draw_ui_rect(
                btn_x, btn_y, btn_w, btn_h, color, outline="#FFFFFF", width=2
            )
            self.renderer.draw_ui_text(
                btn_x + btn_w / 2,
                btn_y + btn_h / 2,
                i18n.get("ui.exit", "Exit"),
                font=(GAME_FONT, 24),
                anchor="center",
            )

        # 데미지 플래시
        if self.damage_flash_timer > 0:
            alpha = min(0.5, self.damage_flash_timer * 0.5)  # 최대 0.5, 서서히 감소

            # 테두리만 붉게 표시 (30px)
            border = 30
            # Top
            self.renderer.draw_overlay(0, 0, self.width, border, "#FF0000", alpha)
            # Bottom
            self.renderer.draw_overlay(
                0, self.height - border, self.width, border, "#FF0000", alpha
            )
            # 왼쪽 (상단/하단 겹치지 않게)
            self.renderer.draw_overlay(
                0, border, border, self.height - 2 * border, "#FF0000", alpha
            )
            # 오른쪽
            self.renderer.draw_overlay(
                self.width - border,
                border,
                border,
                self.height - 2 * border,
                "#FF0000",
                alpha,
            )

        # 커서를 마지막에 그리기
        self.draw_cursor()

    def draw_cursor(self):
        mx, my = self.input.mouse_x, self.input.mouse_y

        # 십자선 스타일
        color = "#00FF00"
        size = 10

        # 선
        self.renderer.draw_ui_line(mx - size, my, mx + size, my, color, width=2)
        self.renderer.draw_ui_line(mx, my - size, mx, my + size, color, width=2)

        # 중앙 점
        self.renderer.draw_ui_oval(mx - 2, my - 2, 4, 4, color)

    def draw_ui(self):
        # HUD
        self.draw_stage_bar()
        self.draw_stage_bar()
        self.renderer.draw_ui_text(
            20, 20, f"{i18n.get('ui.level')}: {self.level}", font=(GAME_FONT, 20)
        )
        self.renderer.draw_ui_text(
            20,
            50,
            f"{i18n.get('ui.gold')}: {self.player.gold}",
            color="#FFD700",
            font=(GAME_FONT, 20),
        )
        self.renderer.draw_ui_text(
            20,
            80,
            f"{i18n.get('ui.enemies')}: {len(self.enemies)}",
            color="#FF0000",
            font=(GAME_FONT, 20),
        )

        # HP Bar
        bar_w = 200
        bar_h = 20
        cx = self.width / 2
        cy = self.height - 50

        pct = max(0, self.player.hp / self.player.stats["max_hp"])
        self.renderer.draw_ui_rect(cx - bar_w / 2, cy, bar_w, bar_h, "#330000")
        self.renderer.draw_ui_rect(cx - bar_w / 2, cy, bar_w * pct, bar_h, "#FF0000")
        self.renderer.draw_ui_text(
            cx,
            cy,
            f"{int(self.player.hp)}/{self.player.stats['max_hp']}",
            anchor="n",
            font=(GAME_FONT, 16),
        )

        # 대시 상태
        dash_cd = self.player.dash_cooldown_timer
        if dash_cd <= 0:
            self.renderer.draw_ui_text(
                cx,
                cy - 25,
                i18n.get("ui.dash_hint"),
                color="#00FFFF",
                anchor="s",
                font=(GAME_FONT, 18),
            )
        self.renderer.draw_ui_rect(
            cx - bar_w / 2,
            cy - 10,
            bar_w * (1 - dash_cd / self.player.stats["dash_cooldown"]),
            5,
            "#00FFFF",
        )

        # 플레이어 스탯 (왼쪽)
        stats_y = 150
        stats_y = 150
        self.renderer.draw_ui_text(
            20,
            stats_y,
            f"{i18n.get('ui.max_hp')}: {self.player.stats['max_hp']}",
            font=(GAME_FONT, 16),
        )
        self.renderer.draw_ui_text(
            20,
            stats_y + 25,
            f"{i18n.get('ui.damage')}: {self.player.stats['damage']}",
            font=(GAME_FONT, 16),
        )
        self.renderer.draw_ui_text(
            20,
            stats_y + 50,
            f"{i18n.get('ui.speed')}: {self.player.stats['speed']}",
            font=(GAME_FONT, 16),
        )

        # ESC 힌트 (왼쪽 하단)
        self.renderer.draw_ui_text(
            20,
            self.height - 30,
            i18n.get("ui.esc_hint"),
            font=(GAME_FONT, 16),
            anchor="sw",
        )

        # 무기 목록 (오른쪽 하단)
        w_list_x = self.width - 20
        w_list_y = self.height - 20

        # 스킬 상태 그리기 (무기 목록 위)
        # 무기가 차지하는 높이 계산
        weapon_font_size = 30
        weapon_line_height = 40
        weapon_list_height = len(self.player.weapons) * weapon_line_height

        # 무기 교체 힌트 (스킬 아래, 무기 위)
        hint_y = w_list_y - weapon_list_height - 10
        self.renderer.draw_ui_text(
            w_list_x,
            hint_y,
            i18n.get("ui.weapon_hint", "Switch: 1, 2"),
            color="#AAAAAA",
            font=(GAME_FONT, 24),
            anchor="se",
        )

        skill_cd = self.player.skill_cooldown_timer
        skill_text = (
            i18n.get("ui.skill_ready")
            if skill_cd <= 0
            else i18n.get("ui.skill_cooldown", time=skill_cd)
        )
        color = (
            "#FF00FF"
            if self.player.skill_active
            else ("#FFFFFF" if skill_cd <= 0 else "#888888")
        )

        # 스킬 상태 (힌트 위)
        skill_y = hint_y - 40
        self.renderer.draw_ui_text(
            w_list_x,
            skill_y,
            skill_text,
            color=color,
            font=(GAME_FONT, 20),
            anchor="se",
        )

        for i, weapon in enumerate(self.player.weapons):
            color = "#00FF00" if i == self.player.current_weapon_index else "#888888"
            text = f"{i+1}. {weapon.name}"
            self.renderer.draw_ui_text(
                w_list_x,
                w_list_y - (len(self.player.weapons) - 1 - i) * weapon_line_height,
                text,
                color=color,
                font=(GAME_FONT, weapon_font_size),
                anchor="se",
            )

        # Minimap
        if self.show_minimap:
            self.draw_minimap()

        # Game Over
        if self.game_over:
            self.renderer.draw_overlay(0, 0, self.width, self.height, "#000000", 0.7)
            self.renderer.draw_ui_text(
                self.width / 2,
                self.height / 2 - 50,
                i18n.get("ui.game_over"),
                color="#FF0000",
                font=(GAME_FONT, 60),
                anchor="center",
            )
            self.renderer.draw_ui_text(
                self.width / 2,
                self.height / 2 + 20,
                i18n.get("ui.restart"),
                color="#FFFFFF",
                font=(GAME_FONT, 30),
                anchor="center",
            )

        if self.state == "GAME_CLEAR":
            self.renderer.draw_overlay(0, 0, self.width, self.height, "#000000", 0.7)
            self.renderer.draw_ui_text(
                self.width / 2,
                self.height / 2 - 50,
                i18n.get("ui.game_clear", "Game Clear!"),
                color="#FFFF00",
                font=(GAME_FONT, 60),
                anchor="center",
            )

            minutes = int(self.total_play_time // 60)
            seconds = int(self.total_play_time % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"

            self.renderer.draw_ui_text(
                self.width / 2,
                self.height / 2 + 10,
                i18n.get("ui.total_time", time=time_str),
                color="#FFFFFF",
                font=(GAME_FONT, 30),
                anchor="center",
            )
            self.renderer.draw_ui_text(
                self.width / 2,
                self.height / 2 + 60,
                i18n.get("ui.restart"),
                color="#AAAAAA",
                font=(GAME_FONT, 24),
                anchor="center",
            )

    def draw_minimap(self):
        map_w = 200
        map_h = 200
        x = self.width - map_w - 20
        y = 20

        # 배경
        self.renderer.draw_ui_rect(
            x, y, map_w, map_h, "#000000", outline="#FFFFFF", width=2
        )

        # 스케일 계산
        scale_x = map_w / self.dungeon.map_width
        scale_y = map_h / self.dungeon.map_height
        scale = min(scale_x, scale_y)

        # 방 그리기
        # 복도 먼저 그리기 (회색)
        for h in self.dungeon.hallways:
            hx = x + h[0] * scale
            hy = y + h[1] * scale
            hw = h[2] * scale
            hh = h[3] * scale
            self.renderer.draw_ui_rect(hx, hy, hw, hh, "#444444")

        for room in self.dungeon.rooms:
            if room.visited:
                rx = x + room.x * scale
                ry = y + room.y * scale
                rw = room.w * scale
                rh = room.h * scale

                color = "#555555"
                if room == self.dungeon.rooms[0]:
                    color = "#005500"  # 시작 방
                elif room == self.dungeon.rooms[-1]:
                    color = "#550000"  # 보스/끝 방
                elif room.type == "SHOP":
                    color = "#FFFF00"  # 상점 (노란색)

                self.renderer.draw_ui_rect(rx, ry, rw, rh, color)

        # 플레이어 위치
        px = x + self.player.x * scale
        py = y + self.player.y * scale
        self.renderer.draw_ui_oval(px - 2, py - 2, 4, 4, "#00FF00")

    def draw_buff_selection(self):
        self.renderer.draw_overlay(0, 0, self.width, self.height, "#000000", 0.8)
        self.renderer.draw_ui_text(
            self.width / 2,
            100,
            i18n.get("ui.choose_buff"),
            font=(GAME_FONT, 40),
            anchor="center",
        )

        card_w = 200
        card_h = 300
        gap = 20
        total_w = 3 * card_w + 2 * gap
        start_x = (self.width - total_w) / 2

        # 최종 Y 위치
        target_y = (self.height - card_h) / 2

        # 애니메이션 파라미터
        current_time = time.time()
        elapsed_total = current_time - self.buff_select_start_time

        card_delay = 0.2  # 카드 간 딜레이
        anim_duration = 0.5  # 카드 당 팝업 애니메이션 지속 시간

        mouse_x, mouse_y = self.input.mouse_x, self.input.mouse_y

        for i, buff in enumerate(self.buff_options):
            x = start_x + i * (card_w + gap)

            # 이 카드의 애니메이션 진행도 계산
            card_start_time = i * card_delay
            t = (elapsed_total - card_start_time) / anim_duration
            t = max(0.0, min(t, 1.0))

            c1 = 1.70158
            c3 = c1 + 1
            ease_val = 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)

            # Y 위치 보간: 화면 아래에서 시작하여 target_y에서 끝남
            start_offset_y = self.height  # 아래에서 시작
            current_y = start_offset_y + (target_y - start_offset_y) * ease_val

            card = BuffCard(buff, x, current_y, card_w, card_h)

            card.update(mouse_x, mouse_y)
            card.draw(self.renderer)

    def draw_shop(self):
        card_w = 200
        card_h = 300

        self.renderer.draw_overlay(0, 0, self.width, self.height, "#000000", 0.8)
        self.renderer.draw_ui_text(
            self.width / 2,
            50,
            i18n.get("ui.shop_title", "SHOP"),  # fallback
            font=(GAME_FONT, 40),
            anchor="center",
            color="#FFD700",
        )

        # 골드 표시
        self.renderer.draw_ui_text(
            self.width / 2,
            90,
            f"{i18n.get('ui.gold')}: {self.player.gold}",
            font=(GAME_FONT, 24),
            anchor="center",
            color="#FFFF00",
        )

        if not self.shop_items:
            self.renderer.draw_ui_text(
                self.width / 2,
                self.height / 2,
                "Sold Out",
                font=(GAME_FONT, 30),
                anchor="center",
                color="#888888",
            )
        else:
            gap = 20
            total_w = len(self.shop_items) * card_w + (len(self.shop_items) - 1) * gap
            start_x = (self.width - total_w) / 2
            start_y = (self.height - card_h) / 2

            mouse_x, mouse_y = self.input.mouse_x, self.input.mouse_y

            for i, item in enumerate(self.shop_items):
                x = start_x + i * (card_w + gap)
                y = start_y

                card = ShopCard(item, x, y, card_w, card_h)
                card.update(mouse_x, mouse_y)
                card.draw(self.renderer, self.player.gold)

        # 건너뛰기 버튼
        btn_w = 150
        btn_h = 50
        btn_x = self.width / 2 - btn_w / 2
        btn_y = (self.height - card_h) / 2 + card_h + 30

        mx, my = self.input.mouse_x, self.input.mouse_y
        hover = btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h
        color = "#444444" if not hover else "#666666"

        self.renderer.draw_ui_rect(btn_x, btn_y, btn_w, btn_h, color, outline="#FFFFFF")
        self.renderer.draw_ui_text(
            self.width / 2,
            btn_y + btn_h / 2,
            i18n.get("ui.skip", "Skip"),
            font=(GAME_FONT, 24),
            anchor="center",
        )

    def draw_main_menu(self):
        self.renderer.draw_overlay(0, 0, self.width, self.height, "#000000", 1.0)

        # 제목
        self.renderer.draw_ui_text(
            self.width / 2,
            self.height / 3,
            i18n.get("ui.enter_dungeon"),
            font=(GAME_FONT, 60),
            color="#FFD700",
            anchor="center",
        )

        # 시작 버튼
        btn_x = self.width / 2 - 100
        btn_y = self.height / 2
        btn_w = 200
        btn_h = 50

        mx, my = self.input.mouse_x, self.input.mouse_y
        hover = btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h
        color = "#444444" if not hover else "#666666"

        self.renderer.draw_ui_rect(btn_x, btn_y, btn_w, btn_h, color, outline="#FFFFFF")
        self.renderer.draw_ui_text(
            self.width / 2,
            btn_y + btn_h / 2,
            i18n.get("ui.start_game"),
            font=(GAME_FONT, 24),
            anchor="center",
        )

        # 설정 버튼
        btn_y += 70
        hover = btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h
        color = "#444444" if not hover else "#666666"

        self.renderer.draw_ui_rect(btn_x, btn_y, btn_w, btn_h, color, outline="#FFFFFF")
        self.renderer.draw_ui_text(
            self.width / 2,
            btn_y + btn_h / 2,
            i18n.get("ui.settings"),
            font=(GAME_FONT, 24),
            anchor="center",
        )

        # 종료 버튼
        btn_y += 70
        hover = btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h
        color = "#444444" if not hover else "#666666"

        self.renderer.draw_ui_rect(btn_x, btn_y, btn_w, btn_h, color, outline="#FFFFFF")
        self.renderer.draw_ui_text(
            self.width / 2,
            btn_y + btn_h / 2,
            i18n.get("ui.exit", "Exit"),
            font=(GAME_FONT, 24),
            anchor="center",
        )

    def draw_settings(self):
        self.renderer.draw_overlay(0, 0, self.width, self.height, "#000000", 1.0)

        self.renderer.draw_ui_text(
            self.width / 2,
            self.height / 5,
            i18n.get("ui.settings"),
            font=(GAME_FONT, 40),
            anchor="center",
            color="#FFFFFF",
        )

        # 슬라이더 그리기
        self.bgm_slider.draw(self.renderer, i18n.get("ui.volume_bgm"))
        self.sfx_slider.draw(self.renderer, i18n.get("ui.volume_sfx"))

        # 언어 토글
        lang_btn_w = 200
        lang_btn_h = 40
        lang_btn_x = self.width / 2 - lang_btn_w / 2
        lang_btn_y = self.sfx_slider.y + 80

        mx, my = self.input.mouse_x, self.input.mouse_y
        hover = (
            lang_btn_x <= mx <= lang_btn_x + lang_btn_w
            and lang_btn_y <= my <= lang_btn_y + lang_btn_h
        )
        color = "#444444" if not hover else "#666666"

        self.renderer.draw_ui_rect(
            lang_btn_x, lang_btn_y, lang_btn_w, lang_btn_h, color, outline="#FFFFFF"
        )
        self.renderer.draw_ui_text(
            self.width / 2,
            lang_btn_y + lang_btn_h / 2,
            f"{i18n.get('ui.language')}: {i18n.locale.upper()}",
            font=(GAME_FONT, 20),
            anchor="center",
        )

        # 뒤로가기 버튼
        btn_x = self.width / 2 - 100
        btn_y = self.height - 100
        btn_w = 200
        btn_h = 50

        hover = btn_x <= mx <= btn_x + btn_w and btn_y <= my <= btn_y + btn_h
        color = "#444444" if not hover else "#666666"

        self.renderer.draw_ui_rect(btn_x, btn_y, btn_w, btn_h, color, outline="#FFFFFF")
        self.renderer.draw_ui_text(
            self.width / 2,
            btn_y + btn_h / 2,
            i18n.get("ui.back"),
            font=(GAME_FONT, 24),
            anchor="center",
        )

    def draw_stage_bar(self):
        # o-o-o-o-o (5단계 예시, 혹은 현재 레벨 표시)
        # 중앙 상단
        cx = self.width / 2
        cy = 40

        # 타이머
        elapsed = time.time() - self.stage_start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        timer_text = f"{mins:02d}:{secs:02d}"
        self.renderer.draw_ui_text(
            cx, cy - 25, timer_text, font=(GAME_FONT, 24), anchor="center"
        )

        # 스테이지 바
        # 현재 레벨을 5로 나눈 나머지 등으로 표시?
        # 그냥 5개 동그라미 그리고 현재 레벨 하이라이트

        bar_w = 200
        spacing = bar_w / 3  # 4개 스테이지 -> 3개 간격
        start_x = cx - bar_w / 2

        for i in range(4):
            x = start_x + i * spacing
            color = "#555555"
            # 현재 레벨 (1~5 순환한다고 가정하거나 그냥 계속 증가)
            # 여기서는 5개만 보여주고 현재 레벨이 채워지는 식

            # 레벨 1 -> 첫번째 o 채움
            # 레벨 2 -> 두번째 o 채움
            current_idx = (self.level - 1) % 4

            if i < current_idx:
                color = "#00FF00"  # 완료
            elif i == current_idx:
                color = "#FFFF00"  # 현재

            self.renderer.draw_ui_oval(x - 8, cy - 8, 16, 16, color)
            if i < 3:
                self.renderer.draw_ui_line(
                    x + 8, cy, x + spacing - 8, cy, "#555555", width=2
                )


if __name__ == "__main__":
    game = UnivGame()
    game.start()
