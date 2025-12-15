class Slider:
    def __init__(self, x, y, w, h, min_val, max_val, initial_val):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.dragging = False

    def update(self, mouse_x, mouse_y, mouse_pressed):
        # 드래그 처리
        if mouse_pressed:
            if self.dragging:
                self.value = (mouse_x - self.x) / self.w * (
                    self.max_val - self.min_val
                ) + self.min_val
                self.value = max(self.min_val, min(self.max_val, self.value))
            elif (
                self.x <= mouse_x <= self.x + self.w
                and self.y - 10 <= mouse_y <= self.y + self.h + 10
            ):
                self.dragging = True
                self.value = (mouse_x - self.x) / self.w * (
                    self.max_val - self.min_val
                ) + self.min_val
                self.value = max(self.min_val, min(self.max_val, self.value))
        else:
            self.dragging = False

        return self.value

    def draw(self, renderer, label):
        # 라벨
        renderer.draw_ui_text(
            self.x, self.y - 25, label, font=(GAME_FONT, 20), color="white", anchor="nw"
        )

        # 트랙
        renderer.draw_ui_rect(self.x, self.y, self.w, self.h, "#555555")

        # 채우기
        fill_w = (self.value - self.min_val) / (self.max_val - self.min_val) * self.w
        renderer.draw_ui_rect(self.x, self.y, fill_w, self.h, "#00FF00")

        # 핸들
        handle_x = self.x + fill_w
        renderer.draw_ui_oval(handle_x - 8, self.y + self.h / 2 - 8, 16, 16, "white")
