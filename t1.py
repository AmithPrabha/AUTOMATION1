import json
import re
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright
from seleniumbase import sb_cdp

URL = "https://visa.vfsglobal.com/are/en/jpn/login"
CREDENTIALS_FILE = Path(__file__).with_name("credentials.json")


def load_credentials():
    try:
        credentials = json.loads(CREDENTIALS_FILE.read_text())
    except (OSError, ValueError):
        raise SystemExit("Add your email and password to a valid credentials.json file.") from None
    if not isinstance(credentials, dict):
        raise SystemExit("credentials.json must contain an email and password object.")
    email = credentials.get("email")
    password = credentials.get("password")
    if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password:
        raise SystemExit("Fill in both email and password in credentials.json before running.")
    return email.strip(), password


def main():
    user_id, password = load_credentials()
    print("Starting Chrome...", flush=True)
    sb = sb_cdp.Chrome(headless=False)
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(sb.get_endpoint_url())
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            print(f"Opening {URL}", flush=True)
            try:
                response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
                print(f"Page: {page.title()}", flush=True)
                print(f"URL: {page.url}", flush=True)
                if response:
                    print(f"HTTP status: {response.status}", flush=True)
                try:
                    page.locator("#onetrust-reject-all-handler").click(timeout=5000)
                except PlaywrightTimeoutError:
                    pass  # The cookie banner may not appear.
                email_field = page.locator("#email")
                try:
                    email_field.wait_for(state="visible", timeout=15000)
                except PlaywrightTimeoutError:
                    print(
                        "Complete any Cloudflare verification in Chrome, "
                        "and the script will fill the login fields automatically.",
                        flush=True,
                    )
                    email_field.wait_for(state="visible", timeout=300000)
                email_field.fill(user_id)
                page.locator("#password").fill(password)
                password = None
                print(
                    "Login fields filled. Complete the Cloudflare checkbox "
                    "manually in Chrome. Waiting up to 5 minutes before signing in...",
                    flush=True,
                )
                # Observe completion only; the user performs the verification.
                try:
                    page.wait_for_function(
                        """() => {
                            const response = document.querySelector(
                                '[name="cf-turnstile-response"]'
                            );
                            return Boolean(response && response.value.trim());
                        }""",
                        timeout=300000,
                    )
                    page.get_by_role("button", name=re.compile(r"^sign\s*in$", re.I)).click(timeout=30000)
                    print("Sign In clicked. Check Chrome for the result or any additional verification.", flush=True)
                except PlaywrightTimeoutError:
                    print("Verification or Sign In was not ready in time. No further login attempt was made.", flush=True)
            finally:
                input("Browser is open for inspection. Press Enter to close it...")
    finally:
        sb.quit()


if __name__ == "__main__":
    main()
