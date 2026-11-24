#!/usr/bin/env python3
"""Erstellt Commits für beliebige Tage (auch in der Vergangenheit).

Beispiele:
  python3 scripts/backfill.py --start 2026-11-20
  python3 scripts/backfill.py --start 2026-11-01 --end 2026-11-15 --count 2-8
  python3 scripts/backfill.py --start 2026-10-01 --end 2026-10-31 --count 5 --skip-weekends
  python3 scripts/backfill.py --start 2026-11-20 --dry-run      # nur anzeigen

Danach: git push
"""
import argparse
import os
import random
import subprocess
import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

WORDS = ["update", "tweak", "refactor", "cleanup", "notes", "log", "tidy", "adjust", "polish", "sync"]
MAX_TOTAL = 5000


def parse_count(text):
    text = text.strip()
    if "-" in text:
        lo, hi = (int(x) for x in text.split("-", 1))
    else:
        lo = hi = int(text)
    if lo < 0 or hi < lo:
        raise ValueError(f"Ungültige Anzahl: {text!r} (z. B. 5 oder 2-8)")
    return lo, hi


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--start", required=True, help="Erster Tag, JJJJ-MM-TT")
    p.add_argument("--end", help="Letzter Tag, JJJJ-MM-TT (Standard: wie --start)")
    p.add_argument("--count", default="1-5", help="Commits pro Tag: Zahl oder Bereich, z. B. 5 oder 2-8 (Standard 1-5)")
    p.add_argument("--skip-weekends", action="store_true", help="Samstag und Sonntag auslassen")
    p.add_argument("--message", default="", help="Eigene Commit-Nachricht (sonst zufälliges Wort)")
    p.add_argument("--tz", default="Europe/Berlin", help="Zeitzone für die Uhrzeiten (Standard Europe/Berlin)")
    p.add_argument("--from-hour", type=int, default=9, help="Früheste Uhrzeit (Standard 9)")
    p.add_argument("--to-hour", type=int, default=20, help="Späteste Uhrzeit (Standard 20)")
    p.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nichts committen")
    a = p.parse_args()

    try:
        start = date.fromisoformat(a.start)
        end = date.fromisoformat(a.end) if a.end else start
        lo, hi = parse_count(a.count)
        tz = ZoneInfo(a.tz)
    except Exception as e:
        sys.exit(f"Fehler: {e}")
    if end < start:
        sys.exit("Fehler: --end liegt vor --start")
    if not (0 <= a.from_hour <= a.to_hour <= 23):
        sys.exit("Fehler: Uhrzeiten müssen 0-23 sein und from-hour <= to-hour")

    plan = []
    day = start
    while day <= end:
        if not (a.skip_weekends and day.weekday() >= 5):
            n = random.randint(lo, hi)
            secs = sorted(random.randint(a.from_hour * 3600, a.to_hour * 3600 + 3599) for _ in range(n))
            for s in secs:
                t = time(s // 3600, (s % 3600) // 60, s % 60)
                plan.append(datetime.combine(day, t, tzinfo=tz))
        day += timedelta(days=1)

    if len(plan) > MAX_TOTAL:
        sys.exit(f"Fehler: {len(plan)} Commits geplant, Maximum ist {MAX_TOTAL}. Zeitraum oder Anzahl verkleinern.")

    days_used = len({d.date() for d in plan})
    print(f"{len(plan)} Commits an {days_used} Tagen ({start} bis {end}).")
    if a.dry_run:
        for d in plan:
            print("  ", d.isoformat())
        return

    os.makedirs("logs", exist_ok=True)
    for i, d in enumerate(plan, 1):
        stamp = d.isoformat()
        word = random.choice(WORDS)
        f = f"logs/{d:%Y-%m}.md"
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(f"- {d:%Y-%m-%d %H:%M:%S} {word} #{i} {random.randint(0, 10**9)}\n")
        msg = a.message or f"{word}: entry {i} ({d:%Y-%m-%d})"
        env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
        subprocess.run(["git", "add", f], check=True)
        subprocess.run(["git", "commit", "-q", "-m", msg], check=True, env=env)
    print("Fertig. Jetzt pushen: git push")


if __name__ == "__main__":
    main()
