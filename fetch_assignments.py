import os
import json
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("CANVAS_TOKEN")
DOMAIN = os.getenv("CANVAS_DOMAIN")
headers = {"Authorization": f"Bearer {TOKEN}"}

def get_paginated(url, params):
    results = []
    while url:
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        results.extend(r.json())
        url = r.links.get("next", {}).get("url")
        params = None  # the next URL already includes the params
    return results

def get_active_courses():
    return get_paginated(f"https://{DOMAIN}/api/v1/courses",
                          {"enrollment_state": "active", "per_page": 100})

def get_assignments(course_id):
    return get_paginated(f"https://{DOMAIN}/api/v1/courses/{course_id}/assignments",
                          {"per_page": 100, "order_by": "due_at", "bucket": "future"})

def main():
    now = datetime.now(timezone.utc)
    courses = get_active_courses()

    all_assignments = []
    for course in courses:
        if course.get("access_restricted_by_date"):
            continue
        course_name = course.get("name", "Unnamed course")
        course_id = course.get("id")

        assignments = get_assignments(course_id)
        for a in assignments:
            due = a.get("due_at")
            if not due:
                continue
            due_dt = datetime.fromisoformat(due.replace("Z", "+00:00"))
            days_out = (due_dt - now).days
            if 0 <= days_out <= 60:
                all_assignments.append({
                    "course": course_name,
                    "title": a.get("name"),
                    "due_at": due,
                    "points": a.get("points_possible"),
                    "days_until_due": days_out,
                })

    all_assignments.sort(key=lambda x: x["due_at"])

    with open("assignments.json", "w") as f:
        json.dump(all_assignments, f, indent=2)

    print(f"\nSaved {len(all_assignments)} upcoming assignment(s) to assignments.json\n")
    for a in all_assignments:
        print(f"[{a['days_until_due']}d] {a['course']} — {a['title']} ({a['points']} pts)")

if __name__ == "__main__":
    main()
