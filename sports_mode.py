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

REFRESH_TIME = 30000  # 30 seconds

# ---------------- Data Fetching ----------------

def fetch_logo(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        img = Image.open(io.BytesIO(r.content)).resize((40, 40))
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
        matches.append(
            {
                "home_name": home.get("team", {}).get("displayName", "Home"),
                "away_name": away.get("team", {}).get("displayName", "Away"),
                "home_score": home.get("score", "0"),
                "away_score": away.get("score", "0"),
                "home_logo": (home.get("team", {}) or {}).get("logo"),
                "away_logo": (away.get("team", {}) or {}).get("logo"),
            }
        )
    return matches


def fetch_last5_for_team(league_code, team_id):
    """
    Fetch last 5 results (W/L/D) for a single team from its schedule.
    """
    if not team_id:
        return []

    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/teams/{team_id}/schedule"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
    except Exception:
        return []

    events = data.get("events", [])
    # Sort by date to ensure correct order
    try:
        events = sorted(events, key=lambda e: e.get("date", ""))
    except Exception:
        pass

    results = []
    str_team_id = str(team_id)

    for event in events:
        competitions = event.get("competitions") or []
        if not competitions:
            continue
        comp = competitions[0]
        status = (comp.get("status") or {}).get("type") or {}
        if not status.get("completed"):
            continue

        competitors = comp.get("competitors") or []
        me = None
        opp = None
        for c in competitors:
            tid = str((c.get("team") or {}).get("id"))
            if tid == str_team_id:
                me = c
            else:
                opp = c if opp is None else opp
        if not me or not opp:
            continue

        try:
            my_score = float(me.get("score", 0))
            opp_score = float(opp.get("score", 0))
        except Exception:
            continue

        if my_score > opp_score:
            results.append("W")
        elif my_score < opp_score:
            results.append("L")
        else:
            results.append("D")

    return results[-5:]

def fetch_table(league_code):

    url = f"https://site.api.espn.com/apis/v2/sports/soccer/{league_code}/standings"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
    except Exception:
        return []

    table = []

    try:
        # ESPN sometimes nests standings differently
        entries = None

        if "children" in data:
            try:
                entries = data["children"][0]["standings"]["entries"]
            except Exception:
                entries = None

        if not entries and "standings" in data:
            entries = data["standings"].get("entries", [])

        if not entries:
            return []

        for idx, entry in enumerate(entries, start=1):
            team_info = entry.get("team", {}) or {}
            team_name = team_info.get("displayName", "Unknown")
            team_id = team_info.get("id")

            # Team logo (if available)
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
                    if isinstance(v, (int, float)):
                        return int(v)
                    return int(v)
                except Exception:
                    return default

            points = int_stat("points")
            wins = int_stat("wins")
            losses = int_stat("losses")
            draws = int_stat("ties")
            played = int_stat("gamesPlayed", wins + draws + losses)

            # Rank is stored as a stat named "rank"
            rank_val = stat_value("rank")
            try:
                if isinstance(rank_val, (int, float)):
                    position = int(rank_val)
                else:
                    position = int(str(rank_val))
            except Exception:
                # Fallback to order in list
                position = idx

            # Last 5 results via team schedule
            last5 = fetch_last5_for_team(league_code, team_id)

            table.append(
                {
                    "position": position,
                    "team": team_name,
                    "points": points,
                    "wins": wins,
                    "losses": losses,
                    "draws": draws,
                    "played": played,
                    "logo_url": logo_url,
                    "last5": last5,
                }
            )

    except Exception:
        return []

    # Sort by position to be safe
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

# ---------------- App ----------------

class SportsModeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sports Mode")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#101010")

        # Only way out: Alt+Esc
        self.root.bind("<Alt-Escape>", lambda e: self.confirm_exit())

        self.container = tk.Frame(self.root, bg="#101010")
        self.container.pack(expand=True, fill="both", padx=40, pady=40)

        self.current_frame = None
        self.scores_box = None
        self.current_league = None
        self.mode = None
        self.logo_cache = {}
        self._refresh_job = None

        self.show_main_menu()

    # ---------------- Frame Control ----------------

    def clear_frame(self):
        # Stop any scheduled auto-refresh when changing screens
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

    # ---------------- Main Menu ----------------

    def show_main_menu(self):
        self.clear_frame()
        frame = tk.Frame(self.container, bg="#101010")
        frame.pack(expand=True)
        self.current_frame = frame

        tk.Label(frame, text="Grandad's Sports Mode", fg="white", bg="#101010",
                 font=("Segoe UI", 48, "bold")).pack(pady=40)

        btn_style = {"width": 18, "height": 3, "font": ("Segoe UI", 32, "bold"), "bd":0, "fg":"white"}

        tk.Button(frame, text="Football", bg="#3182ce",
                  command=self.show_football_leagues, **btn_style).pack(pady=20)

        tk.Button(frame, text="Speedway", bg="#d69e2e",
                  command=lambda: self.show_scores("speedway"), **btn_style).pack(pady=20)

        tk.Button(frame, text="OFF", bg="#e53e3e", fg="white",
                  font=("Segoe UI",36,"bold"), width=18, height=2,
                  command=self.confirm_shutdown).pack(pady=40)

    # ---------------- Football Menu ----------------

    def show_football_leagues(self):
        self.clear_frame()
        frame = tk.Frame(self.container, bg="#101010")
        frame.pack(expand=True)
        self.current_frame = frame

        tk.Label(frame, text="Choose League", fg="white", bg="#101010",
                 font=("Segoe UI",44,"bold")).pack(pady=40)

        for name, code in LEAGUES.items():
            tk.Button(frame, text=name, font=("Segoe UI",30,"bold"), width=20, height=2,
                      bg="#3182ce", fg="white", bd=0,
                      command=lambda c=code: self.show_football_submenu(c)).pack(pady=15)

        tk.Button(frame, text="Back", font=("Segoe UI",28), width=15,
                  command=self.show_main_menu).pack(pady=30)

    # ---------------- Football Submenu ----------------

    def show_football_submenu(self, league_code):
        self.current_league = league_code
        self.clear_frame()
        frame = tk.Frame(self.container, bg="#101010")
        frame.pack(expand=True)
        self.current_frame = frame

        tk.Label(frame, text="Football League Menu", fg="white", bg="#101010",
                 font=("Segoe UI",44,"bold")).pack(pady=40)

        tk.Button(frame, text="Fixtures", font=("Segoe UI",30,"bold"), width=20, height=2,
                  bg="#3182ce", fg="white",
                  command=lambda: self.show_scores("football", league_code)).pack(pady=20)

        tk.Button(frame, text="Table", font=("Segoe UI",30,"bold"), width=20, height=2,
                  bg="#2c7a7b", fg="white",
                  command=lambda: self.show_table(league_code)).pack(pady=20)

        tk.Button(frame, text="Back", font=("Segoe UI",28),
                  command=self.show_main_menu).pack(pady=40)

    # ---------------- Scores Display ----------------

    def show_scores(self, mode, league=None):
        self.mode = mode
        self.current_league = league
        self.clear_frame()
        frame = tk.Frame(self.container, bg="#101010")
        frame.pack(expand=True, fill="both")
        self.current_frame = frame

        self.scores_box = tk.Frame(frame, bg="#101010")
        self.scores_box.pack(expand=True, fill="both", padx=40, pady=40)

        tk.Button(frame, text="Back", font=("Segoe UI",28),
                  command=self.show_main_menu).pack(pady=20)

        self.update_scores()

    # ---------------- Table Display ----------------

    def show_table(self, league_code):
        self.clear_frame()

        frame = tk.Frame(self.container, bg="#101010")
        frame.pack(expand=True, fill="both")
        self.current_frame = frame

        title = tk.Label(
            frame,
            text="League Table",
            fg="white",
            bg="#101010",
            font=("Segoe UI", 44, "bold"),
        )
        title.pack(pady=(0, 20))

        self.scores_box = tk.Frame(frame, bg="#101010")
        self.scores_box.pack(expand=True, fill="both", padx=40, pady=40)

        bottom_bar = tk.Frame(frame, bg="#101010")
        bottom_bar.pack(side="bottom", pady=20)

        back_btn = tk.Button(
            bottom_bar,
            text="Back to league menu",
            font=("Segoe UI", 28, "bold"),
            bg="#4a5568",
            fg="white",
            bd=0,
            width=18,
            height=2,
            activebackground="#2d3748",
            activeforeground="white",
            command=self.show_main_menu,
        )
        back_btn.pack(side="left", padx=10)

        pages_box = tk.Frame(bottom_bar, bg="#101010")
        pages_box.pack(side="left", padx=30)

        page_size = 10

        def load_table():
            table = fetch_table(league_code)

            # Determine promotion and relegation ranges across full table
            positions = []
            for row in table:
                try:
                    positions.append(int(row["position"]))
                except Exception:
                    continue
            max_pos = max(positions) if positions else len(table)

            def row_bg(pos: int) -> str:
                # Top 4: promotion / Europe (green), bottom 3: relegation (red)
                if pos <= 4:
                    return "#22543d"  # greenish
                if pos > max_pos - 3:
                    return "#742a2a"  # reddish
                return "#1a202c"  # neutral dark row

            def render_page(page_index: int):
                # Clear current rows and page buttons
                for w in self.scores_box.winfo_children():
                    w.destroy()
                for w in pages_box.winfo_children():
                    w.destroy()

                if not table:
                    tk.Label(
                        self.scores_box,
                        text="Table data unavailable",
                        fg="white",
                        bg="#101010",
                        font=("Segoe UI", 28),
                    ).pack(pady=40)
                    return

                # Headers
                headers = ["Pos", "Team", "GP", "W", "D", "L", "Pts", "Last 5"]
                for col, text in enumerate(headers):
                    tk.Label(
                        self.scores_box,
                        text=text,
                        fg="#cbd5f5",
                        bg="#101010",
                        font=("Segoe UI", 22, "bold"),
                        anchor="w",
                    ).grid(row=0, column=col, padx=8, pady=(0, 10), sticky="w")

                # Slice rows for this page
                start = page_index * page_size
                end = start + page_size
                page_rows = table[start:end]

                for r_index, row in enumerate(page_rows, start=1):
                    try:
                        pos_int = int(row["position"])
                    except Exception:
                        pos_int = 999

                    bg = row_bg(pos_int)
                    fg = "white"

                    # Position (global)
                    tk.Label(
                        self.scores_box,
                        text=str(row["position"]),
                        fg=fg,
                        bg=bg,
                        font=("Segoe UI", 22),
                        anchor="w",
                        width=4,
                    ).grid(row=r_index, column=0, padx=8, pady=4, sticky="w")

                    # Team name + logo
                    team_cell = tk.Frame(self.scores_box, bg=bg)
                    team_cell.grid(row=r_index, column=1, padx=8, pady=4, sticky="w")

                    logo_img = None
                    logo_url = row.get("logo_url")
                    if logo_url:
                        logo_img = self.get_logo(logo_url)
                    if logo_img:
                        tk.Label(team_cell, image=logo_img, bg=bg).pack(side="left", padx=(0, 8))

                    tk.Label(
                        team_cell,
                        text=row["team"],
                        fg=fg,
                        bg=bg,
                        font=("Segoe UI", 22),
                        anchor="w",
                    ).pack(side="left")

                    # Basic stats columns (already provided)
                    stats_values = [
                        str(row.get("played", 0)),
                        str(row["wins"]),
                        str(row["draws"]),
                        str(row["losses"]),
                        str(row["points"]),
                    ]

                    for c_offset, value in enumerate(stats_values):
                        col_index = 2 + c_offset
                        tk.Label(
                            self.scores_box,
                            text=value,
                            fg=fg,
                            bg=bg,
                            font=("Segoe UI", 22),
                            anchor="w",
                            width=4,
                        ).grid(row=r_index, column=col_index, padx=8, pady=4, sticky="w")

                    # Last 5 form as coloured dots
                    form_cell = tk.Frame(self.scores_box, bg=bg)
                    form_cell.grid(row=r_index, column=7, padx=8, pady=4, sticky="w")

                    last5 = row.get("last5") or []
                    for ch in (last5 + [""] * (5 - len(last5)))[:5]:
                        if ch == "W":
                            color = "#48bb78"  # green
                        elif ch == "L":
                            color = "#f56565"  # red
                        elif ch == "D":
                            color = "#a0aec0"  # grey
                        else:
                            color = "#4a5568"  # empty / unknown

                        tk.Label(
                            form_cell,
                            text="●",
                            fg=color,
                            bg=bg,
                            font=("Segoe UI", 20),
                        ).pack(side="left", padx=2)

                # Page buttons (1, 2, ...)
                total_rows = len(table)
                total_pages = max(1, math.ceil(total_rows / page_size))
                for i in range(total_pages):
                    is_current = i == page_index
                    tk.Button(
                        pages_box,
                        text=str(i + 1),
                        font=("Segoe UI", 26, "bold"),
                        width=3,
                        height=2,
                        bg="#3182ce" if is_current else "#4a5568",
                        fg="white",
                        bd=0,
                        activebackground="#2b6cb0",
                        activeforeground="white",
                        command=lambda p=i: render_page(p),
                    ).pack(side="left", padx=10)

            self.root.after(0, lambda: render_page(0))

        threading.Thread(target=load_table, daemon=True).start()

    # ---------------- Refresh Logic ----------------

    def update_scores(self):
        threading.Thread(target=self.load_scores, daemon=True).start()

    def load_scores(self):
        if self.mode == "football":
            matches = fetch_football_scores(self.current_league)
            self.root.after(0, lambda: self.display_matches(matches))
        elif self.mode == "speedway":
            lines = fetch_speedway_scores()
            self.root.after(0, lambda: self.display_speedway(lines))

    # ---------------- Display Helpers ----------------

    def display_matches(self, matches):
        for w in self.scores_box.winfo_children():
            w.destroy()
        for m in matches:
            row = tk.Frame(self.scores_box, bg="#101010")
            row.pack(pady=10)

            home_logo = self.get_logo(m["home_logo"])
            away_logo = self.get_logo(m["away_logo"])

            if home_logo:
                tk.Label(row, image=home_logo, bg="#101010").pack(side="left", padx=10)

            tk.Label(row, text=f"{m['home_name']} {m['home_score']} - {m['away_score']} {m['away_name']}",
                     fg="white", bg="#101010", font=("Segoe UI",28)).pack(side="left", padx=20)

            if away_logo:
                tk.Label(row, image=away_logo, bg="#101010").pack(side="left", padx=10)

        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        self._refresh_job = self.root.after(REFRESH_TIME, self.update_scores)

    def display_speedway(self, lines):
        for w in self.scores_box.winfo_children():
            w.destroy()
        if not lines:
            tk.Label(self.scores_box, text="No speedway results available",
                     fg="white", bg="#101010", font=("Segoe UI",28)).pack(pady=40)
        else:
            for idx, line in enumerate(lines, start=1):
                tk.Label(self.scores_box, text=f"#{idx} {line}",
                         fg="white", bg="#101010", font=("Segoe UI",28)).pack(anchor="w", pady=6)
        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        self._refresh_job = self.root.after(REFRESH_TIME, self.update_scores)

    # ---------------- Logo Cache ----------------

    def get_logo(self, url):
        if url in self.logo_cache:
            return self.logo_cache[url]
        logo = fetch_logo(url)
        if logo:
            self.logo_cache[url] = logo
        return logo

    # ---------------- Exit ----------------

    def confirm_exit(self):
        if messagebox.askyesno("Exit", "Exit Sports Mode?"):
            self.root.destroy()

    def confirm_shutdown(self):
        if messagebox.askyesno("Turn off", "Turn off this PC now?"):
            self.shutdown_pc()

    def run(self):
        self.root.mainloop()


# ---------------- Run App ----------------

def main():
    app = SportsModeApp()
    app.run()

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        main()
    else:
        print("Sports Mode is designed for Windows.")