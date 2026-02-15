import requests
import json
from datetime import datetime, timedelta
import sys
import os
import re
import textwrap

# --- CONFIGURATION ---
TIMETABLE_URL = "https://s3-ap-southeast-1.amazonaws.com/open-ws/weektimetable"
CALENDAR_ICS_URL = "https://calendar.google.com/calendar/ical/2n93erhbkek11ucdaak24tb6i8%40group.calendar.google.com/public/basic.ics"

HEADERS = {
    "Origin": "https://apspace.apu.edu.my",
    "Referer": "https://apspace.apu.edu.my/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- COLORS ---
os.system('') 
class Col:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    GREY = '\033[90m'
    END = '\033[0m'

class APSearch:
    def __init__(self):
        self.data = []
        self.all_physical_rooms = set()
        self.load_data()

    def load_data(self):
        print(f"{Col.GREY} [~] Initializing uplink...{Col.END}")
        try:
            r = requests.get(TIMETABLE_URL, headers=HEADERS, timeout=10)
            r.raise_for_status()
            self.data = r.json()
            print(f"{Col.GREEN} [OK] Database synced: {len(self.data)} nodes active.{Col.END}")
            
            for item in self.data:
                room = item.get('ROOM')
                if room and room != "N/A" and not self.is_online(room):
                    self.all_physical_rooms.add(room.strip())
                    
        except Exception as e:
            print(f"{Col.RED} [ERR] Critical failure: {e}{Col.END}")
            sys.exit(1)

    # --- UTILS ---
    def is_online(self, room_name):
        if not room_name: return False
        r = room_name.upper().strip()
        return r.startswith("ONL") or r.startswith("ONC") or "TEAMS" in r or "VIRTUAL" in r

    def parse_time(self, date_iso, time_iso):
        try:
            dt_str = f"{date_iso} {time_iso.split('T')[1].split('+')[0]}"
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except:
            return None

    def clean_room_name(self, user_input):
        q = user_input.lower().strip()
        match = re.search(r'(tl|tech\s*lab|t)\s*0?(\d+)[- ]0?(\d+)', q)
        if match: return f"Tech Lab {match.group(2)}-{match.group(3)}"
        if "aud" in q:
            num = re.search(r'\d+', q)
            if num: return f"Auditorium {num.group(0)}"
        if "cyber" in q or "cr" == q: return "Cyber Range"
        return user_input

    def get_current_status(self, target_time=None):
        if target_time is None: target_time = datetime.now()
        active, future = [], []
        for item in self.data:
            date_iso = item.get('DATESTAMP_ISO')
            if not date_iso: continue
            
            start_dt = self.parse_time(date_iso, item.get('TIME_FROM_ISO'))
            end_dt = self.parse_time(date_iso, item.get('TIME_TO_ISO'))
            
            if start_dt and end_dt:
                item['_start_dt'] = start_dt
                item['_end_dt'] = end_dt
                
                if start_dt <= target_time < end_dt:
                    active.append(item)
                elif start_dt > target_time:
                    future.append(item)
        return active, future, target_time

    # --- ADVANCED TABLE PRINTER (WRAPPING) ---
    def print_table(self, headers, rows, col_widths):
        """
        Prints a table where cells wrap to new lines instead of truncating.
        rows: List of lists containing (text, color_code)
        """
        # Print Header
        header_str = " | ".join([f"{h:<{w}}" for h, w in zip(headers, col_widths)])
        print(f"\n {Col.BOLD}{header_str}{Col.END}")
        print(" " + "-" * (sum(col_widths) + 3 * (len(col_widths) - 1)))

        for row in rows:
            # 1. Wrap content for each cell
            wrapped_cells = []
            for (text, color), width in zip(row, col_widths):
                lines = textwrap.wrap(str(text), width) if text else [""]
                wrapped_cells.append((lines, color))
            
            # 2. Find max height of this row
            max_height = max(len(w[0]) for w in wrapped_cells) if wrapped_cells else 0
            
            # 3. Print line by line
            for i in range(max_height):
                print(" ", end="")
                for idx, ((lines, color), width) in enumerate(zip(wrapped_cells, col_widths)):
                    content = lines[i] if i < len(lines) else ""
                    # Apply color only to the text, maintain padding
                    print(f"{color}{content:<{width}}{Col.END}", end="")
                    if idx < len(col_widths) - 1:
                        print(f" {Col.GREY}|{Col.END} ", end="")
                print() # Newline
            print(f"{Col.GREY} " + "-" * (sum(col_widths) + 3 * (len(col_widths) - 1)) + f"{Col.END}")

    # --- ICS PARSER ---
    def parse_ics_date(self, date_str):
        try:
            clean = date_str.strip()
            if 'T' in clean:
                dt = datetime.strptime(clean.split('Z')[0], "%Y%m%dT%H%M%S")
                return dt + timedelta(hours=8)
            else:
                return datetime.strptime(clean, "%Y%m%d")
        except:
            return None

    def fetch_events(self):
        print(f"\n{Col.CYAN}--- Syncing Student Affairs Calendar... ---{Col.END}")
        try:
            r = requests.get(CALENDAR_ICS_URL, timeout=5)
            r.raise_for_status()
            ics_data = r.text
        except:
            print(f"{Col.RED} [!] Offline Mode.{Col.END} (Check studentaffairs.apu.edu.my)")
            return

        events = []
        lines = ics_data.splitlines()
        current_event = {}
        in_event = False

        for line in lines:
            if line.startswith("BEGIN:VEVENT"):
                in_event = True
                current_event = {}
            elif line.startswith("END:VEVENT"):
                in_event = False
                if 'SUMMARY' in current_event and 'DTSTART' in current_event:
                    events.append(current_event)
            elif in_event:
                if line.startswith("SUMMARY:"):
                    current_event['SUMMARY'] = line.split(":", 1)[1]
                elif line.startswith("DTSTART"):
                    val = line.split(":", 1)[1]
                    current_event['DTSTART'] = self.parse_ics_date(val)
                    current_event['ALL_DAY'] = 'T' not in val

        now = datetime.now()
        upcoming = [e for e in events if e.get('DTSTART') and e['DTSTART'].date() >= now.date()]
        upcoming.sort(key=lambda x: x['DTSTART'])
        
        # Prepare Table Data
        headers = ["DATE", "EVENT DETAILS"]
        widths = [18, 50]
        rows = []
        
        for e in upcoming[:10]:
            dt = e['DTSTART']
            d_str = dt.strftime("%d %b (All Day)") if e.get('ALL_DAY') else dt.strftime("%d %b, %I:%M%p")
            color = Col.YELLOW if "Holiday" in e['SUMMARY'] else Col.END
            rows.append([(d_str, color), (e['SUMMARY'], Col.END)])
            
        print(f"{Col.GREEN} [V] Synced.{Col.END}")
        self.print_table(headers, rows, widths)

    # --- FEATURES ---

    def find_lecturer(self, name_query):
        print(f"\n{Col.CYAN}--- Tracking: '{name_query}' ---{Col.END}")
        active, future, now = self.get_current_status()
        
        # 1. Find Current Status
        active_matches = [c for c in active if name_query.upper() in c.get('NAME', '').upper()]
        
        # 2. Find Future Matches
        future_matches = [c for c in future if name_query.upper() in c.get('NAME', '').upper()]
        future_matches.sort(key=lambda x: x['_start_dt'])

        if active_matches:
            print(f"{Col.GREEN} [!] TARGET FOUND (ONLINE/ACTIVE){Col.END}")
            # Use deduplication by room/time
            seen = set()
            for cls in active_matches:
                uid = f"{cls['NAME']}-{cls['ROOM']}"
                if uid in seen: continue
                seen.add(uid)
                
                room = cls.get('ROOM')
                status = "ONLINE" if self.is_online(room) else "PHYSICAL"
                color = Col.CYAN if status == "ONLINE" else Col.RED
                
                print(f"     Name:   {Col.BOLD}{cls.get('NAME')}{Col.END}")
                print(f"     Status: {color}CURRENTLY TEACHING ({status}){Col.END}")
                print(f"     Loc:    {Col.YELLOW}{room}{Col.END}")
                print(f"     Class:  {cls.get('MODULE_NAME')}")
                print(f"     Ends:   {cls.get('TIME_TO')}")
                print("     " + "-"*30)
        else:
            print(f"{Col.YELLOW} [i] Target is currently FREE.{Col.END}")

        # 3. Always Show Next Class (Context is King)
        if future_matches:
            nxt = future_matches[0]
            start_diff = (nxt['_start_dt'] - now).total_seconds() / 60
            
            print(f"\n {Col.BOLD}UPCOMING SCHEDULE:{Col.END}")
            if start_diff < 30:
                 print(f"{Col.RED} [!] STARTING SOON (in {int(start_diff)} mins){Col.END}")
            
            day = nxt['_start_dt'].strftime("%a %d")
            time = nxt.get('TIME_FROM')
            print(f" [>] {Col.CYAN}{day} @ {time}{Col.END} in {Col.YELLOW}{nxt.get('ROOM')}{Col.END}")
            print(f"     {nxt.get('MODULE_NAME')}")

    def find_empty_venues(self):
        print(f"\n{Col.CYAN}--- Scanning Sector for Empty Venues ---{Col.END}")
        active, future, now = self.get_current_status()
        
        busy = set(c.get('ROOM').strip() for c in active)
        empty = list(self.all_physical_rooms - busy)
        
        results = []
        for room in empty:
            next_start = None
            for f in future:
                if f.get('ROOM').strip() == room:
                    if next_start is None or f['_start_dt'] < next_start:
                        next_start = f['_start_dt']
            
            if next_start:
                diff = next_start - now
                mins = int(diff.total_seconds() // 60)
                dur_str = f"{mins//60}h {mins%60}m"
                sort_val = mins
                until = next_start.strftime("%I:%M%p")
            else:
                dur_str = "All Day"
                sort_val = 9999
                until = "Tmrw"
            results.append({'r': room, 'd': dur_str, 'u': until, 'v': sort_val})

        results.sort(key=lambda x: x['v'], reverse=True)
        
        # Prepare Table
        headers = ["ROOM", "FREE FOR", "UNTIL"]
        widths = [25, 15, 10]
        rows = []
        
        for x in results[:15]:
            c = Col.GREEN if x['v'] > 60 else Col.YELLOW
            rows.append([(x['r'], Col.BOLD), (x['d'], c), (x['u'], Col.END)])

        print(f"{Col.GREEN} [V] {len(empty)} venues available.{Col.END}")
        self.print_table(headers, rows, widths)

    def inspect_room(self, user_input):
        q = self.clean_room_name(user_input)
        print(f"\n{Col.CYAN}--- Inspecting Node: '{q}' ---{Col.END}")
        active, future, now = self.get_current_status()
        
        found = False
        for cls in active:
            if q.upper() in str(cls.get('ROOM')).upper():
                print(f"{Col.RED} [!] OCCUPIED{Col.END}")
                print(f"     Class:    {cls.get('MODULE_NAME')}")
                print(f"     Lecturer: {cls.get('NAME')}")
                print(f"     Ends:     {Col.BOLD}{cls.get('TIME_TO')}{Col.END}")
                found = True
        
        if not found:
            upcoming = [f for f in future if q.upper() in str(f.get('ROOM')).upper()]
            if upcoming:
                upcoming.sort(key=lambda x: x['_start_dt'])
                nxt = upcoming[0]
                diff = nxt['_start_dt'] - now
                mins = int(diff.total_seconds() // 60)
                print(f"{Col.GREEN} [V] EMPTY. Free for {mins//60}h {mins%60}m.{Col.END}")
                print(f"     Next: {nxt.get('TIME_FROM')} ({nxt.get('MODULE_NAME')})")
            else:
                print(f"{Col.GREEN} [V] EMPTY for the rest of the day.{Col.END}")

    def find_intake(self, intake_query):
        print(f"\n{Col.CYAN}--- Tracking Intake: '{intake_query}' ---{Col.END}")
        active, future, _ = self.get_current_status()
        found = False
        seen = set()
        
        for cls in active:
            if intake_query.upper() in cls.get('INTAKE', '').upper():
                if cls.get('MODULE_NAME') in seen: continue
                seen.add(cls.get('MODULE_NAME'))
                room = cls.get('ROOM')
                c = Col.CYAN if self.is_online(room) else Col.RED
                print(f"{Col.GREEN} [!] SESSION ACTIVE{Col.END}")
                print(f"     Subject:  {cls.get('MODULE_NAME')}")
                print(f"     Location: {c}{room}{Col.END}")
                found = True
        
        if not found:
            print(f"{Col.GREEN} [V] No active sessions.{Col.END}")
            upcoming = [c for c in future if intake_query.upper() in c.get('INTAKE', '').upper()]
            if upcoming:
                upcoming.sort(key=lambda x: x['_start_dt'])
                nxt = upcoming[0]
                print(f" [>] NEXT: {nxt.get('TIME_FROM')} ({nxt.get('ROOM')})")

    def discovery_mode(self, keyword):
        print(f"\n{Col.CYAN}--- Global Search: '{keyword}' ---{Col.END}")
        active, _, _ = self.get_current_status()
        keyword = keyword.upper()
        
        headers = ["TIME", "ROOM", "MODULE"]
        widths = [10, 20, 40]
        rows = []
        
        seen = set()
        for cls in active:
            blob = str(cls.values()).upper()
            if keyword in blob:
                uid = f"{cls.get('ROOM')}-{cls.get('MODULE_NAME')}"
                if uid in seen: continue
                seen.add(uid)
                
                rows.append([
                    (cls.get('TIME_FROM'), Col.END),
                    (cls.get('ROOM'), Col.CYAN if self.is_online(cls.get('ROOM')) else Col.YELLOW),
                    (cls.get('MODULE_NAME'), Col.END)
                ])

        if not rows:
            print(f" No active matches found.")
        else:
            self.print_table(headers, rows, widths)

# --- MAIN MENU ---
def main():
    app = APSearch()
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"""{Col.CYAN}
    █   █▀▀█ █▀▀ █▀▀ █▀▀█ █▀▀█ █▀▀ █   █
   █ █  █▄▄█ ▀▀█ █▀▀ █▄▄█ █▄▄▀ █   █▄▄▄█
  █   █ █    ▀▀▀ ▀▀▀ ▀  ▀ ▀  ▀ ▀▀▀ █   █ {Col.END}{Col.GREY}v7.0{Col.END}
  {Col.YELLOW}>> UNIVERSAL APU STUDENT INTELLIGENCE TOOL <<{Col.END}
  ------------------------------------------------
  {Col.BOLD}1.{Col.END} Find Lecturer    {Col.GREY}[Who is free?]{Col.END}
  {Col.BOLD}2.{Col.END} Empty Venues     {Col.GREY}[Chill Spots]{Col.END}
  {Col.BOLD}3.{Col.END} Inspect Room     {Col.GREY}[Scan: 'tl4-03']{Col.END}
  {Col.BOLD}4.{Col.END} Track Intake     {Col.GREY}[Locate Batch]{Col.END}
  {Col.BOLD}5.{Col.END} Global Search    {Col.GREY}[Keyword]{Col.END}
  {Col.BOLD}6.{Col.END} Events           {Col.GREY}[Live Calendar]{Col.END}
  {Col.BOLD}Q.{Col.END} Quit
        """)
        
        choice = input(f"{Col.CYAN}apsearch@{os.environ.get('USERNAME', 'user')}~${Col.END} ").strip().lower()
        
        if choice == '1':
            app.find_lecturer(input("Lecturer Name: "))
        elif choice == '2':
            app.find_empty_venues()
        elif choice == '3':
            app.inspect_room(input("Room ID: "))
        elif choice == '4':
            app.find_intake(input("Intake Code: "))
        elif choice == '5':
            app.discovery_mode(input("Query: "))
        elif choice == '6':
            app.fetch_events()
        elif choice == 'q':
            print("System offline.")
            break
        
        input(f"\n{Col.GREY}[PRESS ENTER TO CONTINUE]{Col.END}")

if __name__ == "__main__":
    main()