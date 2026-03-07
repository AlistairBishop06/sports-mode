import sys
import tkinter as tk
from tkinter import messagebox
import threading
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageTk
import io
import os

HEADERS = {"User-Agent": "Mozilla/5.0"}

LEAGUES = {
    "Premier League": "eng.1",
    "Championship": "eng.2",
    "League One": "eng.3",
    "League Two": "eng.4",
    "Champions League": "uefa.champions"
}

SPEEDWAY_URL = "https://britishspeedway.co.uk/results/"
REFRESH_TIME = 30000  # 30 seconds

# ---- Helper functions ----

def fetch_logo(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        img = Image.open(io.BytesIO(r.content))
        img = img.resize((40, 40))
        return ImageTk.PhotoImage(img)
    except:
        return None

def fetch_football_scores(league_code):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_code}/scoreboard"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
    except:
        return []

    matches = []
    for event in data.get("events", []):
        comp = event["competitions"][0]
        teams = comp["competitors"]
        home = next(t for t in teams if t["homeAway"] == "home")
        away = next(t for t in teams if t["homeAway"] == "away")
        matches.append({
            "home_name": home["team"]["displayName"],
            "away_name": away["team"]["displayName"],
            "home_score": home["score"],
            "away_score": away["score"],
            "home_logo": home["team"]["logo"],
            "away_logo": away["team"]["logo"],
            "status": event["status"]["type"]["shortDetail"]
        })
    return matches

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

# ---- Main App ----

class SportsModeApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sports Mode")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#101010")
        self.root.bind("<Escape>", lambda e: self.confirm_exit())

        self.container = tk.Frame(self.root, bg="#101010")
        self.container.pack(expand=True, fill="both", padx=40, pady=40)

        self.current_frame = None
        self.scores_box = None
        self.current_league = None
        self.mode = None
        self.logo_cache = {}

        self._refresh_job = None

        self.show_main_menu()

    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()

    def shutdown_pc(self):
        os.system("shutdown /s /t 0")

    # ---- Main Menu ----
    def show_main_menu(self):
        self.clear_frame()
        frame = tk.Frame(self.container, bg="#101010")
        frame.pack(expand=True)
        self.current_frame = frame

        title = tk.Label(frame,
                         text="Grandad's Sports Mode",
                         fg="white", bg="#101010",
                         font=("Segoe UI", 48, "bold"))
        title.pack(pady=40)

        btn_style = {"width": 18, "height": 3, "font": ("Segoe UI", 32, "bold"),
                     "bd": 0, "fg": "white"}

        football_btn = tk.Button(frame, text="Football", bg="#3182ce",
                                 command=self.show_football_leagues, **btn_style)
        football_btn.pack(pady=20)

        speedway_btn = tk.Button(frame, text="Speedway", bg="#d69e2e",
                                 command=lambda: self.show_scores("speedway"), **btn_style)
        speedway_btn.pack(pady=20)

        off_btn = tk.Button(frame, text="OFF", bg="#e53e3e", fg="white",
                            font=("Segoe UI", 36, "bold"), width=18, height=2,
                            command=self.shutdown_pc)
        off_btn.pack(pady=40)

    # ---- Football League Selection ----
    def show_football_leagues(self):
        self.clear_frame()
        frame = tk.Frame(self.container, bg="#101010")
        frame.pack(expand=True)
        self.current_frame = frame

        title = tk.Label(frame, text="Choose League",
                         fg="white", bg="#101010", font=("Segoe UI", 44, "bold"))
        title.pack(pady=40)

        for name, code in LEAGUES.items():
            btn = tk.Button(frame, text=name, font=("Segoe UI", 30, "bold"),
                            width=20, height=2, bg="#3182ce", fg="white", bd=0,
                            command=lambda c=code: self.show_scores("football", c))
            btn.pack(pady=15)

        back = tk.Button(frame, text="Back", font=("Segoe UI", 28), width=15,
                         command=self.show_main_menu)
        back.pack(pady=30)

    # ---- Scores Display ----
    def show_scores(self, mode, league=None):
        self.mode = mode
        self.current_league = league
        self.clear_frame()
        frame = tk.Frame(self.container, bg="#101010")
        frame.pack(expand=True, fill="both")
        self.current_frame = frame

        self.scores_box = tk.Frame(frame, bg="#101010")
        self.scores_box.pack(expand=True, fill="both", padx=40, pady=40)

        back = tk.Button(frame, text="Back", font=("Segoe UI", 28),
                         command=self.show_main_menu)
        back.pack(pady=20)

        self.update_scores()

    def update_scores(self):
        thread = threading.Thread(target=self.load_scores)
        thread.daemon = True
        thread.start()

    def load_scores(self):
        if self.mode == "football":
            matches = fetch_football_scores(self.current_league)
            self.root.after(0, lambda: self.display_matches(matches))
        else:
            lines = fetch_speedway_scores()
            self.root.after(0, lambda: self.display_speedway_tv(lines))

    # ---- Football Display ----
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
                     fg="white", bg="#101010", font=("Segoe UI", 28)).pack(side="left", padx=10)
            if away_logo:
                tk.Label(row, image=away_logo, bg="#101010").pack(side="left", padx=10)

        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        self._refresh_job = self.root.after(REFRESH_TIME, self.update_scores)

    # ---- Speedway TV-style Display ----
    def display_speedway_tv(self, lines):
        for w in self.scores_box.winfo_children():
            w.destroy()

        if not lines:
            tk.Label(self.scores_box, text="No speedway results available",
                     fg="white", bg="#101010", font=("Segoe UI", 28)).pack(pady=40)
        else:
            for idx, line in enumerate(lines, start=1):
                row = tk.Frame(self.scores_box, bg="#101010", pady=10)
                row.pack(fill="x")

                race_number = tk.Label(row, text=f"#{idx}", fg="#FFD700",
                                       bg="#101010", font=("Segoe UI", 28, "bold"), width=4)
                race_number.pack(side="left")

                race_label = tk.Label(row, text=line, fg="white", bg="#101010",
                                      font=("Segoe UI", 28), anchor="w")
                race_label.pack(side="left", fill="x", expand=True)

        if self._refresh_job:
            self.root.after_cancel(self._refresh_job)
        self._refresh_job = self.root.after(REFRESH_TIME, self.update_scores)

    # ---- Logo Caching ----
    def get_logo(self, url):
        if url in self.logo_cache:
            return self.logo_cache[url]

        logo = fetch_logo(url)
        if logo:
            self.logo_cache[url] = logo
        return logo

    # ---- Exit Confirmation ----
    def confirm_exit(self):
        if messagebox.askyesno("Exit", "Exit Sports Mode?"):
            self.root.destroy()

    def run(self):
        self.root.mainloop()


# ---- Run App ----
def main():
    app = SportsModeApp()
    app.run()


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        main()
    else:
        print("Sports Mode is designed for Windows.")