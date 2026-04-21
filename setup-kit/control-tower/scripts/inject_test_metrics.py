"""
Inject synthetic metric data for smoke testing.
"""
import os
from datetime import datetime, timezone
from supabase import create_client

db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

METRICS = [
    ("leads_per_day",         12.0,    "manual"),
    ("demo_conv_rate",         0.13,   "manual"),
    ("signup_to_demo_rate",    0.25,   "manual"),
    ("trial_to_paid_rate",     0.09,   "manual"),
    ("mrr_inr",            50000.0,    "manual"),
    ("mrr_weekly_delta_inr", -2000.0,  "manual"),
    ("churn_rate_30d",         0.06,   "manual"),
    ("landing_bounce_rate",    0.68,   "manual"),
    ("demos_booked_today",     4.0,    "manual"),
    ("new_signups_7d",        35.0,    "manual"),
    ("active_trials",         18.0,    "manual"),
    ("paying_users",          52.0,    "manual"),
    ("tasks_completed_today",  3.0,    "manual"),
]

def main():
    inserted = 0
    for key, value, source in METRICS:
        try:
            db.table("metrics").insert({
                "key": key,
                "value": value,
                "source": source,
                "metadata": {"injected_by": "inject_test_metrics.py"},
            }).execute()
            inserted += 1
        except Exception as e:
            print(f"Error inserting {key}: {e}")
    print(f"Injected {inserted} metric rows")

if __name__ == "__main__":
    main()
