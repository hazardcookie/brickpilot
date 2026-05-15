from __future__ import annotations

from collections.abc import Callable
import math

import pyray as rl

from openpilot.system.ui.lib.application import FontWeight, MouseEvent, gui_app
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget


class BookmarkTagButton(Widget):
  TEXT_PADDING = 24
  MAX_FONT_SIZE = 58
  MIN_FONT_SIZE = 36

  def __init__(self,
               label: str,
               color: rl.Color,
               pressed_color: rl.Color,
               text_color: rl.Color,
               click_callback: Callable[[], None]) -> None:
    super().__init__()
    self._label = label
    self._color = color
    self._pressed_color = pressed_color
    self._text_color = text_color
    self.set_click_callback(click_callback)

  def _font_size(self) -> int:
    font_size = min(self.MAX_FONT_SIZE, max(self.MIN_FONT_SIZE, int(self.rect.height * 0.45)))
    while font_size > self.MIN_FONT_SIZE:
      text_size = measure_text_cached(gui_app.font(FontWeight.BOLD), self._label, font_size)
      if text_size.x <= self.rect.width - 2 * self.TEXT_PADDING:
        break
      font_size -= 2
    return font_size

  def _render(self, _) -> None:
    bg_color = self._pressed_color if self.is_pressed else self._color
    roundness = (self.rect.height / 2) / (min(self.rect.width, self.rect.height) / 2)
    rl.draw_rectangle_rounded(self.rect, roundness, 12, bg_color)

    font_size = self._font_size()
    font = gui_app.font(FontWeight.BOLD)
    text_size = measure_text_cached(font, self._label, font_size)
    text_x = self.rect.x + (self.rect.width - text_size.x) / 2
    text_y = self.rect.y + (self.rect.height - text_size.y) / 2
    rl.draw_text_ex(font, self._label, rl.Vector2(text_x, text_y), font_size, 0, self._text_color)


