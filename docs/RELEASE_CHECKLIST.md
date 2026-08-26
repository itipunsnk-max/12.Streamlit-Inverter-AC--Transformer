# Release Checklist | รายการตรวจสอบการปล่อยรุ่น

Use this checklist for each release candidate. A checked item needs evidence in
the release ticket or CI run. Blank, failed, or unexplained items block release.

## 1. Ownership and scope | ผู้รับผิดชอบและขอบเขต

- [ ] Release owner named: ____________________
- [ ] Responsible engineer / engineering-rule owner named: ____________________
- [ ] Technical reviewer named: ____________________
- [ ] Rollback owner named: ____________________
- [ ] Approved commit SHA: ____________________
- [ ] Approved branch: ____________________
- [ ] Deployed app URL: ____________________
- [ ] Release decision and timestamp (Asia/Bangkok): ____________________
- [ ] No formula, catalogue value, utility rule, fill limit, BOQ rule, or cost
      rule changed without owner approval and traceable review evidence.

## 2. Data and security | ข้อมูลและความปลอดภัย

- [ ] Reference release is `2026.08-draft` or an explicitly approved version.
- [ ] `manifest.json` hashes and record counts are valid.
- [ ] Schema/data versions are unchanged or approved and recorded.
- [ ] No `.streamlit/secrets.toml`, `.env`, credentials, tokens, customer data,
      local exports, or debug dumps are tracked by Git.
- [ ] Upload boundaries and CSV formula-safety tests pass.
- [ ] Dependency/static security checks pass in CI; any exception has owner sign-off.

## 3. Automated quality gates | การตรวจสอบอัตโนมัติ

- [ ] `python -m pytest -p no:cacheprovider --cov=solar_design --cov-report=term-missing --cov-fail-under=75 -q`
- [ ] `python -m ruff check src tests app.py pages`
- [ ] `python -m mypy src tests`
- [ ] `python -m compileall -q src tests app.py pages`
- [ ] `python -m pip check`
- [ ] CI full test, coverage, package, Linux smoke, and security jobs are green.
- [ ] Streamlit AppTest passes for landing, navigation, all pages, STALE state,
      validation, override reason, Thai/English labels, help, and disclaimer.
- [ ] Golden, property, export/reconciliation, and data-contract tests pass.

## 4. UX and accessibility | UX และ accessibility

- [ ] Every page has Thai/English title and description.
- [ ] Navigation labels are bilingual and descriptive; icons are supplementary.
- [ ] Inputs have visible labels, stable keys, and bilingual help text.
- [ ] Buttons describe their action in Thai and English; no icon-only action is required.
- [ ] Validation, warning, blocker, STALE, MISSING, REVIEW, and override messages
      do not rely on color alone and retain the source message.
- [ ] Disclaimer is visible on the app and states preliminary/budgetary limits.
- [ ] Tables have bilingual column meaning and remain usable with horizontal scrolling.
- [ ] Keyboard focus order is logical; text can be zoomed without clipping critical actions.

## 5. Manual smoke | Manual smoke test

Record browser/device and viewport before testing.

- [ ] Desktop: landing page loads with no unhandled exception.
- [ ] Desktop: open every workflow page from navigation.
- [ ] Desktop: save Project Inputs; confirm downstream STALE state.
- [ ] Desktop: run workflow; review warnings, override reason, BOQ, and Cost Summary.
- [ ] Tablet viewport: repeat landing, navigation, input save, workflow run, and
      table review; confirm no critical control is hidden or unusable.
- [ ] Tablet viewport: keyboard/focus or assistive navigation check completed where available.
- [ ] Browser refresh: no unhandled exception; release/data version remains visible.
- [ ] Evidence recorded without secrets, cookies, tokens, or personal data.

Manual evidence: ____________________________________________________________

## 6. Restricted access | สิทธิ์แบบจำกัด

- [ ] Repository visibility and app visibility match the approved release decision.
- [ ] Private app is set to **Only specific people can view this app** when required.
- [ ] Approved viewer can sign in and view the app.
- [ ] Non-approved test identity is denied, or the negative test is documented as
      unavailable by policy.
- [ ] Temporary viewer access is removed after testing.
- [ ] Secrets are present only in Community Cloud settings when explicitly approved.

Access evidence: ____________________________________________________________

## 7. Release and rollback readiness | พร้อมปล่อยและย้อนกลับ

- [ ] Community Cloud repository, branch, and entrypoint are exact: `app.py`.
- [ ] Python version and dependency file match the validated environment.
- [ ] Cloud logs show a healthy build and no unresolved import/data errors.
- [ ] Deployed URL, commit SHA, data version, and warnings are recorded.
- [ ] Last known-good commit SHA is recorded: ____________________
- [ ] Rollback owner can revert the release branch through the approved review path.
- [ ] Rollback procedure has been rehearsed or its last successful rehearsal is recorded.
- [ ] Post-rollback test owner and communication path are known.

Rollback evidence: _________________________________________________________

## 8. Sign-off | การอนุมัติ

- [ ] Engineering owner: ____________________ Date: __________
- [ ] Technical reviewer: ____________________ Date: __________
- [ ] Release owner: ____________________ Date: __________
- [ ] Release status: `GO` / `HOLD` / `ROLLBACK`
- [ ] Follow-up actions and due dates recorded: ______________________________
