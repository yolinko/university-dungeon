import re
from engine import GAME_FONT
from i18n import i18n


class RichTextRenderer:
    @staticmethod
    def parse_text(text):
        segments = []
        current_bold = False
        current_color = "white"
        color_stack = []

        tokens = re.split(r"(<b>|</b>|<color=.*?>|</color>)", text)

        for token in tokens:
            if not token:
                continue

            if token == "<b>":
                current_bold = True
            elif token == "</b>":
                current_bold = False
            elif token.startswith("<color="):
                # 색상 추출
                match = re.search(r"<color=(.*?)>", token)
                if match:
                    color_stack.append(current_color)
                    current_color = match.group(1)
            elif token == "</color>":
                if color_stack:
                    current_color = color_stack.pop()
                else:
                    current_color = "white"
            else:
                # 텍스트 내용
                segments.append(
                    {"text": token, "bold": current_bold, "color": current_color}
                )
        return segments

    @staticmethod
    def draw_rich_text(renderer, x, y, text, base_font_size=18, width_limit=200):
        segments = RichTextRenderer.parse_text(text)

        current_x = x
        current_y = y
        line_height = base_font_size + 4

        for seg in segments:
            content = seg["text"]
            bold = seg["bold"]
            color = seg["color"]

            font_spec = (
                (GAME_FONT, base_font_size, "bold")
                if bold
                else (GAME_FONT, base_font_size)
            )

            # 줄바꿈을 위해 단어로 분할
            words = content.split(" ")
            for i, word in enumerate(words):
                # 첫 번째 단어가 아니면 공백 추가
                word_to_draw = word + (" " if i < len(words) - 1 else "")

                w = renderer.measure_text(word_to_draw, font_spec)

                if current_x + w > x + width_limit:
                    current_x = x
                    current_y += line_height

                renderer.draw_ui_text(
                    current_x, current_y, word_to_draw, color, font_spec, anchor="nw"
                )
                current_x += w


class BuffCard:
    def __init__(self, buff, x, y, w, h):
        self.buff = buff
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.hovered = False

    def update(self, mouse_x, mouse_y):
        self.hovered = (
            self.x <= mouse_x <= self.x + self.w
            and self.y <= mouse_y <= self.y + self.h
        )
        return self.hovered

    def draw(self, renderer):
        # 배경
        bg_color = "#333333" if not self.hovered else "#555555"
        border_color = "#FFFFFF" if self.hovered else "#AAAAAA"

        # 카드 본문 및 테두리
        renderer.draw_ui_rect(
            self.x, self.y, self.w, self.h, bg_color, outline=border_color, width=2
        )

        # 제목
        renderer.draw_ui_text(
            self.x + self.w / 2,
            self.y + 20,
            self.buff.name,
            "#FFD700",
            (GAME_FONT, 24, "bold"),
            anchor="n",
        )

        # 아이콘, 유형
        type_text = i18n.get(f"buff_types.{self.buff.effect_type}")
        renderer.draw_ui_text(
            self.x + self.w / 2,
            self.y + 50,
            type_text,
            "#AAAAAA",
            (GAME_FONT, 15),
            anchor="n",
        )

        # 설명
        text_x = self.x + 20
        text_y = self.y + 80
        RichTextRenderer.draw_rich_text(
            renderer,
            text_x,
            text_y,
            self.buff.description,
            base_font_size=18,
            width_limit=self.w - 40,
        )


