# APSearch 🔍

**APSearch** is a terminal-based "Student Intelligence Tool" specifically designed for Asia Pacific University (APU) students. It provides real-time visibility into campus resource availability by syncing directly with live timetable data and student event calendars.

---

## 🛠 Key Features

* **Lecturer Tracking:** Search for a lecturer by name to see if they are currently teaching, their physical/online location, and when their next session starts.
* **Empty Venue Scanner:** Instantly identifies available physical rooms on campus, sorted by duration (how long they stay free).
* **Room Inspection:** Deep-scan specific nodes like Tech Labs, Auditoriums, or the Cyber Range to check current occupancy and upcoming schedules.
* **Intake Tracking:** Quickly locate specific student batches/intakes to find their active session locations.
* **Global Search:** A keyword-based discovery engine to find specific modules, subjects, or keywords across all active sessions.
* **Live Events:** Syncs with the APU Student Affairs Google Calendar to display upcoming events and public holidays.

---

## 🏗 Technical Architecture

### Data Sourcing
* **Timetable:** Fetches live JSON data from the APU S3-hosted weekly timetable API.
* **Calendar:** Parses `.ics` (iCalendar) files from the Student Affairs public feed.

### Core Logic
* **Time Normalization:** Handles ISO date-time parsing and localizes to **UTC+8 (Malaysia Time)**.
* **Intelligent Parsing:** Features a regex-based cleaning engine to resolve room shorthand (e.g., converting "tl4" or "t4" into "Tech Lab 4-03").
* **Terminal UI:** Custom-built TUI using ANSI escape codes for a "hacker-style" aesthetic and `textwrap` for dynamic table formatting.

---

## 🚀 Installation & Usage

### Prerequisites
* Python 3.x
* `requests` library

```bash
pip install requests
