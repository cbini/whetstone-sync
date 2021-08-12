import os

from dotenv import load_dotenv

load_dotenv()

WHETSTONE_DISTRICT_ID = os.getenv("WHETSTONE_DISTRICT_ID")

ENDPOINTS = [
    {"path": "roles", "params": {"district": WHETSTONE_DISTRICT_ID}},
    {"path": "informals"},
    {"path": "measurements"},
    {"path": "meetings"},
    {"path": "rubrics"},
    {"path": "schools"},
    {"path": "videos"},
    {"path": "users"},
    {"path": "lessonplans/forms"},
    {"path": "lessonplans/groups"},
    {"path": "lessonplans/reviews"},
    {"path": "assignments"},
    {"path": "observations"},
    {"path": "roles", "params": {"district": WHETSTONE_DISTRICT_ID, "archived": True}},
    {"path": "informals", "params": {"archived": True}},
    {"path": "measurements", "params": {"archived": True}},
    {"path": "meetings", "params": {"archived": True}},
    {"path": "rubrics", "params": {"archived": True}},
    {"path": "schools", "params": {"archived": True}},
    {"path": "videos", "params": {"archived": True}},
    {"path": "users", "params": {"archived": True}},
    {"path": "lessonplans/forms", "params": {"archived": True}},
    {"path": "lessonplans/groups", "params": {"archived": True}},
    {"path": "lessonplans/reviews", "params": {"archived": True}},
    {"path": "assignments", "params": {"archived": True}},
    {"path": "observations", "params": {"archived": True}},
]
