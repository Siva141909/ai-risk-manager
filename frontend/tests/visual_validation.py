"""Phase 5B visual validation — captures every route at 1440/1280/1024px,
including all 5 demo cases, for manual inspection (docs/FRONTEND_ARCHITECTURE.md §6).
Run against already-running backend (127.0.0.1:8000) + frontend (5173)."""

import os
from playwright.sync_api import sync_playwright

OUT_DIR = "/tmp/phase5b_screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

BASE = "http://localhost:5173"
WIDTHS = [1440, 1280, 1024]

DEMO_CASES = [
    "CASE-3410549",  # strong_coordinated_ring
    "CASE-3452855",  # legitimate_household
    "CASE-3457202",  # ml_low_graph_high
    "CASE-3416834",  # conflicting_evidence
    "CASE-3400406",  # missing_data
]

ROUTES = [("overview", "/")] + [("queue", "/cases")]
for case_id in DEMO_CASES:
    ROUTES.append((f"investigation-{case_id}", f"/cases/{case_id}"))
    ROUTES.append((f"graph-{case_id}", f"/cases/{case_id}/graph"))
    ROUTES.append((f"report-{case_id}", f"/cases/{case_id}/report"))
ROUTES.append(("investigation-not-found", "/cases/CASE-999999999"))
ROUTES.append(("queue-filtered-critical", "/cases?risk_tier=CRITICAL"))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for width in WIDTHS:
        page = browser.new_page(viewport={"width": width, "height": 900})
        for name, path in ROUTES:
            page.goto(f"{BASE}{path}")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(300)
            out_path = f"{OUT_DIR}/{name}__{width}.png"
            page.screenshot(path=out_path, full_page=True)
            print(f"captured {out_path}")
        page.close()
    browser.close()

print("done")
