"""
main.py - BetPawa Predictor Android App (Kivy)
Reads pre-generated predictions.json — no ML on device.
Developer: Sserunjogi Sharif | 0787816686
"""

import os
import json
from datetime import datetime, timedelta

os.environ.setdefault("KIVY_NO_ENV_CONFIG", "1")

import kivy
kivy.require("2.1.0")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.metrics import dp, sp

# ── Palette ──────────────────────────────────────────────────────
C_BG      = get_color_from_hex("#0D1117")
C_CARD    = get_color_from_hex("#161B22")
C_PRIMARY = get_color_from_hex("#238636")
C_ACCENT  = get_color_from_hex("#1F6FEB")
C_DANGER  = get_color_from_hex("#DA3633")
C_TEXT    = get_color_from_hex("#F0F6FC")
C_MUTED   = get_color_from_hex("#8B949E")
C_GOLD    = get_color_from_hex("#D29922")
C_WIN     = get_color_from_hex("#238636")
C_DRAW    = get_color_from_hex("#D29922")
C_LOSS    = get_color_from_hex("#DA3633")
WHITE     = (1, 1, 1, 1)


def bg(widget, color, radius=0):
    with widget.canvas.before:
        Color(*color)
        if radius:
            widget._bg = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius])
        else:
            widget._bg = Rectangle(pos=widget.pos, size=widget.size)
    def upd(*_):
        widget._bg.pos  = widget.pos
        widget._bg.size = widget.size
    widget.bind(pos=upd, size=upd)


def outcome_color(pred):
    p = pred.lower()
    if "home" in p: return C_WIN
    if "away" in p: return C_LOSS
    return C_DRAW


def load_predictions():
    """Load predictions.json bundled with the app."""
    paths = [
        "predictions.json",
        os.path.join(os.path.dirname(__file__), "predictions.json"),
        os.path.join(os.environ.get("ANDROID_APP_PATH", ""), "predictions.json"),
    ]
    for p in paths:
        if p and os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    return None


# ── Screens ───────────────────────────────────────────────────────

class HomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        bg(root, C_BG)

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(70), padding=[dp(16), dp(10)])
        bg(hdr, C_CARD)
        col = BoxLayout(orientation="vertical", spacing=dp(2))
        col.add_widget(Label(text="BetPawa Predictor", font_size=sp(20),
                             bold=True, color=C_TEXT, halign="left",
                             size_hint_y=None, height=dp(28)))
        col.add_widget(Label(text="AI-powered match outcome predictions",
                             font_size=sp(11), color=C_MUTED, halign="left",
                             size_hint_y=None, height=dp(18)))
        hdr.add_widget(col)
        root.add_widget(hdr)

        # Body
        body = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(14))
        bg(body, C_BG)

        body.add_widget(Label(text="SELECT MATCH DATE", font_size=sp(11),
                              color=C_MUTED, bold=True, halign="left",
                              size_hint_y=None, height=dp(18),
                              text_size=(Window.width - dp(36), None)))

        # Date input row
        dr = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        self.date_input = TextInput(
            text=datetime.today().strftime("%Y-%m-%d"),
            multiline=False, font_size=sp(16),
            foreground_color=C_TEXT, background_color=C_CARD,
            cursor_color=C_PRIMARY, padding=[dp(12), dp(14)],
            hint_text="YYYY-MM-DD", hint_text_color=C_MUTED)
        yest = Button(text="Yesterday", size_hint_x=None, width=dp(90),
                      font_size=sp(12), background_color=C_ACCENT, color=WHITE)
        yest.bind(on_press=lambda _: setattr(
            self.date_input, "text",
            (datetime.today()-timedelta(days=1)).strftime("%Y-%m-%d")))
        dr.add_widget(self.date_input)
        dr.add_widget(yest)
        body.add_widget(dr)

        # Quick select
        qs = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
        for lbl, delta in [("Today", 0), ("Tomorrow", 1), ("-2 days", -2)]:
            b = Button(text=lbl, font_size=sp(12),
                       background_color=C_CARD, color=C_TEXT)
            b.bind(on_press=lambda _, d=delta: setattr(
                self.date_input, "text",
                (datetime.today()+timedelta(days=d)).strftime("%Y-%m-%d")))
            qs.add_widget(b)
        body.add_widget(qs)

        # Predict button
        pb = Button(text="GET PREDICTIONS", size_hint_y=None, height=dp(54),
                    font_size=sp(16), bold=True,
                    background_color=C_PRIMARY, color=WHITE)
        pb.bind(on_press=self._predict)
        body.add_widget(pb)

        self.status = Label(text="", font_size=sp(13), color=C_MUTED,
                            size_hint_y=None, height=dp(22))
        body.add_widget(self.status)

        # Info card
        ic = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(6),
                       size_hint_y=None, height=dp(96))
        bg(ic, C_CARD, radius=10)
        ic.add_widget(Label(text="HOW IT WORKS", font_size=sp(10),
                            color=C_MUTED, bold=True, halign="left",
                            size_hint_y=None, height=dp(16)))
        for tip in ["XGBoost model trained on 500+ real matches",
                    "Predictions rebuilt on every release",
                    "For informational purposes only"]:
            ic.add_widget(Label(text=tip, font_size=sp(12), color=C_TEXT,
                                halign="left", size_hint_y=None, height=dp(20),
                                text_size=(Window.width - dp(56), None)))
        body.add_widget(ic)

        body.add_widget(BoxLayout())  # spacer
        root.add_widget(body)
        root.add_widget(self._nav("home"))
        self.add_widget(root)

    def _predict(self, *_):
        date = self.date_input.text.strip()
        data = load_predictions()
        if data is None:
            self.status.text = "predictions.json not found"
            self.status.color = C_DANGER
            return
        preds = data.get("predictions", {}).get(date)
        if preds is None:
            available = sorted(data.get("predictions", {}).keys())
            if available:
                self.status.text = f"No data for {date}. Try: {available[0]} - {available[-1]}"
            else:
                self.status.text = "No predictions available"
            self.status.color = C_DANGER
            return
        self.status.text = ""
        screen = self.manager.get_screen("results")
        screen.set_results(date, preds, data)
        self.manager.current = "results"

    def _nav(self, active):
        nav = BoxLayout(size_hint_y=None, height=dp(58), spacing=1)
        bg(nav, C_CARD)
        for icon, lbl, scr in [("H","Home","home"),("S","Stats","history"),("i","About","about")]:
            b = Button(text=f"{icon}\n{lbl}", font_size=sp(10), halign="center",
                       background_color=C_PRIMARY if scr == active else C_CARD,
                       color=WHITE)
            b.bind(on_press=lambda _, s=scr: setattr(self.manager, "current", s))
            nav.add_widget(b)
        return nav


class ResultsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._root = BoxLayout(orientation="vertical")
        bg(self._root, C_BG)
        self.add_widget(self._root)

    def set_results(self, date, preds, bundle):
        self._root.clear_widgets()

        # Header
        hdr = BoxLayout(size_hint_y=None, height=dp(58), padding=[dp(12), dp(8)])
        bg(hdr, C_CARD)
        back = Button(text="< Back", size_hint_x=None, width=dp(80),
                      font_size=sp(13), background_color=C_CARD, color=C_ACCENT)
        back.bind(on_press=lambda _: setattr(self.manager, "current", "home"))
        hdr.add_widget(back)
        hdr.add_widget(Label(text=f"Predictions  {date}",
                             font_size=sp(15), bold=True, color=C_TEXT))
        self._root.add_widget(hdr)

        # Model info bar
        acc = bundle.get("model_accuracy", "N/A")
        acc_str = f"{float(acc)*100:.1f}%" if isinstance(acc, float) else str(acc)
        info = Label(
            text=f"Model accuracy: {acc_str}  |  Built: {bundle.get('generated_at','?')}",
            font_size=sp(10), color=C_MUTED, size_hint_y=None, height=dp(22),
            halign="center")
        self._root.add_widget(info)

        # Cards
        scroll = ScrollView()
        cards = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(10),
                          size_hint_y=None)
        cards.bind(minimum_height=cards.setter("height"))

        if not preds:
            cards.add_widget(Label(text="No predictions for this date.",
                                   color=C_MUTED, font_size=sp(14)))
        else:
            for i, p in enumerate(preds, 1):
                cards.add_widget(self._card(i, p))

        cards.add_widget(Label(
            text="Statistical predictions only. Gamble responsibly. 18+",
            font_size=sp(10), color=C_MUTED, halign="center",
            size_hint_y=None, height=dp(36),
            text_size=(Window.width - dp(20), None)))

        scroll.add_widget(cards)
        self._root.add_widget(scroll)

    def _card(self, n, p):
        card = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8),
                         size_hint_y=None, height=dp(148))
        bg(card, C_CARD, radius=10)

        # Teams
        tr = BoxLayout(size_hint_y=None, height=dp(30))
        tr.add_widget(Label(text=p["home"], font_size=sp(13), bold=True,
                            color=C_TEXT, halign="center"))
        tr.add_widget(Label(text="VS", font_size=sp(10), color=C_MUTED,
                            size_hint_x=None, width=dp(32)))
        tr.add_widget(Label(text=p["away"], font_size=sp(13), bold=True,
                            color=C_TEXT, halign="center"))
        card.add_widget(tr)

        # Badge
        br = BoxLayout(size_hint_y=None, height=dp(34))
        br.add_widget(BoxLayout())
        badge = Label(text=f"  {p['prediction'].upper()}  ",
                      font_size=sp(12), bold=True, color=WHITE,
                      size_hint_x=None, width=dp(126))
        bg(badge, outcome_color(p["prediction"]), radius=14)
        br.add_widget(badge)
        br.add_widget(BoxLayout())
        card.add_widget(br)

        # Probability bar
        try:
            ph = float(p.get("proba_home","33%").rstrip("%")) / 100
            pd_ = float(p.get("proba_draw","27%").rstrip("%")) / 100
            pa = float(p.get("proba_away","33%").rstrip("%")) / 100
        except Exception:
            ph, pd_, pa = 0.33, 0.27, 0.40
        pb = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(3))
        for lbl, val, col in [(f"H {p.get('proba_home','?')}", max(ph,0.12), C_WIN),
                               (f"D {p.get('proba_draw','?')}", max(pd_,0.12), C_DRAW),
                               (f"A {p.get('proba_away','?')}", max(pa,0.12), C_LOSS)]:
            seg = Label(text=lbl, font_size=sp(9), color=WHITE,
                        size_hint_x=val, halign="center")
            bg(seg, col)
            pb.add_widget(seg)
        card.add_widget(pb)

        # Confidence + odds
        mr = BoxLayout(size_hint_y=None, height=dp(22))
        mr.add_widget(Label(text=f"Confidence: {p.get('confidence','?')}",
                            font_size=sp(11), color=C_MUTED, halign="left",
                            text_size=(dp(160), None)))
        mr.add_widget(Label(text=f"Odds hint: {p.get('odds_hint','?')}",
                            font_size=sp(11), color=C_GOLD, halign="right",
                            text_size=(dp(160), None)))
        card.add_widget(mr)
        return card


class HistoryScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        bg(root, C_BG)
        hdr = BoxLayout(size_hint_y=None, height=dp(58), padding=[dp(16), dp(10)])
        bg(hdr, C_CARD)
        hdr.add_widget(Label(text="Recent Predictions",
                             font_size=sp(17), bold=True, color=C_TEXT))
        root.add_widget(hdr)

        scroll = ScrollView()
        body = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10),
                         size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))

        data = load_predictions()
        if data:
            today = datetime.today()
            preds_dict = data.get("predictions", {})
            # Show last 7 days
            for i in range(7, 0, -1):
                d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                if d in preds_dict:
                    day_card = BoxLayout(orientation="vertical", padding=dp(10),
                                        spacing=dp(4), size_hint_y=None, height=dp(80))
                    bg(day_card, C_CARD, radius=8)
                    day_card.add_widget(Label(text=f"  {d}", font_size=sp(13),
                                             bold=True, color=C_TEXT, halign="left",
                                             size_hint_y=None, height=dp(22)))
                    ps = preds_dict[d][:2]
                    for p in ps:
                        day_card.add_widget(Label(
                            text=f"  {p['home']} vs {p['away']}  =>  {p['prediction']}  ({p['confidence']})",
                            font_size=sp(11), color=C_MUTED, halign="left",
                            text_size=(Window.width - dp(52), None),
                            size_hint_y=None, height=dp(18)))
                    body.add_widget(day_card)
        else:
            body.add_widget(Label(
                text="No prediction history yet.\nTap Home to get predictions.",
                color=C_MUTED, font_size=sp(14), halign="center",
                size_hint_y=None, height=dp(80)))

        scroll.add_widget(body)
        root.add_widget(scroll)
        root.add_widget(self._nav("history"))
        self.add_widget(root)

    def _nav(self, active):
        nav = BoxLayout(size_hint_y=None, height=dp(58), spacing=1)
        bg(nav, C_CARD)
        for icon, lbl, scr in [("H","Home","home"),("S","Stats","history"),("i","About","about")]:
            b = Button(text=f"{icon}\n{lbl}", font_size=sp(10), halign="center",
                       background_color=C_PRIMARY if scr == active else C_CARD,
                       color=WHITE)
            b.bind(on_press=lambda _, s=scr: setattr(self.manager, "current", s))
            nav.add_widget(b)
        return nav


class AboutScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        bg(root, C_BG)
        hdr = BoxLayout(size_hint_y=None, height=dp(58), padding=[dp(16), dp(10)])
        bg(hdr, C_CARD)
        hdr.add_widget(Label(text="About", font_size=sp(17),
                             bold=True, color=C_TEXT))
        root.add_widget(hdr)

        scroll = ScrollView()
        body = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(14),
                         size_hint_y=None)
        body.bind(minimum_height=body.setter("height"))

        # App card
        ac = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8),
                       size_hint_y=None, height=dp(120))
        bg(ac, C_CARD, radius=10)
        ac.add_widget(Label(text="BetPawa Predictor", font_size=sp(19),
                            bold=True, color=C_PRIMARY, halign="center",
                            size_hint_y=None, height=dp(28)))
        ac.add_widget(Label(text="Version 1.0.0  |  AI-Powered Football Predictions",
                            font_size=sp(11), color=C_MUTED, halign="center",
                            size_hint_y=None, height=dp(18)))
        ac.add_widget(Label(
            text="XGBoost Machine Learning  |  500+ match training set\nPredictions generated server-side, bundled fresh each build",
            font_size=sp(11), color=C_TEXT, halign="center",
            text_size=(Window.width - dp(52), None),
            size_hint_y=None, height=dp(36)))
        body.add_widget(ac)

        # Developer card
        dc = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(6),
                       size_hint_y=None, height=dp(170))
        bg(dc, C_CARD, radius=10)
        dc.add_widget(Label(text="DEVELOPER", font_size=sp(10),
                            color=C_MUTED, bold=True, halign="left",
                            size_hint_y=None, height=dp(18)))
        for field, value in [
            ("Name",     "Sserunjogi Sharif"),
            ("Phone",    "0787816686"),
            ("Password", "Teenaged10@"),
            ("GitHub",   "Sharif123-cloud"),
            ("App",      "BetPawa Predictor v1.0"),
        ]:
            row = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(8))
            row.add_widget(Label(text=field, font_size=sp(11), color=C_MUTED,
                                 size_hint_x=None, width=dp(76), halign="right",
                                 text_size=(dp(76), None)))
            row.add_widget(Label(text=value, font_size=sp(12), bold=True,
                                 color=C_TEXT, halign="left",
                                 text_size=(Window.width - dp(114), None)))
            dc.add_widget(row)
        body.add_widget(dc)

        # Disclaimer
        disc = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(4),
                         size_hint_y=None, height=dp(110))
        bg(disc, C_CARD, radius=10)
        disc.add_widget(Label(text="DISCLAIMER", font_size=sp(10),
                              color=C_DANGER, bold=True, halign="left",
                              size_hint_y=None, height=dp(18)))
        disc.add_widget(Label(
            text="Statistical predictions for informational use only.\n"
                 "No outcome is guaranteed. Gamble responsibly. 18+ only.\n"
                 "Developer not liable for any financial losses.",
            font_size=sp(11), color=C_MUTED, halign="left",
            text_size=(Window.width - dp(52), None),
            size_hint_y=None, height=dp(68)))
        body.add_widget(disc)

        scroll.add_widget(body)
        root.add_widget(scroll)
        root.add_widget(self._nav("about"))
        self.add_widget(root)

    def _nav(self, active):
        nav = BoxLayout(size_hint_y=None, height=dp(58), spacing=1)
        bg(nav, C_CARD)
        for icon, lbl, scr in [("H","Home","home"),("S","Stats","history"),("i","About","about")]:
            b = Button(text=f"{icon}\n{lbl}", font_size=sp(10), halign="center",
                       background_color=C_PRIMARY if scr == active else C_CARD,
                       color=WHITE)
            b.bind(on_press=lambda _, s=scr: setattr(self.manager, "current", s))
            nav.add_widget(b)
        return nav


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
        return True

    def on_resume(self):
        pass


if __name__ == "__main__":
    BetPawaPredictorApp().run()
