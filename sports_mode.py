import sys
import tkinter as tk
from tkinter import messagebox
import threading
import requests
from PIL import Image, ImageTk
import io
import os
import math

HEADERS = {"User-Agent": "Mozilla/5.0"}

LEAGUES = {
    "Premier League": "eng.1",
    "Championship": "eng.2",
    "League One": "eng.3",
    "League Two": "eng.4",
    "Champions League": "uefa.champions"
}

REFRESH_TIME = 30000  

BTN = dict(
    font=("Segoe UI", 34, "bold"),
    bd=0,
    relief="flat",
    cursor="hand2",
    activeforeground="white",
)

BTN_WIDE  = dict(**BTN, width=22, height=3)   

BTN_SMALL = dict(**BTN, width=14, height=2)   

PAD_Y = 18   

BG        = "#0d0d0d"
BLUE      = "#2563eb"
BLUE_HOV  = "#1d4ed8"
TEAL      = "#0d9488"
TEAL_HOV  = "#0f766e"
AMBER     = "#d97706"
AMBER_HOV = "#b45309"
RED       = "#dc2626"
RED_HOV   = "#b91c1c"
GREY      = "#374151"
GREY_HOV  = "#1f2937"

def styled_btn(parent, text, bg, hover_bg, command, **overrides):
    """Create a button with a hover/active highlight effect."""
    kwargs = {**BTN_WIDE, "text": text, "bg": bg, "fg": "white",
              "activebackground": hover_bg, "command": command}
    kwargs.update(overrides)
    b = tk.Button(parent, **kwargs)
    b.bind("<Enter>", lambda e: b.config(bg=hover_bg))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b

