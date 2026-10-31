# VFS login automation — technical walkthrough

## Overview

This Python script opens the VFS Japan login page for applicants in the UAE, reads credentials from a local JSON file, fills the login form, waits for the user to complete Cloudflare verification, and clicks **Sign In**. The browser stays open so the user can inspect the result.

The implemented scope ends at submitting the login form. The script does not confirm successful authentication, handle OTPs, search for appointments, or book appointments.

### A short explanation to share

“We use SeleniumBase to start a visible Chrome browser and Playwright to control that same browser through Chrome DevTools Protocol. The script loads credentials from a local JSON file, fills the VFS login fields, and waits for the user to finish Cloudflare verification. Once the page exposes a verification response, it clicks Sign In and leaves the browser open for inspection.”

## Project files

| File | Purpose |
| --- | --- |
| `t1.py` | Browser startup, credential loading, form filling, verification wait, and login submission. |
| `credentials.json` | Local email and VFS account password; edit this before running. |
| `.gitignore` | Excludes credentials, the virtual environment, and Python bytecode from future Git tracking. |
| `.venv/` | Local Python environment containing the installed dependencies. |

## Architecture

```text
credentials.json
       |
       v
Python script ----> SeleniumBase ----> visible Chrome
       |                                  ^
       +----> Playwright ---- CDP ----------+
                                          |
                                   VFS login page
                                          |
                             user completes Cloudflare
                                          |
                              script clicks Sign In
```

**SeleniumBase** owns browser startup and cleanup. `sb_cdp.Chrome(headless=False)` starts a visible Chrome session, and `sb.get_endpoint_url()` exposes its debugging endpoint.

**Playwright** attaches to that existing session with `p.chromium.connect_over_cdp(...)`. It uses the browser’s first context and first tab, creating a tab if needed. It handles navigation, selectors, form filling, and the Sign In click.

**CDP (Chrome DevTools Protocol)** is the connection used to control the Chrome session. The script uses one browser shared by the two libraries.

## Execution flow

1. **Load and validate credentials.** `load_credentials()` reads `credentials.json` relative to the script location. It requires a JSON object with nonempty string values for `email` and `password`. The email is trimmed; the password is preserved exactly. Invalid or missing credentials stop execution before Chrome opens.
2. **Launch and attach.** SeleniumBase launches Chrome and Playwright attaches through CDP.
3. **Open the login page.** The script navigates to `https://visa.vfsglobal.com/are/en/jpn/login`, waiting for `domcontentloaded`. It prints the page title, URL, and HTTP status when available. This navigation event does not guarantee that the application has finished rendering.
4. **Handle the cookie banner.** It attempts to click the necessary-cookies button using `#onetrust-reject-all-handler`. If that selector is not actionable within five seconds, execution continues.
5. **Wait for and fill the form.** It waits for `#email`, then fills that field and `#password`. If the email field is initially unavailable, it allows extra time for the user to complete any initial verification in Chrome.
6. **Wait for manual Cloudflare completion.** The user completes the checkbox in the browser. The script observes the page’s `[name="cf-turnstile-response"]` field until it contains a nonempty value. It does not click the Cloudflare checkbox or generate a verification response.
7. **Submit the form.** Playwright locates a button with an accessible name matching `Sign In`, case-insensitively and allowing whitespace between the words, then clicks it once.
8. **Keep the result visible.** The script waits for Enter in the terminal. Its cleanup block calls `sb.quit()` to close the browser.

## Timeouts and error handling

| Operation | Explicit timeout | Behavior on timeout |
| --- | --- | --- |
| Initial navigation | 60 seconds | Error propagates after the browser-inspection prompt. |
| Cookie-banner click | 5 seconds | Continues without clicking the banner. |
| Initial email-field visibility | 15 seconds | Prints instructions and starts an extended wait. |
| Extended email-field visibility | 5 minutes | Error propagates after the inspection prompt. |
| Cloudflare response observation | 5 minutes | Prints a timeout message; no further login attempt is made. |
| Sign In click | 30 seconds | Prints the same timeout message; no retry is made. |

The script also uses Playwright’s default waits for operations without explicit timeouts. The inspection prompt runs after navigation or form errors inside its protected block. Browser cleanup is in an outer `finally` block. Browser-startup failures happen before that block and may exit immediately.

## Setup and usage

Run these commands from the project directory when setting up a new environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install playwright seleniumbase
```

The current project uses a local virtual environment. Dependency versions have not been pinned in a requirements file.

Edit `credentials.json` locally:

```json
{
  "email": "your-email@gmail.com",
  "password": "your-vfs-account-password"
}
```

Use the password for the **VFS account** associated with that email address. It is not necessarily the password for the Gmail mailbox.

Start the script:

```bash
.venv/bin/python t1.py
```

Complete Cloudflare verification manually when shown. The script then clicks Sign In automatically. Check Chrome for success, validation errors, or additional verification. Press Enter in the terminal when finished to close Chrome.

## Credential handling

- Credentials are stored as plain text in `credentials.json`; they are not encrypted.
- The local file was given owner-only read/write permissions with `chmod 600 credentials.json` on macOS.
- `.gitignore` excludes the file from future Git tracking. This does not protect copies, backups, or files already tracked elsewhere.
- The script does not print the password. Setting the local password variable to `None` after filling the form is not secure memory erasure; the browser still contains the filled value.
- Share the script and this document with others, and have them create their own credentials file.

## Issues found during implementation

The initial run with the system Python failed because `playwright` and `seleniumbase` were not installed in that interpreter. The project virtual environment subsequently contained the dependencies, so the run command explicitly uses `.venv/bin/python`.

Running Chrome inside the restricted execution sandbox failed when SeleniumBase tried to bind a local debugging port. Running outside that sandbox allowed startup. This was a restriction of the assistant’s execution environment, not evidence of a VFS website failure.

The original script stopped immediately after navigation and contained no login actions. We added progress output, credential loading, field filling, verification observation, automatic Sign In submission, and an inspection pause before cleanup.

## Validation performed and remaining limitations

Browser startup and navigation to the VFS URL were exercised, and the URL returned HTTP 200. Live inspection found the `#email`, `#password`, and Cloudflare response fields used by the implementation. Python syntax and rejection of empty credentials were checked after the updates.

An end-to-end login with real credentials has **not** been verified. HTTP 200 only confirms a successful HTTP response; it does not prove the login application is ready or that authentication succeeded. The final credential-fill, verification-wait, and submission sequence still needs a real-user run.

The implementation depends on the current page structure and English Sign In label. A selector change, a different Cloudflare integration, or an overlay could require updates. A nonempty Cloudflare response is a client-side completion signal, not a guarantee that the server will accept verification. The script does not check token expiry or retry rejected authentication.

Possible follow-up work includes detecting successful login versus an error message, handling the next user-approved workflow, and pinning dependency versions for reproducible setup.
