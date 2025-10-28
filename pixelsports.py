import json
import requests
from datetime import datetime, timezone, timedelta

BASE = "https://pixelsport.tv"
API_EVENTS = f"{BASE}/backend/liveTV/events"
OUTPUT_FILE = "Pixelsports.m3u8"

VLC_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:144.0) Gecko/20100101 Firefox/144.0"
VLC_REFERER = f"{BASE}/"
VLC_ICY = "1"

LEAGUE_INFO = {
    "NFL": ("NFL.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Maxx.png", "NFL"),
    "MLB": ("MLB.Baseball.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Baseball3.png", "MLB"),
    "NHL": ("NHL.Hockey.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Hockey2.png", "NHL"),
    "NBA": ("NBA.Basketball.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Basketball-2.png", "NBA"),
    "NASCAR": ("Racing.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Motorsports2.png", "NASCAR Cup Series"),
    "UFC": ("UFC.Fight.Pass.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/CombatSports2.png", "UFC"),
    "SOCCER": ("Soccer.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Soccer.png", "Soccer"),
    "BOXING": ("PPV.EVENTS.Dummy.us", "http://drewlive24.duckdns.org:9000/Logos/Combat-Sports.png", "Boxing"),
}

def utc_to_eastern(utc_str):
    """Convert ISO UTC time string to Eastern Time (ET) and return formatted string."""
    try:
        utc_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00")).astimezone(timezone.utc)
        month = utc_dt.month
        offset = -4 if 3 <= month <= 11 else -5
        et = utc_dt + timedelta(hours=offset)
        return et.strftime("%I:%M %p ET - %m/%d/%Y").replace(" 0", " ")
    except Exception:
        return ""

def get_game_status(utc_str):
    """Determine game status and return status string."""
    try:
        utc_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00")).astimezone(timezone.utc)
        now = datetime.now(timezone.utc)
        
        time_diff = (utc_dt - now).total_seconds()
        
        # Game finished (assuming 3 hours duration)
        if time_diff < -10800:
            return "Finished"
        # Game started
        elif time_diff < 0:
            return "Started"
        # Game hasn't started - show countdown
        else:
            hours = int(time_diff // 3600)
            minutes = int((time_diff % 3600) // 60)
            if hours > 0:
                return f"In {hours}h {minutes}m"
            else:
                return f"In {minutes}m"
    except Exception:
        return ""

def fetch_json(url):
    """Fetch JSON data from a URL."""
    headers = {
        "User-Agent": VLC_USER_AGENT,
        "Referer": VLC_REFERER,
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": BASE,
    }
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[!] Error fetching data: {e}")
        raise

def collect_links_with_labels(event):
    """Collect valid stream URLs with home/away labels from an event."""
    links = []
    comp1_home = event.get("competitors1_homeAway", "").lower() == "home"
    
    for i in range(1, 4):
        key = f"server{i}URL"
        try:
            link = event["channel"][key]
            if link and link.lower() != "null":
                # Server 1 matches competitor 1, server 2 matches competitor 2
                if i == 1:
                    label = "Home" if comp1_home else "Away"
                elif i == 2:
                    label = "Away" if comp1_home else "Home"
                else:
                    label = "Alt"
                links.append((link, label))
        except KeyError:
            continue
    return links

def get_league_info(league_name):
    """Return tvg-id, logo, and formatted group name based on league name."""
    for key, (tvid, logo, display_name) in LEAGUE_INFO.items():
        if key.lower() in league_name.lower():
            return tvid, logo, display_name
    return ("Pixelsports.Dummy.us", "", "Live Sports")

def build_m3u(events):
    """Generate M3U8 playlist text with EXTVLCOPT headers and smart group titles."""
    lines = ["#EXTM3U"]
    for ev in events:
        title = ev.get("match_name", "Unknown Event").strip()
        logo = ev.get("competitors1_logo", "")
        date_str = ev.get("date")
        time_et = utc_to_eastern(date_str)
        status = get_game_status(date_str)
        
        if time_et:
            title = f"{title} - {time_et}"
        
        if status:
            title = f"{title} - {status}"

        league = ev.get("channel", {}).get("TVCategory", {}).get("name", "LIVE")
        tvid, group_logo, group_display = get_league_info(league)

        if not logo:
            logo = group_logo

        for link, label in collect_links_with_labels(ev):
            lines.append(f'#EXTINF:-1 tvg-id="{tvid}" tvg-logo="{logo}" group-title="Pixelsports - {group_display} - {label}",{title}')
            lines.append(f"#EXTVLCOPT:http-user-agent={VLC_USER_AGENT}")
            lines.append(f"#EXTVLCOPT:http-referrer={VLC_REFERER}")
            lines.append(f"#EXTVLCOPT:http-icy-metadata={VLC_ICY}")
            lines.append(link)
    return "\n".join(lines)

def main():
    print("[*] Fetching PixelSport live events…")
    try:
        data = fetch_json(API_EVENTS)
        events = data.get("events", [])
        if not events:
            print("[-] No live events found.")
            return

        playlist = build_m3u(events)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(playlist)

        print(f"[+] Saved playlist: {OUTPUT_FILE} ({len(events)} events)")
    except (URLError, HTTPError) as e:
        print(f"[!] Error fetching data: {e}")
    except Exception as e:
        print(f"[!] Unexpected error: {e}")

if __name__ == "__main__":
    main()
