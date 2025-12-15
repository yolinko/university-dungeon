import random
import os
import math
from enum import Enum
from PIL import Image, ImageDraw


class MapType(Enum):
    DEFAULT = 0
    MAZE = 1
    OPEN = 2
    NARROW = 3


class Room:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.center = (x + w // 2, y + h // 2)
        self.cleared = False
        self.active = False
        self.visited = False
        self.doors = []
        self.door_positions = []
        self.obstacles = []
        self.spikes = []
        self.type = "NORMAL"  # NORMAL, SHOP, BOSS, START (일반, 상점, 보스, 시작)

    def intersect(self, other):
        return (
            self.x <= other.x + other.w
            and self.x + self.w >= other.x
            and self.y <= other.y + other.h
            and self.y + self.h >= other.y
        )


class DungeonGenerator:
    def __init__(self, map_width=3000, map_height=3000):
        self.map_width = map_width
        self.map_height = map_height
        self.rooms = []
        self.walls = []
        self.floors = []
        self.hallways = []
        self.doors = []
        self.spikes = []
        self.floor_texture = None
        self.hallway_texture = None
        self.full_map_image = None

        # 공간 분할
        self.chunk_size = 500
        self.chunks = {}

    def load_assets(self, renderer):
        if self.floor_texture is None:
            path = os.path.join(os.path.dirname(__file__), "assets/ui/floor_32x.png")
            self.floor_texture = renderer.load_image(path, size=(50, 50))
        if self.hallway_texture is None:
            path = os.path.join(os.path.dirname(__file__), "assets/ui/hallway_32x.png")
            self.hallway_texture = renderer.load_image(path, size=(50, 50))

    def generate(self, num_rooms=20):
        self.rooms = []
        self.walls = []
        self.floors = []
        self.hallways = []
        self.doors = []
        self.full_map_image = None

        # 맵 유형 확률 테이블
        r = random.random()
        if r < 0.4:
            self.map_type = MapType.DEFAULT
            print("Generating DEFAULT Map")
            self._generate_default(num_rooms)
        elif r < 0.6:
            self.map_type = MapType.MAZE
            print("Generating MAZE Map")
            self._generate_maze(num_rooms)
        elif r < 0.8:
            self.map_type = MapType.OPEN
            print("Generating OPEN Map")
            self._generate_open()
        else:
            self.map_type = MapType.NARROW
            print("Generating NARROW Map")
            self._generate_narrow(num_rooms)  # 좁은 맵을 위해 더 많은 방

        # 상점 방 할당
        if len(self.rooms) > 5:
            shop_candidates = self.rooms[1:-1]
            if shop_candidates:
                shop_room = random.choice(shop_candidates)
                shop_room.type = "SHOP"
                print(f"Room at {shop_room.x},{shop_room.y} is SHOP")

        self.generate_walls_from_floors()
        self.build_spatial_grid()

    def build_spatial_grid(self):
        self.chunks = {}

        def add_to_chunks(item, category, is_rect=True):
            if is_rect:
                x, y, w, h = item
            else:
                x, y, w, h = item.x, item.y, item.w, item.h

            # 시작 및 종료 청크 결정
            start_cx = int(x // self.chunk_size)
            start_cy = int(y // self.chunk_size)
            end_cx = int((x + w) // self.chunk_size)
            end_cy = int((y + h) // self.chunk_size)

            for cy in range(start_cy, end_cy + 1):
                for cx in range(start_cx, end_cx + 1):
                    if (cx, cy) not in self.chunks:
                        self.chunks[(cx, cy)] = {
                            "walls": [],
                            "floors": [],
                            "hallways": [],
                            "rooms": [],
                            "spikes": [],
                        }
                    self.chunks[(cx, cy)][category].append(item)

        for w in self.walls:
            add_to_chunks(w, "walls")

        for f in self.floors:
            pass

        for r in self.rooms:
            add_to_chunks(r, "rooms", is_rect=False)

        for h in self.hallways:
            add_to_chunks(h, "hallways")

        for s in self.spikes:
            add_to_chunks(s, "spikes")

    def _generate_default(self, num_rooms):
        for i in range(num_rooms):
            w = random.randint(600, 1000)
            h = random.randint(600, 1000)
            x = random.randint(100, self.map_width - w - 100)
            y = random.randint(100, self.map_height - h - 100)

            new_room = Room(x, y, w, h)

            failed = False
            for other in self.rooms:
                if new_room.intersect(other):
                    failed = True
                    break

            if not failed:
                self.create_room(new_room)
                if self.rooms:
                    # 이전 방과 연결
                    prev_room = self.rooms[-1]
                    self.connect_rooms(prev_room, new_room)

                # 방에 장애물 추가 (스폰 제외)
                if len(self.rooms) > 0:
                    self.add_obstacles(new_room)
                    if random.random() < 0.3:
                        self.add_spikes(new_room)

                self.rooms.append(new_room)

    def _generate_maze(self, num_rooms):
        # 그리드 기반 미로 생성
        cell_size = 300
        cols = self.map_width // cell_size
        rows = self.map_height // cell_size

        stack = []
        visited = set()

        start_cell = (cols // 2, rows // 2)
        stack.append(start_cell)
        visited.add(start_cell)

        cell_rooms = {}

        while stack:
            current = stack[-1]
            cx, cy = current

            if current not in cell_rooms and len(self.rooms) < num_rooms:
                padding = 20
                w = random.randint(cell_size // 2, cell_size - padding * 2)
                h = random.randint(cell_size // 2, cell_size - padding * 2)
                x = cx * cell_size + (cell_size - w) // 2
                y = cy * cell_size + (cell_size - h) // 2

                room = Room(x, y, w, h)
                self.create_room(room)
                self.rooms.append(room)
                cell_rooms[current] = room

                # 가끔 장애물 추가
                if random.random() < 0.3:
                    self.add_obstacles(room)
                    if random.random() < 0.3:
                        self.add_spikes(room)

            neighbors = []
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < cols and 0 <= ny < rows and (nx, ny) not in visited:
                    neighbors.append((nx, ny))

            if neighbors:
                next_cell = random.choice(neighbors)
                stack.append(next_cell)
                visited.add(next_cell)

                if len(self.rooms) >= num_rooms:
                    continue

                nx, ny = next_cell
                padding = 20
                w = random.randint(cell_size // 2, cell_size - padding * 2)
                h = random.randint(cell_size // 2, cell_size - padding * 2)
                x = nx * cell_size + (cell_size - w) // 2
                y = ny * cell_size + (cell_size - h) // 2

                next_room = Room(x, y, w, h)
                self.create_room(next_room)
                self.rooms.append(next_room)
                cell_rooms[next_cell] = next_room

                self.connect_rooms(cell_rooms[current], next_room)

            else:
                stack.pop()

    def _generate_open(self):
        num_rooms = random.randint(3, 5)

        for i in range(num_rooms):
            w = random.randint(1000, 1800)
            h = random.randint(1000, 1800)
            x = random.randint(100, self.map_width - w - 100)
            y = random.randint(100, self.map_height - h - 100)

            new_room = Room(x, y, w, h)

            failed = False
            for other in self.rooms:
                if new_room.intersect(other):
                    failed = True
                    break

            if not failed:
                self.create_room(new_room)
                if self.rooms:
                    self.connect_rooms(self.rooms[-1], new_room, wide=True)

                # 많은 장애물 추가
                self.add_obstacles(new_room, count=15)
                self.add_spikes(new_room, count=5)
                self.rooms.append(new_room)

    def _generate_narrow(self, num_rooms):
        # 많은 작은 방, 좁은 복도
        for i in range(num_rooms):
            w = random.randint(300, 600)
            h = random.randint(300, 600)
            x = random.randint(100, self.map_width - w - 100)
            y = random.randint(100, self.map_height - h - 100)

            new_room = Room(x, y, w, h)

            failed = False
            for other in self.rooms:
                if new_room.intersect(other):
                    failed = True
                    break

            if not failed:
                self.create_room(new_room)
                if self.rooms:
                    self.connect_rooms(self.rooms[-1], new_room, narrow=True)
                    # 루프를 위한 추가 연결 추가
                    if len(self.rooms) > 2 and random.random() < 0.3:
                        other = random.choice(self.rooms[:-1])
                        self.connect_rooms(other, new_room, narrow=True)

                if random.random() < 0.5:
                    self.add_obstacles(new_room, count=2)
                self.rooms.append(new_room)

    def create_room(self, room):
        self.floors.append((room.x, room.y, room.w, room.h))

    def connect_rooms(self, r1, r2, wide=False, narrow=False):
        x1, y1 = r1.center
        x2, y2 = r2.center

        tunnel_w = 100
        if wide:
            tunnel_w = 300
        if narrow:
            tunnel_w = 120
        # 수평 후 수직
        if random.random() < 0.5:
            self.create_h_tunnel(x1, x2, y1, tunnel_w)
            self.create_v_tunnel(y1, y2, x2, tunnel_w)
        else:
            self.create_v_tunnel(y1, y2, x1, tunnel_w)
            self.create_h_tunnel(x1, x2, y2, tunnel_w)

    def create_h_tunnel(self, x1, x2, y, w_tunnel=100):
        w = abs(x2 - x1) + w_tunnel
        x = min(x1, x2)
        h = w_tunnel
        self.floors.append((x, y - h // 2, w, h))
        self.hallways.append((x, y - h // 2, w, h))
        pass

    def create_v_tunnel(self, y1, y2, x, w_tunnel=100):
        h = abs(y2 - y1) + w_tunnel
        y = min(y1, y2)
        w = w_tunnel
        self.floors.append((x - w // 2, y, w, h))
        self.hallways.append((x - w // 2, y, w, h))
        pass

    def add_obstacles(self, room, count=None):
        # 방 안에 무작위 기둥이나 블록 추가
        num_obstacles = count if count is not None else random.randint(2, 6)
        for _ in range(num_obstacles):
            w = random.randint(50, 150)
            h = random.randint(50, 150)
            # 장애물이 방에 맞는지 확인
            if room.w - 200 - w <= 0 or room.h - 200 - h <= 0:
                continue

            x = random.randint(room.x + 100, room.x + room.w - 100 - w)
            y = random.randint(room.y + 100, room.y + room.h - 100 - h)

            obstacle = (x, y, w, h)
            room.obstacles.append(obstacle)
            self.walls.append(obstacle)

    def add_spikes(self, room, count=None):
        # 가시 함정 추가
        num_spikes = count if count is not None else random.randint(1, 4)
        for _ in range(num_spikes):
            w = random.randint(30, 60)
            h = random.randint(30, 60)

            # 방 범위 체크
            if room.w - 100 - w <= 0 or room.h - 100 - h <= 0:
                continue

            x = random.randint(room.x + 50, room.x + room.w - 50 - w)
            y = random.randint(room.y + 50, room.y + room.h - 50 - h)

            # 충돌 체크 (벽/장애물과 겹치지 않게)
            spike_rect = (x, y, w, h)
            overlap = False

            # 다른 장애물과 겹치는지
            for obs in room.obstacles:
                if (
                    x < obs[0] + obs[2]
                    and x + w > obs[0]
                    and y < obs[1] + obs[3]
                    and y + h > obs[1]
                ):
                    overlap = True
                    break

            if overlap:
                continue

            # 다른 가시와 겹치는지
            for s in room.spikes:
                if (
                    x < s[0] + s[2]
                    and x + w > s[0]
                    and y < s[1] + s[3]
                    and y + h > s[1]
                ):
                    overlap = True
                    break

            if overlap:
                continue

            room.spikes.append(spike_rect)
            self.spikes.append(spike_rect)

    def generate_walls_from_floors(self):
        self.grid_size = 50
        self.cols = self.map_width // self.grid_size
        self.rows = self.map_height // self.grid_size
        self.grid = [
            [1 for _ in range(self.cols)] for _ in range(self.rows)
        ]  # 1 = 벽, 0 = 바닥

        for f in self.floors:
            c1 = max(0, f[0] // self.grid_size)
            r1 = max(0, f[1] // self.grid_size)
            c2 = min(self.cols, (f[0] + f[2]) // self.grid_size)
            r2 = min(self.rows, (f[1] + f[3]) // self.grid_size)

            for i in range(r1, r2):
                for j in range(c1, c2):
                    self.grid[i][j] = 0

        for room in self.rooms:
            for obs in room.obstacles:
                c1 = obs[0] // self.grid_size
                r1 = obs[1] // self.grid_size
                c2 = (obs[0] + obs[2]) // self.grid_size
                r2 = (obs[1] + obs[3]) // self.grid_size
                for i in range(r1, r2):
                    for j in range(c1, c2):
                        if 0 <= i < self.rows and 0 <= j < self.cols:
                            self.grid[i][j] = 1

        self.walls = []
        for i in range(self.rows):
            start_col = -1
            for j in range(self.cols):
                if self.grid[i][j] == 1:
                    if start_col == -1:
                        start_col = j
                else:
                    if start_col != -1:
                        self.walls.append(
                            (
                                start_col * self.grid_size,
                                i * self.grid_size,
                                (j - start_col) * self.grid_size,
                                self.grid_size,
                            )
                        )
                        start_col = -1
            if start_col != -1:
                self.walls.append(
                    (
                        start_col * self.grid_size,
                        i * self.grid_size,
                        (self.cols - start_col) * self.grid_size,
                        self.grid_size,
                    )
                )

        for room in self.rooms:
            # 방 둘레 확인
            # 위쪽 가장자리
            r = room.y // self.grid_size
            for c in range(
                room.x // self.grid_size, (room.x + room.w) // self.grid_size
            ):
                if self.grid[r - 1][c] == 0:
                    self.add_door(c, r, room)
            # 아래쪽 가장자리
            r = (room.y + room.h) // self.grid_size
            for c in range(
                room.x // self.grid_size, (room.x + room.w) // self.grid_size
            ):
                if self.grid[r][c] == 0:
                    self.add_door(c, r - 1, room)
            # 왼쪽 가장자리
            c = room.x // self.grid_size
            for r in range(
                room.y // self.grid_size, (room.y + room.h) // self.grid_size
            ):
                if self.grid[r][c - 1] == 0:
                    self.add_door(c, r, room)
            # 오른쪽 가장자리
            c = (room.x + room.w) // self.grid_size
            for r in range(
                room.y // self.grid_size, (room.y + room.h) // self.grid_size
            ):
                if self.grid[r][c] == 0:
                    self.add_door(c - 1, r, room)

    def add_door(self, c, r, room):
        x = c * self.grid_size
        y = r * self.grid_size

        for d in room.door_positions:
            if abs(d[0] - x) < 10 and abs(d[1] - y) < 10:
                return

        room.door_positions.append((x, y, self.grid_size, self.grid_size))

    def cache_map(self, renderer):
        if self.full_map_image:
            return

        print("Caching map...")
        self.full_map_image = Image.new(
            "RGBA", (self.map_width, self.map_height), (32, 32, 32, 255)
        )
        draw = ImageDraw.Draw(self.full_map_image)

        # 복도 그리기
        if self.hallway_texture:
            tex_w, tex_h = self.hallway_texture.size
            for h in self.hallways:
                # 타일 텍스처
                cols = math.ceil(h[2] / tex_w)
                rows = math.ceil(h[3] / tex_h)
                for r in range(rows):
                    for c in range(cols):
                        px = h[0] + c * tex_w
                        py = h[1] + r * tex_h
                        # 필요한 경우 자르기
                        if px + tex_w > h[0] + h[2] or py + tex_h > h[1] + h[3]:
                            cw = min(tex_w, h[0] + h[2] - px)
                            ch = min(tex_h, h[1] + h[3] - py)
                            if cw > 0 and ch > 0:
                                crop = self.hallway_texture.crop((0, 0, cw, ch))
                                self.full_map_image.paste(crop, (px, py))
                        else:
                            self.full_map_image.paste(self.hallway_texture, (px, py))
        else:
            for h in self.hallways:
                draw.rectangle((h[0], h[1], h[0] + h[2], h[1] + h[3]), fill="#222222")

        # 방 그리기
        if self.floor_texture:
            tex_w, tex_h = self.floor_texture.size
            for room in self.rooms:
                cols = math.ceil(room.w / tex_w)
                rows = math.ceil(room.h / tex_h)
                for r in range(rows):
                    for c in range(cols):
                        px = room.x + c * tex_w
                        py = room.y + r * tex_h
                        if px + tex_w > room.x + room.w or py + tex_h > room.y + room.h:
                            cw = min(tex_w, room.x + room.w - px)
                            ch = min(tex_h, room.y + room.h - py)
                            if cw > 0 and ch > 0:
                                crop = self.floor_texture.crop((0, 0, cw, ch))
                                self.full_map_image.paste(crop, (px, py))
                        else:
                            self.full_map_image.paste(self.floor_texture, (px, py))
        else:
            for room in self.rooms:
                draw.rectangle(
                    (room.x, room.y, room.x + room.w, room.y + room.h), fill="#333333"
                )

        # 벽 그리기
        for w in self.walls:
            draw.rectangle((w[0], w[1], w[0] + w[2], w[1] + w[3]), fill="#111111")

        # 가시 그리기
        for s in self.spikes:
            # 약간 투명한 붉은색 또는 회색 스파이크 느낌
            draw.rectangle(
                (s[0], s[1], s[0] + s[2], s[1] + s[3]),
                fill="#550000",
                outline="#880000",
            )
            # X자 표시로 가시 느낌 내기
            draw.line((s[0], s[1], s[0] + s[2], s[1] + s[3]), fill="#AA0000", width=2)
            draw.line((s[0] + s[2], s[1], s[0], s[1] + s[3]), fill="#AA0000", width=2)

        print("Map cached.")

    def draw(self, renderer):
        # 캐시 존재 확인
        if self.full_map_image is None:
            self.cache_map(renderer)

        cam_x = renderer.camera.x
        cam_y = renderer.camera.y
        cam_w = renderer.camera.width
        cam_h = renderer.camera.height

        view_x = int(cam_x)
        view_y = int(cam_y)
        view_w = int(cam_w)
        view_h = int(cam_h)

        crop_x = max(0, view_x)
        crop_y = max(0, view_y)
        crop_w = min(view_w, self.map_width - crop_x)
        crop_h = min(view_h, self.map_height - crop_y)

        if crop_w <= 0 or crop_h <= 0:
            return

        region = self.full_map_image.crop(
            (crop_x, crop_y, crop_x + crop_w, crop_y + crop_h)
        )

        screen_x = crop_x
        screen_y = crop_y

        renderer.draw_image(
            region, screen_x + crop_w / 2, screen_y + crop_h / 2, anchor="center"
        )