def fetch_logo(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        img = Image.open(io.BytesIO(r.content)).resize((48, 48))
        return ImageTk.PhotoImage(img)
    except:
        return None

def fetch_football_scores(league_code):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
    except Exception:
        return []

    matches = []
    for event in data.get("events", []):
        comp = event.get("competitions", [{}])[0]
        teams = comp.get("competitors", [])
        if len(teams) < 2:
            continue
        try:
            home = next(t for t in teams if t.get("homeAway") == "home")
            away = next(t for t in teams if t.get("homeAway") == "away")
        except StopIteration:
            continue

        status_obj  = comp.get("status", {})
        status_type = status_obj.get("type", {})
        state       = status_type.get("state", "pre")      

        completed   = status_type.get("completed", False)
        detail      = status_type.get("shortDetail", "")   

        kickoff_raw = event.get("date", "")
        kickoff_str = ""
        if state == "pre" and kickoff_raw:
            try:
                from datetime import datetime, timezone, timedelta
                dt_utc = datetime.strptime(kickoff_raw, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
                dt_local = dt_utc + timedelta(hours=1)   

                kickoff_str = dt_local.strftime("%H:%M")
            except Exception:
                kickoff_str = ""

        matches.append({
            "home_name":   home.get("team", {}).get("displayName", "Home"),
            "away_name":   away.get("team", {}).get("displayName", "Away"),
            "home_score":  home.get("score", "-"),
            "away_score":  away.get("score", "-"),
            "home_logo":   (home.get("team") or {}).get("logo"),
            "away_logo":   (away.get("team") or {}).get("logo"),
            "state":       state,        

            "completed":   completed,
            "detail":      detail,       

            "kickoff":     kickoff_str,  

        })
    return matches

def fetch_form_for_league(league_code):
    """
    Fetch recent completed matches using a date range query, building a
    form map {team_displayName: ['W','D','L', ...]} for the last 5 games.
    Falls back to the streak stat from the standings if scoreboard fails.
    """
    from datetime import datetime, timedelta

    today    = datetime.utcnow()
    start    = today - timedelta(weeks=10)
    date_str = f"{start.strftime('%Y%m%d')}-{today.strftime('%Y%m%d')}"

    url = (f"https://site.api.espn.com/apis/site/v2/sports/soccer/"
           f"{league_code}/scoreboard?dates={date_str}&limit=500")

    all_events = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        all_events = data.get("events", [])
    except Exception:
        pass

    if not all_events:
        for weeks_ago in range(10):
            d = today - timedelta(weeks=weeks_ago)
            fb_url = (f"https://site.api.espn.com/apis/site/v2/sports/soccer/"
                      f"{league_code}/scoreboard?dates={d.strftime('%Y%m%d')}&limit=50")
            try:
                r = requests.get(fb_url, headers=HEADERS, timeout=8)
                all_events.extend(r.json().get("events", []))
            except Exception:
                continue

    try:
        all_events.sort(key=lambda e: e.get("date", ""))
    except Exception:
        pass

    form_map = {}
    seen = set()

    for event in all_events:
        eid = event.get("id")
        if eid in seen:
            continue
        seen.add(eid)

        comp   = (event.get("competitions") or [{}])[0]
        status = (comp.get("status") or {}).get("type") or {}
        if not status.get("completed"):
            continue

        competitors = comp.get("competitors") or []
        if len(competitors) < 2:
            continue

        try:
            home = next(c for c in competitors if c.get("homeAway") == "home")
            away = next(c for c in competitors if c.get("homeAway") == "away")
            hs   = float(home.get("score", 0))
            as_  = float(away.get("score", 0))
        except Exception:
            continue

        hn = (home.get("team") or {}).get("displayName", "")
        an = (away.get("team") or {}).get("displayName", "")
        if not hn or not an:
            continue

        if hs > as_:
            hr, ar = "W", "L"
        elif hs < as_:
            hr, ar = "L", "W"
        else:
            hr, ar = "D", "D"

        form_map.setdefault(hn, []).append(hr)
        form_map.setdefault(an, []).append(ar)

    return {name: results[-5:] for name, results in form_map.items()}

def fetch_table(league_code):
    url = f"https://site.api.espn.com/apis/v2/sports/soccer/{league_code}/standings"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
    except Exception:
        return []

    form_map = fetch_form_for_league(league_code)

    table = []
    try:
        entries = None
        if "children" in data:
            try:
                entries = data["children"][0]["standings"]["entries"]
            except Exception:
                pass
        if not entries and "standings" in data:
            entries = data["standings"].get("entries", [])
        if not entries:
            return []

        for idx, entry in enumerate(entries, start=1):
            team_info = entry.get("team", {}) or {}
            team_name = team_info.get("displayName", "Unknown")

            logo_url = None
            logos = team_info.get("logos") or []
            if isinstance(logos, list) and logos:
                logo_url = logos[0].get("href")
            if not logo_url:
                logo_url = team_info.get("logo")

            stats = entry.get("stats", []) or []

            def stat_value(name):
                for s in stats:
                    if s.get("name") == name:
                        return s.get("value")
                return None

            def int_stat(name, default=0):
                v = stat_value(name)
                try:
                    return int(v) if isinstance(v, (int, float)) else int(v)
                except Exception:
                    return default

            points = int_stat("points")
            wins   = int_stat("wins")
            losses = int_stat("losses")
            draws  = int_stat("ties")
            played = int_stat("gamesPlayed", wins + draws + losses)

            rank_val = stat_value("rank")
            try:
                position = int(rank_val) if isinstance(rank_val, (int, float)) else int(str(rank_val))
            except Exception:
                position = idx

            last5 = form_map.get(team_name, [])

            table.append({
                "position": position, "team": team_name,
                "points": points, "wins": wins, "losses": losses,
                "draws": draws, "played": played,
                "logo_url": logo_url, "last5": last5,
            })
    except Exception:
        return []

    table.sort(key=lambda r: r.get("position", 999))
    return table

def fetch_speedway_scores():
    api_url = "https://www.britishspeedway.co.uk/wp-json/wp/v2/posts?per_page=10"
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
    except:
        return []

    results = []
    for post in data:
        title = post.get("title", {}).get("rendered", "")
        if "-" in title and any(c.isdigit() for c in title):
            results.append(title)
    return results[:15]

class SportsModeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sports Mode")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg=BG)
        self.root.bind("<Alt-Escape>", lambda e: self.confirm_exit())

        self.container = tk.Frame(self.root, bg=BG)
        self.container.pack(expand=True, fill="both", padx=60, pady=40)

        self.current_frame  = None
        self.scores_box     = None
        self.current_league = None
        self.mode           = None
        self.logo_cache     = {}
        self._refresh_job   = None
        self._loading_job   = None
        self._loading_label = None
        self._loading_dots  = 1

        self.show_main_menu()

    def clear_frame(self):
        self.stop_loading()
        if self._refresh_job is not None:
            try:
                self.root.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None
        if self.current_frame:
            self.current_frame.destroy()

    def shutdown_pc(self):
        os.system("shutdown /s /t 0")

    def start_loading(self, parent):
        self.stop_loading()
        self._loading_dots = 1
        self._loading_label = tk.Label(
            parent, text="Please wait .",
            fg="#6b7280", bg=BG,
            font=("Segoe UI", 36, "italic"),
        )
        self._loading_label.pack(expand=True)
        self._animate_loading()

    def _animate_loading(self):
        if self._loading_label is None:
            return
        try:
            if not self._loading_label.winfo_exists():
                return
        except Exception:
            return
        self._loading_label.config(text=f"Please wait {'.' * self._loading_dots}")
        self._loading_dots = (self._loading_dots % 3) + 1
        self._loading_job = self.root.after(500, self._animate_loading)

    def stop_loading(self):
        if self._loading_job is not None:
            try:
                self.root.after_cancel(self._loading_job)
            except Exception:
                pass
            self._loading_job = None
        if self._loading_label is not None:
            try:
                self._loading_label.destroy()
            except Exception:
                pass
            self._loading_label = None

    def show_main_menu(self):
        self.clear_frame()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True, fill="both")
        self.current_frame = frame

        tk.Label(frame, text="⚽  Grandad's Sports Tracker",
                 fg="white", bg=BG,
                 font=("Segoe UI", 52, "bold")).pack(pady=(10, 20))

        grid = tk.Frame(frame, bg=BG)
        grid.pack(expand=True, fill="both", padx=20, pady=10)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=2)
        grid.rowconfigure(1, weight=1)

        def gbtn(parent, text, bg, hbg, cmd, row, col, colspan=1):
            b = tk.Button(parent, text=text, bg=bg, fg="white",
                          font=("Segoe UI", 40, "bold"), bd=0, relief="flat",
                          cursor="hand2", activebackground=hbg, activeforeground="white",
                          command=cmd)
            b.grid(row=row, column=col, columnspan=colspan,
                   sticky="nsew", padx=12, pady=12)
            b.bind("<Enter>", lambda e: b.config(bg=hbg))
            b.bind("<Leave>", lambda e: b.config(bg=bg))

        gbtn(grid, "🏟\nFootball",    BLUE,  BLUE_HOV,  self.show_football_leagues,           0, 0)
        gbtn(grid, "🏍\nSpeedway",    AMBER, AMBER_HOV, lambda: self.show_scores("speedway"), 0, 1)
        gbtn(grid, "⏻   Turn Off", RED,   RED_HOV,   self.confirm_shutdown,                1, 0, colspan=2)

    def show_football_leagues(self):
        self.clear_frame()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True, fill="both")
        self.current_frame = frame

        tk.Label(frame, text="Choose a League", fg="white", bg=BG,
                 font=("Segoe UI", 48, "bold")).pack(pady=(10, 16))

        grid = tk.Frame(frame, bg=BG)
        grid.pack(expand=True, fill="both", padx=20)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        league_items = list(LEAGUES.items())
        for i, (name, code) in enumerate(league_items):
            row, col = divmod(i, 2)
            grid.rowconfigure(row, weight=1)
            b = tk.Button(grid, text=name, bg=BLUE, fg="white",
                          font=("Segoe UI", 34, "bold"), bd=0, relief="flat",
                          cursor="hand2", activebackground=BLUE_HOV, activeforeground="white",
                          command=lambda c=code: self.show_football_submenu(c))
            b.grid(row=row, column=col, sticky="nsew", padx=12, pady=12)
            b.bind("<Enter>", lambda e, b=b: b.config(bg=BLUE_HOV))
            b.bind("<Leave>", lambda e, b=b: b.config(bg=BLUE))

        back_row = (len(league_items) + 1) // 2
        grid.rowconfigure(back_row, weight=1)
        back = tk.Button(grid, text="← Back", bg=GREY, fg="white",
                         font=("Segoe UI", 34, "bold"), bd=0, relief="flat",
                         cursor="hand2", activebackground=GREY_HOV, activeforeground="white",
                         command=self.show_main_menu)
        back.grid(row=back_row, column=0, columnspan=2, sticky="nsew", padx=12, pady=12)
        back.bind("<Enter>", lambda e: back.config(bg=GREY_HOV))
        back.bind("<Leave>", lambda e: back.config(bg=GREY))

    def show_football_submenu(self, league_code):
        self.current_league = league_code
        league_name = next((n for n, c in LEAGUES.items() if c == league_code), "Football")
        self.clear_frame()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True, fill="both")
        self.current_frame = frame

        tk.Label(frame, text=league_name, fg="white", bg=BG,
                 font=("Segoe UI", 48, "bold")).pack(pady=(10, 16))

        grid = tk.Frame(frame, bg=BG)
        grid.pack(expand=True, fill="both", padx=20)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(0, weight=2)
        grid.rowconfigure(1, weight=1)

        def gbtn(text, bg, hbg, cmd, row, col, colspan=1):
            b = tk.Button(grid, text=text, bg=bg, fg="white",
                          font=("Segoe UI", 36, "bold"), bd=0, relief="flat",
                          cursor="hand2", activebackground=hbg, activeforeground="white",
                          command=cmd)
            b.grid(row=row, column=col, columnspan=colspan,
                   sticky="nsew", padx=12, pady=12)
            b.bind("<Enter>", lambda e: b.config(bg=hbg))
            b.bind("<Leave>", lambda e: b.config(bg=bg))

        gbtn("📅\nFixtures & Scores", BLUE, BLUE_HOV,
             lambda: self.show_scores("football", league_code), 0, 0)
        gbtn("📊\nLeague Table",      TEAL, TEAL_HOV,
             lambda: self.show_table(league_code),              0, 1)
        gbtn("← Back",               GREY, GREY_HOV,
             self.show_football_leagues,                        1, 0, colspan=2)

    def show_scores(self, mode, league=None):
        self.mode = mode
        self.current_league = league
        self.clear_frame()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True, fill="both")
        self.current_frame = frame

        title = "Speedway Results" if mode == "speedway" else "Fixtures & Scores"
        tk.Label(frame, text=title, fg="white", bg=BG,
                 font=("Segoe UI", 44, "bold")).pack(pady=(0, 10))

        back_bar = tk.Frame(frame, bg=BG)
        back_bar.pack(side="bottom", fill="x", pady=14)
        styled_btn(back_bar, "← Back", GREY, GREY_HOV,
                   self.show_main_menu, **BTN_SMALL).pack()

        self.scores_box = tk.Frame(frame, bg=BG)
        self.scores_box.pack(expand=True, fill="both", padx=10)

        self.start_loading(self.scores_box)
        self.update_scores()

    def show_table(self, league_code):
        self.clear_frame()
        frame = tk.Frame(self.container, bg=BG)
        frame.pack(expand=True, fill="both")
        self.current_frame = frame

        league_name = next((n for n, c in LEAGUES.items() if c == league_code), "League")
        tk.Label(frame, text=f"{league_name} Table", fg="white", bg=BG,
                 font=("Segoe UI", 44, "bold")).pack(pady=(0, 16))

        self.scores_box = tk.Frame(frame, bg=BG)
        self.scores_box.pack(expand=True, fill="both", padx=20)

        bottom_bar = tk.Frame(frame, bg=BG)
        bottom_bar.pack(side="bottom", pady=24)

        styled_btn(bottom_bar, "← Back", GREY, GREY_HOV,
                   self.show_main_menu, **BTN_SMALL).pack(side="left", padx=16)

        pages_box = tk.Frame(bottom_bar, bg=BG)
        pages_box.pack(side="left", padx=20)

        page_size = 10
        self.start_loading(self.scores_box)

        def load_table():
            table = fetch_table(league_code)
            positions = []
            for row in table:
                try:
                    positions.append(int(row["position"]))
                except Exception:
                    pass
            max_pos = max(positions) if positions else len(table)

            def row_bg(pos):
                if pos <= 4:              return "#14532d"
                if pos > max_pos - 3:    return "#7f1d1d"
                return "#111827"

            def render_page(page_index):
                self.stop_loading()
                for w in self.scores_box.winfo_children():
                    w.destroy()
                for w in pages_box.winfo_children():
                    w.destroy()

                if not table:
                    tk.Label(self.scores_box, text="Table data unavailable",
                             fg="white", bg=BG, font=("Segoe UI", 28)).pack(pady=40)
                    return

                headers   = ["Pos", "Team", "GP", "W", "D", "L", "Pts", "Last 5"]
                col_widths = [4,     24,     4,    4,   4,   4,   4,     10]
                for col, (hdr, cw) in enumerate(zip(headers, col_widths)):
                    tk.Label(self.scores_box, text=hdr, fg="#9ca3af", bg=BG,
                             font=("Segoe UI", 22, "bold"), anchor="w", width=cw
                             ).grid(row=0, column=col, padx=6, pady=(0, 8), sticky="w")

                start = page_index * page_size
                page_rows = table[start: start + page_size]

                for r_i, row in enumerate(page_rows, start=1):
                    try:
                        pos_int = int(row["position"])
                    except Exception:
                        pos_int = 999
                    bg = row_bg(pos_int)

                    tk.Label(self.scores_box, text=str(row["position"]),
                             fg="white", bg=bg, font=("Segoe UI", 22), anchor="w", width=4
                             ).grid(row=r_i, column=0, padx=6, pady=3, sticky="w")

                    team_cell = tk.Frame(self.scores_box, bg=bg)
                    team_cell.grid(row=r_i, column=1, padx=6, pady=3, sticky="w")
                    logo_img = self.get_logo(row.get("logo_url")) if row.get("logo_url") else None
                    if logo_img:
                        tk.Label(team_cell, image=logo_img, bg=bg).pack(side="left", padx=(0, 6))
                    tk.Label(team_cell, text=row["team"], fg="white", bg=bg,
                             font=("Segoe UI", 22), anchor="w").pack(side="left")

                    for c_off, val in enumerate([
                        row.get("played", 0), row["wins"], row["draws"],
                        row["losses"], row["points"]
                    ]):
                        tk.Label(self.scores_box, text=str(val),
                                 fg="white", bg=bg, font=("Segoe UI", 22), anchor="w", width=4
                                 ).grid(row=r_i, column=2 + c_off, padx=6, pady=3, sticky="w")

                    form_cell = tk.Frame(self.scores_box, bg=bg)
                    form_cell.grid(row=r_i, column=7, padx=6, pady=3, sticky="w")
                    last5  = row.get("last5") or []
                    padded = (last5 + [""] * (5 - len(last5)))[:5]
                    FORM_COLOURS = {"W": "#16a34a", "L": "#dc2626", "D": "#4b5563"}
                    for ch in padded:
                        if ch in FORM_COLOURS:
                            dot_bg = FORM_COLOURS[ch]
                            dot_fg = "white"
                            letter = ch
                        else:

                            dot_bg = bg
                            dot_fg = "#374151"
                            letter = "–"
                        dot = tk.Frame(form_cell, bg=dot_bg,
                                       highlightbackground="#374151",
                                       highlightthickness=1,
                                       width=34, height=34)
                        dot.pack(side="left", padx=2)
                        dot.pack_propagate(False)
                        tk.Label(dot, text=letter, fg=dot_fg, bg=dot_bg,
                                 font=("Segoe UI", 14, "bold")
                                 ).place(relx=0.5, rely=0.5, anchor="center")

                total_pages = max(1, math.ceil(len(table) / page_size))
                for i in range(total_pages):
                    is_cur = i == page_index
                    b = tk.Button(
                        pages_box,
                        text=str(i + 1),
                        font=("Segoe UI", 28, "bold"),
                        width=4, height=2,
                        bg=BLUE if is_cur else GREY,
                        fg="white", bd=0, cursor="hand2",
                        activebackground=BLUE_HOV, activeforeground="white",
                        command=lambda p=i: render_page(p),
                    )
                    b.pack(side="left", padx=8)

            self.root.after(0, lambda: render_page(0))

        threading.Thread(target=load_table, daemon=True).start()

    def update_scores(self):
        threading.Thread(target=self.load_scores, daemon=True).start()

    def load_scores(self):
        if self.mode == "football":
            matches = fetch_football_scores(self.current_league)
            self.root.after(0, lambda: self.display_matches(matches))
        elif self.mode == "speedway":
            lines = fetch_speedway_scores()
            self.root.after(0, lambda: self.display_speedway(lines))

    def display_matches(self, matches):
        self.stop_loading()
        for w in self.scores_box.winfo_children():
            w.destroy()

        if not matches:
            tk.Label(self.scores_box, text="No fixtures available right now",
                     fg="#9ca3af", bg=BG, font=("Segoe UI", 30)).pack(expand=True)
        else:
            self.scores_box.columnconfigure(0, weight=1)
            self.scores_box.columnconfigure(1, weight=1)

            for idx, m in enumerate(matches):
                grid_row, grid_col = divmod(idx, 2)
                self.scores_box.rowconfigure(grid_row, weight=1)

                state = m.get("state", "post")

                if state == "in":
                    card_bg  = "#1a1f2e"
                    border   = "#3b82f6"   

                else:
                    card_bg  = "#111827"
                    border   = "#2d3748"

                card = tk.Frame(self.scores_box, bg=card_bg,
                                highlightbackground=border, highlightthickness=2)
                card.grid(row=grid_row, column=grid_col, sticky="nsew", padx=8, pady=8)
                card.columnconfigure(0, weight=1)  

                card.columnconfigure(1, weight=0)  

                card.columnconfigure(2, weight=1)  

                home_logo = self.get_logo(m["home_logo"]) if m.get("home_logo") else None
                away_logo = self.get_logo(m["away_logo"]) if m.get("away_logo") else None

                if state == "in":
                    badge_text = f"🔴 LIVE  {m.get('detail', '')}"
                    badge_fg   = "#f87171"
                elif state == "pre":
                    badge_text = f"🕐 {m.get('kickoff', 'Upcoming')}"
                    badge_fg   = "#94a3b8"
                else:
                    badge_text = f"✔  FT  {m.get('detail', '')}"
                    badge_fg   = "#6b7280"

                tk.Label(card, text=badge_text, fg=badge_fg, bg=card_bg,
                         font=("Segoe UI", 14, "bold")).grid(
                             row=0, column=0, columnspan=3, pady=(8, 0), padx=10, sticky="w")

                home_inner = tk.Frame(card, bg=card_bg)
                home_inner.grid(row=1, column=0, sticky="e", padx=(10, 4), pady=(4, 10))
                if home_logo:
                    tk.Label(home_inner, image=home_logo, bg=card_bg).pack(side="right", padx=(6, 0))
                tk.Label(home_inner, text=m["home_name"], fg="white", bg=card_bg,
                         font=("Segoe UI", 20, "bold"), anchor="e").pack(side="right")

                if state == "pre":
                    score_text = "vs"
                    score_fg   = "#94a3b8"
                else:
                    score_text = f"{m['home_score']}–{m['away_score']}"
                    score_fg   = "#facc15" if state == "in" else "white"

                tk.Label(card, text=score_text, fg=score_fg, bg=card_bg,
                         font=("Segoe UI", 24, "bold"), width=7, anchor="center"
                         ).grid(row=1, column=1, padx=6, pady=(4, 10))

                away_inner = tk.Frame(card, bg=card_bg)
                away_inner.grid(row=1, column=2, sticky="w", padx=(4, 10), pady=(4, 10))
                if away_logo:
                    tk.Label(away_inner, image=away_logo, bg=card_bg).pack(side="left", padx=(0, 6))
                tk.Label(away_inner, text=m["away_name"], fg="#cbd5e1", bg=card_bg,
                         font=("Segoe UI", 20, "bold"), anchor="w").pack(side="left")

        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        self._refresh_job = self.root.after(REFRESH_TIME, self.update_scores)

    def display_speedway(self, lines):
        self.stop_loading()
        for w in self.scores_box.winfo_children():
            w.destroy()

        if not lines:
            tk.Label(self.scores_box, text="No speedway results available",
                     fg="#9ca3af", bg=BG, font=("Segoe UI", 30)).pack(expand=True)
        else:

            self.scores_box.columnconfigure(0, weight=1)
            self.scores_box.columnconfigure(1, weight=1)
            for idx, line in enumerate(lines):
                row, col = divmod(idx, 2)
                self.scores_box.rowconfigure(row, weight=1)
                card = tk.Frame(self.scores_box, bg="#111827",
                                highlightbackground="#2d3748", highlightthickness=2)
                card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
                tk.Label(card, text=f"#{idx + 1}  {line}",
                         fg="white", bg="#111827",
                         font=("Segoe UI", 22), anchor="w", wraplength=600,
                         justify="left").pack(fill="both", expand=True, padx=14, pady=12)

        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        self._refresh_job = self.root.after(REFRESH_TIME, self.update_scores)

    def get_logo(self, url):
        if not url:
            return None
        if url in self.logo_cache:
            return self.logo_cache[url]
        logo = fetch_logo(url)
        if logo:
            self.logo_cache[url] = logo
        return logo

    def confirm_exit(self):
        if messagebox.askyesno("Exit", "Exit Sports Mode?"):
            self.root.destroy()

    def confirm_shutdown(self):
        self.shutdown_pc()

    def run(self):
        self.root.mainloop()

def main():
    app = SportsModeApp()
    app.run()

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        main()
    else:
        print("Sports Mode is designed for Windows.")