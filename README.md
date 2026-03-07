# Sports Mode for Grandad

This is a very simple **full‑screen launcher** with **huge buttons** so your grandad only needs to tap:

- **Sky Football**
- **Speedway**
- **Exit Sports Mode**

When you click a sport, Windows opens the pre‑configured website or app for that sport. The main window stays simple and uncluttered.

---

## 1. Requirements

- **Windows 10 or later**
- **Python 3.10+** installed from the Microsoft Store or `python.org`.

You do **not** need to install any extra Python packages.

---

## 2. How to run Sports Mode

1. Open this folder in VS Code / Cursor:  
   `c:\Users\alist\Documents\VSCode\sports mode`
2. Open a terminal in this folder.
3. Run:

   ```bash
   python sports_mode.py
   ```

4. The screen should go **full‑screen black** with **three big buttons**.
5. To **exit quickly** (for you or hospital staff), press **ESC** on the keyboard, or use the **Exit Sports Mode** button.

You can also create a **desktop shortcut** that runs:

```text
python "c:\Users\alist\Documents\VSCode\sports mode\sports_mode.py"
```

so it’s just a double‑click.

---

## 3. Configure the actual sports streams

Open `sports_mode.py` and look for the section near the top:

```python
SKY_FOOTBALL_URL = "https://www.skysports.com/watch/sky-sports-football"
SPEEDWAY_URL = "https://www.discoveryplus.com/gb/sport/motorsport"

SKY_FOOTBALL_APP_CMD = None
SPEEDWAY_APP_CMD = None
```

- **If you watch via the browser**  
  - Log into the service in your normal browser.  
  - Go to the page that starts the live football / speedway.  
  - Copy the URL from the address bar.  
  - Paste it into `SKY_FOOTBALL_URL` or `SPEEDWAY_URL`.

- **If you have a native Windows app (e.g. Sky Go)**  
  - Find the `.exe` path (right‑click → Properties on the shortcut).  
  - Paste the full path into `SKY_FOOTBALL_APP_CMD` or `SPEEDWAY_APP_CMD`, for example:

    ```python
    SKY_FOOTBALL_APP_CMD = r"C:\Program Files\Sky\SkyGo\SkyGo.exe"
    ```

The app will **prefer launching the native app** if `*_APP_CMD` is set; otherwise it falls back to the browser URL.

---

## 4. Using it with your grandad

- **You (or staff) do the fiddly bits once**:
  - Make sure you’re logged into Sky / Discovery+ / etc. in the default browser, or that the native app is logged in.
  - Test each button to confirm it opens the right thing.
- After that, your grandad just:
  1. Starts **Sports Mode** (or you open it for him).
  2. Presses **one big button** for the sport he wants.

If you want to go further and truly **lock down Windows** (so he can’t accidentally close things or open other apps), that requires Windows kiosk mode / parental controls and is a separate OS‑level setup.

