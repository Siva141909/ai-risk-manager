"""Phase 5B real-Claude end-to-end proof: drives the ACTUAL browser UI
(click Start Investigation), not a direct API call, against a backend
running RISK_MANAGER_LLM_BACKEND=claude_agent_sdk. Confirms
Frontend -> FastAPI -> frozen pipeline -> LangGraph -> Claude Agent SDK
-> InvestigationReport -> Frontend end-to-end, with a screenshot as
evidence, not just a claim."""

import time
from playwright.sync_api import sync_playwright

CASE_ID = "CASE-3457202"  # ml_low_graph_high, per docs/DEMO_FLOW.md step 3

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900})

    page.goto(f"http://localhost:5173/cases/{CASE_ID}")
    page.wait_for_load_state("networkidle")
    page.screenshot(path="/tmp/phase5b_screenshots/real_claude_before.png", full_page=True)

    start_button = page.get_by_role("button", name="Start Investigation").first
    assert start_button.is_visible(), "Start Investigation button not found"

    t0 = time.time()
    start_button.click()

    # Confirm the "Investigating..." state actually appears (no fake instant result)
    page.wait_for_selector("text=Investigating…", timeout=5000)
    page.screenshot(path="/tmp/phase5b_screenshots/real_claude_investigating.png", full_page=True)
    print("Investigating state confirmed visible")

    # Real Claude call: wait up to 90s for the investigating state to clear
    # (waiting for "AI Investigation" text is wrong -- that's also the
    # always-present card title, so it would match instantly).
    page.wait_for_selector("text=Investigating…", state="detached", timeout=90000)
    elapsed = time.time() - t0
    print(f"Investigation completed in {elapsed:.1f}s (browser-observed)")

    page.wait_for_timeout(300)
    page.screenshot(path="/tmp/phase5b_screenshots/real_claude_complete.png", full_page=True)

    # Pull the actual recommendation text + confidence + backend label for the report
    body_text = page.inner_text("body")
    print("--- contains 'STUB TEST' (should be False) ---")
    print("STUB TEST" in body_text)

    browser.close()

print("done")