class ShopCard:

    def __init__(self, item, x, y, w, h):

        self.item = item

        self.x = x

        self.y = y

        self.w = w

        self.h = h

        self.hovered = False

    def update(self, mouse_x, mouse_y):

        self.hovered = (
            self.x <= mouse_x <= self.x + self.w
            and self.y <= mouse_y <= self.y + self.h
        )

        return self.hovered

    def draw(self, renderer, player_gold):

        # 배경

        bg_color = "#333333" if not self.hovered else "#555555"

        border_color = "#FFFFFF" if self.hovered else "#AAAAAA"

        # 구매 가능 여부

        can_afford = player_gold >= self.item.price

        price_color = "#FFD700" if can_afford else "#FF0000"

        # 구매 가능 여부

        renderer.draw_ui_rect(
            self.x, self.y, self.w, self.h, bg_color, outline=border_color, width=2
        )

        # 이름

        renderer.draw_ui_text(
            self.x + self.w / 2,
            self.y + 20,
            self.item.name,
            "#00FFFF",
            (GAME_FONT, 24, "bold"),
            anchor="n",
        )

        renderer.draw_ui_text(
            self.x + self.w / 2,
            self.y + 50,
            f"{self.item.price} G",
            price_color,
            (GAME_FONT, 20, "bold"),
            anchor="n",
        )

        text_x = self.x + 20

        text_y = self.y + 90

        RichTextRenderer.draw_rich_text(
            renderer,
            text_x,
            text_y,
            self.item.description,
            base_font_size=18,
            width_limit=self.w - 40,
        )


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


def draw_tutorial(renderer, width, height, on_start_click):
    # 배경 (반투명 검정)
    renderer.draw_overlay(0, 0, width, height, "#000000", 0.9)

    # 컨텐츠 영역
    content_w = 800
    content_h = 600
    start_x = (width - content_w) / 2
    start_y = (height - content_h) / 2

    # 제목 스타일
    title_font = (GAME_FONT, 36, "bold")
    subtitle_font = (GAME_FONT, 28, "bold")
    body_font = (GAME_FONT, 20)

    # 1. 세계관 섹션
    curr_y = start_y + 50
    renderer.draw_ui_text(
        width / 2,
        curr_y,
        i18n.get("tutorial.worldview_title"),
        "#FFD700",
        title_font,
        anchor="center",
    )

    curr_y += 60
    worldview_text = i18n.get("tutorial.worldview_content")
    # 줄바꿈 처리해서 그리기
    lines = worldview_text.split("\n")
    for line in lines:
        renderer.draw_ui_text(
            width / 2, curr_y, line, "white", body_font, anchor="center"
        )
        curr_y += 30

    # 구분선
    curr_y += 30
    renderer.draw_ui_rect(start_x + 100, curr_y, content_w - 200, 2, "#555555")

    # 2. 가이드 섹션
    curr_y += 50
    renderer.draw_ui_text(
        width / 2,
        curr_y,
        i18n.get("tutorial.guide_title"),
        "#00FFFF",
        subtitle_font,
        anchor="center",
    )

    curr_y += 50
    guide_text = i18n.get("tutorial.guide_content")

    # RichTextRenderer를 사용하여 색상이 들어간 텍스트 렌더링
    # 중앙 정렬을 위해 약간의 트릭 사용 (RichText는 기본적으로 좌측 정렬)
    # 여기서는 간단히 RichTextRenderer를 호출하되, x 위치를 조정

    # 가이드 텍스트는 줄바꿈이 있으므로 라인별로 처리
    guide_lines = guide_text.split("\n")
    guide_start_x = width / 2 - 200  # 대략적인 중앙 정렬 시도

    for line in guide_lines:
        RichTextRenderer.draw_rich_text(
            renderer, guide_start_x, curr_y, line, base_font_size=20, width_limit=500
        )
        curr_y += 30

    # 3. 시작 버튼
    btn_w = 240
    btn_h = 60
    btn_x = width / 2 - btn_w / 2
    # 텍스트와 겹치지 않게 위치 조정 (기본 위치와 텍스트 끝 위치 중 더 아래쪽 선택)
    btn_y = max(start_y + content_h - 100, curr_y + 50)

    # 마우스 호버 확인은 main.py에서 처리하거나 여기서 mouse pos를 받아야 함
    # 여기서는 그리기만 담당하고, main.py에서 좌표 체크

    renderer.draw_ui_rect(
        btn_x, btn_y, btn_w, btn_h, "#4CAF50", outline="white", width=2
    )
    renderer.draw_ui_text(
        btn_x + btn_w / 2,
        btn_y + btn_h / 2,
        i18n.get("tutorial.start_btn"),
        "white",
        (GAME_FONT, 24, "bold"),
        anchor="center",
    )

    return (btn_x, btn_y, btn_w, btn_h)
