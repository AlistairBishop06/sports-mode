# ⚽ Sports Mode

A fullscreen, touchscreen-friendly sports dashboard for Windows. Built with Python and tkinter, it shows live football scores, fixtures, league tables, and British Speedway results — all pulled from live data, no subscriptions needed.

---

## Features

### 🏟 Football
- **Fixtures & Scores** — shows all matches for the selected league, laid out in a 2-column card grid. Each card displays:
  - Home and away team names with club logos
  - Score (or kickoff time for upcoming games)
  - Match status: 🔴 **LIVE** with minute, 🕐 **Upcoming** with kickoff time, or ✔ **Full Time**
  - Live cards refresh automatically every 30 seconds
- **League Table** — full standings with position, games played, wins, draws, losses, points, and last 5 form indicators (colour-coded W/D/L squares). Paginated in groups of 10.

### Supported Leagues
| League | Code |
|---|---|
| Premier League | eng.1 |
| Championship | eng.2 |
| League One | eng.3 |
| League Two | eng.4 |
| Champions League | uefa.champions |

### 🏍 Speedway
- Latest British Speedway results pulled from the official British Speedway website, displayed in a 2-column grid.

### General
- Fullscreen with no window chrome — ideal for a TV or touchscreen
- Large buttons throughout, designed for fat fingers and touchscreens
- "Please wait..." animated loading indicator while data fetches
- Turn off PC button on the main menu (shuts down Windows immediately)
- Alt + Escape to exit the app

---

## Requirements

- **Windows** (the app will not run on macOS or Linux — this is intentional, as the shutdown button uses `shutdown /s /t 0`)
- **Python 3.8+**

### Python dependencies

Install with pip:

```
pip install requests Pillow
```

`tkinter` comes bundled with Python on Windows — no separate install needed.

---

## Running the app

```
python sports_mode.py
```

The app launches fullscreen immediately. To exit, press **Alt + Escape** or use the Turn Off button on the main menu.

---

## Customisation

### Adding or removing leagues

Edit the `LEAGUES` dictionary near the top of `sports_mode.py`:

```python
LEAGUES = {
    "Premier League": "eng.1",
    "Championship":   "eng.2",
    "League One":     "eng.3",
    "League Two":     "eng.4",
    "Champions League": "uefa.champions"
}
```

The key is the display name shown on the button. The value is the ESPN league code. Some other codes you can use:

| League | Code |
|---|---|
| La Liga | esp.1 |
| Bundesliga | ger.1 |
| Serie A | ita.1 |
| Ligue 1 | fra.1 |
| Scottish Premiership | sco.1 |

### Adjusting the refresh rate

Change `REFRESH_TIME` (in milliseconds) near the top of the file:

```python
REFRESH_TIME = 30000  # 30 seconds — change to 60000 for 1 minute
```

### Timezone for kickoff times

Kickoff times are converted from UTC. The offset is set to +1 (BST). In winter (GMT), change the `hours=1` to `hours=0`:

```python
dt_local = dt_utc + timedelta(hours=1)   # change to hours=0 in winter
```

---

## Data sources

All data is fetched from free, public APIs — no API keys required:

- **Football scores, fixtures & tables** — [ESPN API](https://site.api.espn.com) (`site.api.espn.com`)
- **Speedway results** — [British Speedway](https://www.britishspeedway.co.uk) WordPress REST API

---

## How the form guide works

The last 5 results column in the league table is built by fetching the scoreboard for the past 10 weeks using a date range query. Results are matched to teams by display name and the last 5 completed results per team are shown as coloured squares:

| Square | Meaning |
|---|---|
| 🟩 **W** | Win |
| 🟥 **L** | Loss |
| ⬜ **D** | Draw |
| dim `–` | No data yet |

---

## File structure

```
sports_mode.py   — the entire application (single file)
README.md        — this file
```

---

## Troubleshooting

**Table shows "Table data unavailable"**
The ESPN standings endpoint structure occasionally changes. The app tries two different JSON paths automatically. If it still fails, check your internet connection first.

**Form guide shows all empty slots**
The date-range scoreboard query fell back to week-by-week fetching. This can happen at the start of a season when few games have been played, or if the ESPN API is temporarily slow. It will populate as results come in.

**Logos not showing**
Logo images are fetched from ESPN's CDN and cached in memory. If the first load is slow, they will appear once downloaded. They do not persist between app restarts.

**Kickoff times are wrong**
The app adds 1 hour to UTC for BST. In winter (October–March), edit `hours=1` to `hours=0` in the `fetch_football_scores` function.

**The app won't start on macOS/Linux**
This is by design. The app uses Windows-specific shutdown commands. The check at the bottom of the file prevents it from running on other platforms.