class BookmarkTagPrompt(Widget):
  SHOW_SECONDS = 8.0
  CONFIRMATION_SECONDS = 2.0

  # Match the large offroad/action button scale instead of tiny settings pills.
  # The rect passed into this widget is the actual onroad camera/content rect
  # (tici excludes UI_BORDER_SIZE; mici excludes SIDE_PANEL_WIDTH), so width is
  # calculated from the real drawable screen area on every layout update.
  BUTTON_SIZE = 180
  BUTTON_MIN_SIZE = 116
  BUTTON_GAP = 96
  BUTTON_MIN_GAP = 30
  EDGE_MARGIN = 36
  CONFIRMATION_HEIGHT = 160
  CONFIRMATION_EDGE_MARGIN = 50
  BOTTOM_MARGIN = 56

  ACCEL_COLOR = rl.Color(34, 177, 76, 255)
  ACCEL_PRESSED_COLOR = rl.Color(25, 135, 57, 255)
  BRAKE_COLOR = rl.Color(226, 44, 44, 255)
  BRAKE_PRESSED_COLOR = rl.Color(180, 35, 35, 255)
  STEER_COLOR = rl.Color(245, 202, 66, 255)
  STEER_PRESSED_COLOR = rl.Color(211, 169, 41, 255)
  PHEV_COLOR = rl.Color(91, 141, 239, 255)
  PHEV_PRESSED_COLOR = rl.Color(60, 105, 205, 255)
  LIGHT_TEXT_COLOR = rl.WHITE
  DARK_TEXT_COLOR = rl.Color(20, 20, 20, 255)

  GOOD_COLOR = rl.Color(142, 212, 98, 255)
  GOOD_PRESSED_COLOR = rl.Color(101, 170, 64, 255)

  TAGS: tuple[tuple[str, str | None, str, tuple[str, ...] | None, rl.Color, rl.Color, rl.Color], ...] = (
    ("Accel", "acceleration", "Accel label saved", None, ACCEL_COLOR, ACCEL_PRESSED_COLOR, LIGHT_TEXT_COLOR),
    ("Brake", "braking", "Brake label saved", None, BRAKE_COLOR, BRAKE_PRESSED_COLOR, LIGHT_TEXT_COLOR),
    ("Steer", "steering", "Steer label saved", None, STEER_COLOR, STEER_PRESSED_COLOR, DARK_TEXT_COLOR),
    ("PHEV", None, "", None, PHEV_COLOR, PHEV_PRESSED_COLOR, LIGHT_TEXT_COLOR),
    ("Good", "good", "Good label saved", ("good_normal",), GOOD_COLOR, GOOD_PRESSED_COLOR, DARK_TEXT_COLOR),
  )
  PHEV_TAGS: tuple[tuple[str, str, tuple[str, ...], rl.Color, rl.Color, rl.Color], ...] = (
    ("EV Lag", "EV lag saved", ("ev_launch_lag",), PHEV_COLOR, PHEV_PRESSED_COLOR, LIGHT_TEXT_COLOR),
    ("Engine", "Engine transition saved", ("engine_transition",), PHEV_COLOR, PHEV_PRESSED_COLOR, LIGHT_TEXT_COLOR),
    ("HEV", "HEV transition saved", ("hev_transition",), PHEV_COLOR, PHEV_PRESSED_COLOR, LIGHT_TEXT_COLOR),
    ("Regen", "Regen blend saved", ("regen_blend",), PHEV_COLOR, PHEV_PRESSED_COLOR, LIGHT_TEXT_COLOR),
    ("Blend", "Brake blend saved", ("brake_blend",), BRAKE_COLOR, BRAKE_PRESSED_COLOR, LIGHT_TEXT_COLOR),
    ("Creep", "Stop creep saved", ("stop_creep",), BRAKE_COLOR, BRAKE_PRESSED_COLOR, LIGHT_TEXT_COLOR),
    ("Lazy", "PHEV lazy saved", ("no_lead_lazy",), ACCEL_COLOR, ACCEL_PRESSED_COLOR, LIGHT_TEXT_COLOR),
    ("Good", "Good PHEV saved", ("good_phev_transition",), GOOD_COLOR, GOOD_PRESSED_COLOR, DARK_TEXT_COLOR),
  )

  def __init__(self, tag_callback: Callable[[str, int | None, tuple[str, ...] | None], None] | None):
    super().__init__()
    self._tag_callback = tag_callback
    self._bookmark_log_mono_time: int | None = None
    self._visible_until = 0.0
    self._confirmation_until = 0.0
    self._confirmation_text = ""
    self._confirmation_color = self.ACCEL_COLOR
    self._confirmation_text_color = self.LIGHT_TEXT_COLOR
    self._interacting = False
    self._button_group_rect = rl.Rectangle(0, 0, 0, 0)
    self._confirmation_rect = rl.Rectangle(0, 0, 0, 0)
    self._primary_buttons = []
    for label, reason, confirmation_text, tags, color, pressed_color, text_color in self.TAGS:
      button = self._child(
        BookmarkTagButton(
          label,
          color,
          pressed_color,
          text_color,
          click_callback=(lambda: self._show_phev_choices()) if reason is None else
          (lambda r=reason, c=confirmation_text, t=tags, bg=color, fg=text_color: self._select_reason(r, c, bg, fg, t)),
        )
      )
      self._primary_buttons.append(button)
    self._phev_buttons = []
    for label, confirmation_text, tags, color, pressed_color, text_color in self.PHEV_TAGS:
      button = self._child(
        BookmarkTagButton(
          label,
          color,
          pressed_color,
          text_color,
          click_callback=lambda c=confirmation_text, t=tags, bg=color, fg=text_color: self._select_reason("phev_context", c, bg, fg, t),
        )
      )
      self._phev_buttons.append(button)
    self._buttons = self._primary_buttons

  def show(self, bookmark_log_mono_time: int | None) -> None:
    self._bookmark_log_mono_time = bookmark_log_mono_time
    self._confirmation_until = 0.0
    self._confirmation_text = ""
    self._buttons = self._primary_buttons
    self._visible_until = rl.get_time() + self.SHOW_SECONDS

  def showing_buttons(self) -> bool:
    return rl.get_time() < self._visible_until

  def _showing_buttons(self) -> bool:
    return self.showing_buttons()

  def _showing_confirmation(self) -> bool:
    return bool(self._confirmation_text) and rl.get_time() < self._confirmation_until

  def visible(self) -> bool:
    return self._showing_buttons() or self._showing_confirmation()

  def interacting(self) -> bool:
    interacting, self._interacting = self._interacting, False
    return interacting

  def _show_phev_choices(self) -> None:
    self._interacting = True
    self._buttons = self._phev_buttons
    self._visible_until = rl.get_time() + self.SHOW_SECONDS

  def _select_reason(self, reason: str, confirmation_text: str, color: rl.Color,
                     text_color: rl.Color, tags: tuple[str, ...] | None = None) -> None:
    self._interacting = True
    if self._tag_callback:
      self._tag_callback(reason, self._bookmark_log_mono_time, tags)
    self._visible_until = 0.0
    self._confirmation_text = confirmation_text
    self._confirmation_color = color
    self._confirmation_text_color = text_color
    self._confirmation_until = rl.get_time() + self.CONFIRMATION_SECONDS

  def _update_state(self):
    if not self._showing_buttons():
      self._visible_until = 0.0
    if not self._showing_confirmation():
      self._confirmation_until = 0.0
      self._confirmation_text = ""

  def _update_layout_rects(self) -> None:
    button_count = len(self._buttons)
    if button_count == 0:
      self._button_group_rect = rl.Rectangle(0, 0, 0, 0)
      self._confirmation_rect = rl.Rectangle(0, 0, 0, 0)
      return

    columns = min(button_count, 5) if button_count <= 5 else 4
    rows = max(1, math.ceil(button_count / columns))
    available_width = max(0.0, self.rect.width - 2 * self.EDGE_MARGIN)
    gap = min(self.BUTTON_GAP, max(self.BUTTON_MIN_GAP, (available_width - columns * self.BUTTON_MIN_SIZE) / max(columns - 1, 1)))
    button_size = min(self.BUTTON_SIZE, max(0.0, (available_width - (columns - 1) * gap) / columns))
    row_gap = min(48, max(20, gap * 0.5))

    total_buttons_width = columns * button_size + (columns - 1) * gap
    total_buttons_height = rows * button_size + (rows - 1) * row_gap
    button_x = self.rect.x + (self.rect.width - total_buttons_width) / 2
    button_y = self.rect.y + self.rect.height - total_buttons_height - self.BOTTOM_MARGIN
    self._button_group_rect = rl.Rectangle(button_x, button_y, total_buttons_width, total_buttons_height)

    confirmation_width = max(0.0, self.rect.width - 2 * self.CONFIRMATION_EDGE_MARGIN)
    confirmation_x = self.rect.x + (self.rect.width - confirmation_width) / 2
    confirmation_y = self.rect.y + self.rect.height - self.CONFIRMATION_HEIGHT - self.BOTTOM_MARGIN
    self._confirmation_rect = rl.Rectangle(confirmation_x, confirmation_y, confirmation_width, self.CONFIRMATION_HEIGHT)

    for i, button in enumerate(self._buttons):
      col = i % columns
      row = i // columns
      button.set_rect(rl.Rectangle(button_x + col * (button_size + gap),
                                   button_y + row * (button_size + row_gap),
                                   button_size, button_size))

  def _handle_mouse_event(self, mouse_event: MouseEvent) -> None:
    if self._showing_buttons() and rl.check_collision_point_rec(mouse_event.pos, self._button_group_rect):
      self._interacting = True
    elif self._showing_confirmation() and rl.check_collision_point_rec(mouse_event.pos, self._confirmation_rect):
      self._interacting = True

  def _confirmation_font_size(self) -> int:
    font_size = 66
    while font_size > 46:
      text_size = measure_text_cached(gui_app.font(FontWeight.BOLD), self._confirmation_text, font_size)
      if text_size.x <= self._confirmation_rect.width - 96:
        break
      font_size -= 2
    return font_size

  def _render_confirmation(self) -> None:
    roundness = (self._confirmation_rect.height / 2) / (min(self._confirmation_rect.width, self._confirmation_rect.height) / 2)
    rl.draw_rectangle_rounded(self._confirmation_rect, roundness, 12, self._confirmation_color)

    font_size = self._confirmation_font_size()
    font = gui_app.font(FontWeight.BOLD)
    text_size = measure_text_cached(font, self._confirmation_text, font_size)
    text_x = self._confirmation_rect.x + (self._confirmation_rect.width - text_size.x) / 2
    text_y = self._confirmation_rect.y + (self._confirmation_rect.height - text_size.y) / 2
    rl.draw_text_ex(font, self._confirmation_text, rl.Vector2(text_x, text_y), font_size, 0, self._confirmation_text_color)

  def _render(self, _):
    if self._showing_buttons():
      for button in self._buttons:
        button.render()
    elif self._showing_confirmation():
      self._render_confirmation()
