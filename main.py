"""
main.py - BetPawa Predictor Android App (Kivy)
Developer: Sserunjogi Sharif | 0787816686
"""

import os
import sys
import threading
from datetime import datetime, timedelta

# Kivy configuration MUST happen before importing kivy widgets
os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")

import kivy
kivy.require("2.2.0")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.metrics import dp, sp

# ─── Color palette ────────────────────────────────────────────────
C_BG         = get_color_from_hex("#0D1117")   # dark background
C_CARD       = get_color_from_hex("#161B22")   # card surface
C_PRIMARY    = get_color_from_hex("#238636")   # green (BetPawa-inspired)
C_ACCENT     = get_color_from_hex("#1F6FEB")   # blue accent
C_DANGER     = get_color_from_hex("#DA3633")   # red
C_TEXT       = get_color_from_hex("#F0F6FC")   # white text
C_MUTED      = get_color_from_hex("#8B949E")   # muted grey
C_GOLD       = get_color_from_hex("#D29922")   # gold highlight
C_WIN        = get_color_from_hex("#238636")
C_DRAW       = get_color_from_hex("#D29922")
C_LOSS       = get_color_from_hex("#DA3633")
WHITE        = (1, 1, 1, 1)


def bg(widget, color, radius=0):
    """Draw a colored background on a widget."""
    with widget.canvas.before:
        Color(*color)
        if radius:
            widget._bg_rect = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
        else:
            widget._bg_rect = Rectangle(pos=widget.pos, size=widget.size)

    def update(*_):
        widget._bg_rect.pos  = widget.pos
        widget._bg_rect.size = widget.size
    widget.bind(pos=update, size=update)


def outcome_color(prediction):
    p = prediction.lower()
    if "home" in p:
        return C_WIN
    if "away" in p:
        return C_LOSS
    return C_DRAW


# ─── Screens ──────────────────────────────────────────────────────

class HomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical", spacing=0)
        bg(root, C_BG)

        # ── Header ──────────────────────────────────────────────
        header = BoxLayout(size_hint_y=None, height=dp(72), padding=[dp(16), dp(12)])
        bg(header, C_CARD)

        logo_area = BoxLayout(orientation="vertical", spacing=dp(2))
        logo_area.add_widget(Label(
            text="⚽  BetPawa Predictor",
            font_size=sp(20), bold=True, color=C_TEXT,
            halign="left", valign="middle",
            size_hint_y=None, height=dp(28),
        ))
        logo_area.add_widget(Label(
            text="AI-powered match outcome predictions",
            font_size=sp(11), color=C_MUTED,
            halign="left", valign="middle",
            size_hint_y=None, height=dp(18),
        ))
        header.add_widget(logo_area)
        root.add_widget(header)

        # ── Body ────────────────────────────────────────────────
        body = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(16))
        bg(body, C_BG)

        # Date section
        body.add_widget(Label(
            text="SELECT MATCH DATE",
            font_size=sp(11), color=C_MUTED, bold=True,
            halign="left", size_hint_y=None, height=dp(20),
            text_size=(Window.width - dp(40), None),
        ))

        date_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        self.date_input = TextInput(
            text=datetime.today().strftime("%Y-%m-%d"),
            multiline=False, font_size=sp(16), foreground_color=C_TEXT,
            background_color=C_CARD, cursor_color=C_PRIMARY,
            padding=[dp(12), dp(14)], hint_text="YYYY-MM-DD",
            hint_text_color=C_MUTED,
        )
        bg(self.date_input, C_CARD, radius=8)

        yesterday_btn = Button(
            text="Yesterday", size_hint_x=None, width=dp(90),
            font_size=sp(12), background_color=C_ACCENT,
            color=WHITE,
        )
        yesterday_btn.bind(on_press=self._set_yesterday)

        date_row.add_widget(self.date_input)
        date_row.add_widget(yesterday_btn)
        body.add_widget(date_row)

        # Quick-select buttons
        qs_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        for label, delta in [("Today", 0), ("Tomorrow", 1), ("-2 days", -2)]:
            btn = Button(text=label, font_size=sp(12), background_color=C_CARD, color=C_TEXT)
            btn.bind(on_press=lambda _, d=delta: self._quick_select(d))
            qs_row.add_widget(btn)
        body.add_widget(qs_row)

        # Predict button
        predict_btn = Button(
            text="🔮  PREDICT MATCHES",
            size_hint_y=None, height=dp(56),
            font_size=sp(16), bold=True,
            background_color=C_PRIMARY, color=WHITE,
        )
        predict_btn.bind(on_press=self._predict)
        body.add_widget(predict_btn)

        # Status label
        self.status_label = Label(
            text="", font_size=sp(13), color=C_MUTED,
            size_hint_y=None, height=dp(24),
        )
        body.add_widget(self.status_label)

        # Stats mini-card
        stats_card = BoxLayout(
            orientation="vertical", padding=dp(14), spacing=dp(6),
            size_hint_y=None, height=dp(100),
        )
        bg(stats_card, C_CARD, radius=12)
        stats_card.add_widget(Label(
            text="HOW IT WORKS", font_size=sp(10), color=C_MUTED, bold=True,
            halign="left", size_hint_y=None, height=dp(16),
        ))
        for tip in [
            "📊  XGBoost model trained on 500+ real matches",
            "🔄  Updated after each new match day",
            "⚠️  For informational purposes only",
        ]:
            stats_card.add_widget(Label(
                text=tip, font_size=sp(12), color=C_TEXT,
                halign="left", size_hint_y=None, height=dp(20),
                text_size=(Window.width - dp(68), None),
            ))
        body.add_widget(stats_card)

        body.add_widget(BoxLayout())  # spacer

        # Bottom nav
        nav = self._bottom_nav()
        root.add_widget(body)
        root.add_widget(nav)
        self.add_widget(root)

    def _set_yesterday(self, *_):
        self.date_input.text = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    def _quick_select(self, delta):
        self.date_input.text = (datetime.today() + timedelta(days=delta)).strftime("%Y-%m-%d")

    def _predict(self, *_):
        date = self.date_input.text.strip()
        self.status_label.text = "⏳  Running model…"
        self.status_label.color = C_MUTED

        def run(_):
            try:
                from predict import predict
                results = predict(date, top_n=5)
                self.manager.get_screen("results").set_results(date, results)
                Clock.schedule_once(lambda _: setattr(self.manager, "current", "results"))
                Clock.schedule_once(lambda _: setattr(self.status_label, "text", ""))
            except Exception as e:
                Clock.schedule_once(lambda _: setattr(self.status_label, "text", f"Error: {e}"))
                Clock.schedule_once(lambda _: setattr(self.status_label, "color", C_DANGER))

        threading.Thread(target=run, daemon=True).start(None)

    def _bottom_nav(self):
        nav = BoxLayout(size_hint_y=None, height=dp(60), spacing=1)
        bg(nav, C_CARD)
        for icon, label, screen in [
            ("🏠", "Home",    "home"),
            ("📊", "History", "history"),
            ("ℹ️",  "About",   "about"),
        ]:
            btn = Button(
                text=f"{icon}\n{label}", font_size=sp(10),
                background_color=C_CARD if screen != "home" else C_PRIMARY,
                color=WHITE, halign="center",
            )
            btn.bind(on_press=lambda _, s=screen: setattr(self.manager, "current", s))
            nav.add_widget(btn)
        return nav


class ResultsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.root_layout = BoxLayout(orientation="vertical")
        bg(self.root_layout, C_BG)
        self.add_widget(self.root_layout)

    def set_results(self, date, results):
        self.root_layout.clear_widgets()

        # Header
        header = BoxLayout(size_hint_y=None, height=dp(60), padding=[dp(16), dp(10)])
        bg(header, C_CARD)
        back_btn = Button(
            text="← Back", size_hint_x=None, width=dp(80),
            font_size=sp(13), background_color=C_CARD, color=C_ACCENT,
        )
        back_btn.bind(on_press=lambda _: setattr(self.manager, "current", "home"))
        header.add_widget(back_btn)
        header.add_widget(Label(
            text=f"Predictions  ·  {date}",
            font_size=sp(15), bold=True, color=C_TEXT,
        ))
        self.root_layout.add_widget(header)

        # Scroll area
        scroll = ScrollView()
        cards  = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10),
                           size_hint_y=None)
        cards.bind(minimum_height=cards.setter("height"))

        if not results or "error" in results[0]:
            lbl = Label(text="No predictions available.\nTry running the full pipeline.",
                        color=C_MUTED, font_size=sp(14), halign="center")
            cards.add_widget(lbl)
        else:
            for i, p in enumerate(results, 1):
                card = self._match_card(i, p)
                cards.add_widget(card)

        # Disclaimer
        cards.add_widget(Label(
            text="⚠️  Predictions are informational only.\n"
                 "Bet responsibly. Past performance ≠ future results.",
            font_size=sp(11), color=C_MUTED,
            halign="center", size_hint_y=None, height=dp(48),
            text_size=(Window.width - dp(24), None),
        ))

        scroll.add_widget(cards)
        self.root_layout.add_widget(scroll)

    def _match_card(self, n, p):
        card = BoxLayout(
            orientation="vertical", padding=dp(14), spacing=dp(8),
            size_hint_y=None, height=dp(148),
        )
        bg(card, C_CARD, radius=12)

        # Teams row
        teams_row = BoxLayout(size_hint_y=None, height=dp(32))
        teams_row.add_widget(Label(
            text=p["home"], font_size=sp(14), bold=True, color=C_TEXT,
            halign="center",
        ))
        teams_row.add_widget(Label(
            text="VS", font_size=sp(11), color=C_MUTED,
            size_hint_x=None, width=dp(36), halign="center",
        ))
        teams_row.add_widget(Label(
            text=p["away"], font_size=sp(14), bold=True, color=C_TEXT,
            halign="center",
        ))
        card.add_widget(teams_row)

        # Prediction badge
        badge_row = BoxLayout(size_hint_y=None, height=dp(36))
        badge_row.add_widget(BoxLayout())  # spacer
        badge = Label(
            text=f"  {p['prediction'].upper()}  ",
            font_size=sp(13), bold=True, color=WHITE,
            size_hint_x=None, width=dp(130),
        )
        bg(badge, outcome_color(p["prediction"]), radius=16)
        badge_row.add_widget(badge)
        badge_row.add_widget(BoxLayout())
        card.add_widget(badge_row)

        # Probabilities bar
        proba_row = BoxLayout(size_hint_y=None, height=dp(20), spacing=dp(4))
        for label, val, color in [
            (f"H {p.get('proba_home','?')}", float(p.get('proba_home','33%').rstrip('%'))/100, C_WIN),
            (f"D {p.get('proba_draw','?')}",  float(p.get('proba_draw','27%').rstrip('%'))/100,  C_DRAW),
            (f"A {p.get('proba_away','?')}",  float(p.get('proba_away','33%').rstrip('%'))/100,  C_LOSS),
        ]:
            seg = Label(text=label, font_size=sp(10), color=WHITE,
                        size_hint_x=max(val, 0.15), halign="center")
            bg(seg, color)
            proba_row.add_widget(seg)
        card.add_widget(proba_row)

        # Confidence + odds
        meta_row = BoxLayout(size_hint_y=None, height=dp(20))
        meta_row.add_widget(Label(
            text=f"Confidence: {p.get('confidence','?')}",
            font_size=sp(12), color=C_MUTED, halign="left",
            text_size=(dp(160), None),
        ))
        meta_row.add_widget(Label(
            text=f"Odds hint: {p.get('odds_hint','?')}",
            font_size=sp(12), color=C_GOLD, halign="right",
            text_size=(dp(160), None),
        ))
        card.add_widget(meta_row)

        return card


class HistoryScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        bg(root, C_BG)

        header = BoxLayout(size_hint_y=None, height=dp(60), padding=[dp(16), dp(12)])
        bg(header, C_CARD)
        header.add_widget(Label(
            text="📊  Prediction History",
            font_size=sp(18), bold=True, color=C_TEXT,
            halign="left",
        ))
        root.add_widget(header)

        body = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(12))
        body.add_widget(Label(
            text="History will appear here after\nyour first prediction run.\n\n"
                 "Run the pipeline to populate:\n"
                 "  1. python scraper.py\n"
                 "  2. python clean.py\n"
                 "  3. python train.py\n"
                 "  4. Launch app & predict",
            font_size=sp(14), color=C_MUTED,
            halign="center", valign="middle",
        ))
        body.add_widget(BoxLayout())

        nav = self._bottom_nav()
        root.add_widget(body)
        root.add_widget(nav)
        self.add_widget(root)

    def _bottom_nav(self):
        nav = BoxLayout(size_hint_y=None, height=dp(60), spacing=1)
        bg(nav, C_CARD)
        for icon, label, screen in [
            ("🏠", "Home",    "home"),
            ("📊", "History", "history"),
            ("ℹ️",  "About",   "about"),
        ]:
            btn = Button(
                text=f"{icon}\n{label}", font_size=sp(10),
                background_color=C_PRIMARY if screen == "history" else C_CARD,
                color=WHITE, halign="center",
            )
            btn.bind(on_press=lambda _, s=screen: setattr(self.manager, "current", s))
            nav.add_widget(btn)
        return nav


class AboutScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        bg(root, C_BG)

        header = BoxLayout(size_hint_y=None, height=dp(60), padding=[dp(16), dp(12)])
        bg(header, C_CARD)
        header.add_widget(Label(
            text="ℹ️  About",
            font_size=sp(18), bold=True, color=C_TEXT, halign="left",
        ))
        root.add_widget(header)

        scroll = ScrollView()
        body = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(16),
                         size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))

        # App info card
        app_card = BoxLayout(
            orientation="vertical", padding=dp(16), spacing=dp(10),
            size_hint_y=None, height=dp(130),
        )
        bg(app_card, C_CARD, radius=12)
        app_card.add_widget(Label(
            text="⚽  BetPawa Predictor",
            font_size=sp(20), bold=True, color=C_PRIMARY,
            halign="center", size_hint_y=None, height=dp(30),
        ))
        app_card.add_widget(Label(
            text="Version 1.0.0  ·  AI-Powered Football Predictions",
            font_size=sp(12), color=C_MUTED, halign="center",
            size_hint_y=None, height=dp(20),
        ))
        app_card.add_widget(Label(
            text="Powered by XGBoost Machine Learning\nTrained on 500+ historical match results",
            font_size=sp(12), color=C_TEXT, halign="center",
            size_hint_y=None, height=dp(40),
        ))
        body.add_widget(app_card)

        # Developer card
        dev_card = BoxLayout(
            orientation="vertical", padding=dp(16), spacing=dp(8),
            size_hint_y=None, height=dp(180),
        )
        bg(dev_card, C_CARD, radius=12)
        dev_card.add_widget(Label(
            text="👨‍💻  DEVELOPER",
            font_size=sp(11), color=C_MUTED, bold=True,
            halign="left", size_hint_y=None, height=dp(20),
        ))

        for field, value in [
            ("Name",     "Sserunjogi Sharif"),
            ("Phone",    "0787816686"),
            ("Password", "Teenaged10@"),
            ("GitHub",   "Sharif123-cloud"),
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
            row.add_widget(Label(
                text=field, font_size=sp(12), color=C_MUTED,
                size_hint_x=None, width=dp(80), halign="right",
                text_size=(dp(80), None),
            ))
            row.add_widget(Label(
                text=value, font_size=sp(13), bold=True, color=C_TEXT,
                halign="left", text_size=(Window.width - dp(120), None),
            ))
            dev_card.add_widget(row)
        body.add_widget(dev_card)

        # Disclaimer card
        disc_card = BoxLayout(
            orientation="vertical", padding=dp(16), spacing=dp(6),
            size_hint_y=None, height=dp(120),
        )
        bg(disc_card, C_CARD, radius=12)
        disc_card.add_widget(Label(
            text="⚠️  DISCLAIMER",
            font_size=sp(11), color=C_DANGER, bold=True,
            halign="left", size_hint_y=None, height=dp(20),
        ))
        disc_card.add_widget(Label(
            text="This app provides statistical predictions for\n"
                 "informational purposes only. It does not guarantee\n"
                 "outcomes. Gamble responsibly. Must be 18+.\n"
                 "The developer is not liable for financial losses.",
            font_size=sp(11), color=C_MUTED, halign="left",
            text_size=(Window.width - dp(52), None),
            size_hint_y=None, height=dp(72),
        ))
        body.add_widget(disc_card)

        scroll.add_widget(body)
        nav = self._bottom_nav()
        root.add_widget(scroll)
        root.add_widget(nav)
        self.add_widget(root)

    def _bottom_nav(self):
        nav = BoxLayout(size_hint_y=None, height=dp(60), spacing=1)
        bg(nav, C_CARD)
        for icon, label, screen in [
            ("🏠", "Home",    "home"),
            ("📊", "History", "history"),
            ("ℹ️",  "About",   "about"),
        ]:
            btn = Button(
                text=f"{icon}\n{label}", font_size=sp(10),
                background_color=C_PRIMARY if screen == "about" else C_CARD,
                color=WHITE, halign="center",
            )
            btn.bind(on_press=lambda _, s=screen: setattr(self.manager, "current", s))
            nav.add_widget(btn)
        return nav


# ─── App ──────────────────────────────────────────────────────────

class BetPawaPredictorApp(App):
    def build(self):
        Window.clearcolor = C_BG

        sm = ScreenManager(transition=FadeTransition(duration=0.15))
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(ResultsScreen(name="results"))
        sm.add_widget(HistoryScreen(name="history"))
        sm.add_widget(AboutScreen(name="about"))

        return sm

    def on_pause(self):
        return True   # allow pause on Android

    def on_resume(self):
        pass


if __name__ == "__main__":
    BetPawaPredictorApp().run()
