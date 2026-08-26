# Deployment Guide | คู่มือการนำระบบขึ้นใช้งาน

This guide is the Phase 11 release procedure for Streamlit Community Cloud. It
deploys the repository root `app.py` and the pinned reference release at
`data/releases/2026.08-draft`.

## Release boundary | ขอบเขตการปล่อยรุ่น

The release contains presentation and documentation refinement only. Do not
change calculation formulas, catalogue values, PE lookup behavior, conduit fill
limits, transformer rules, BOQ quantity rules, or costing rules without owner
approval and a new engineering review record.

Required release inputs:

- approved GitHub commit and release branch;
- successful CI checks and the local full test command in the README;
- completed [release checklist](RELEASE_CHECKLIST.md);
- named release owner, technical reviewer, and rollback owner;
- confirmed `data/releases/2026.08-draft/manifest.json` and data version;
- no secrets, local exports, or personal data committed to Git.

## Local preflight | ตรวจสอบก่อนปล่อย

Run from the repository root so local paths match Community Cloud:

```text
python -m pytest -p no:cacheprovider --cov=solar_design --cov-report=term-missing --cov-fail-under=75 -q
python -m ruff check src tests app.py pages
python -m mypy src tests
python -m compileall -q src tests app.py pages
python -m pip check
```

Then run the manual smoke procedure in the checklist at the same viewport sizes
used for acceptance. Record the commit SHA, data version, test output, and any
warnings in the release ticket.

## Community Cloud procedure | ขั้นตอน Streamlit Community Cloud

1. Push the approved commit to the approved GitHub branch. Use a release branch
   such as `implementation-v1` during validation, or the approved default branch
   after merge. Confirm that `app.py`, `requirements.txt`, `.streamlit/config.toml`,
   `data/`, `src/`, and `pages/` are present in the commit.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) with the
   GitHub account that has the required repository access. For a private repo,
   authorize private-repository access before creating the app.
3. Select **Create app → Yup, I have an app**, then enter the exact repository,
   release branch, and entrypoint `app.py`. Choose the approved app subdomain.
4. Open **Advanced settings**. Select the Python version used by the validated
   CI environment (currently Python 3.11 is the compatibility target for this
   project). Keep the application dependency definition in root `requirements.txt`.
5. Leave the **Secrets** field empty unless an owner-approved integration needs a
   secret. Never paste a secret into source code, a CSV, an issue, or a screenshot.
   If a secret is required, paste only its `secrets.toml` content into the app's
   settings and record its owner and rotation date in the private release ticket.
6. Click **Deploy**, wait for the build to finish, and inspect the Cloud logs for
   import, dependency, and data-release errors.
7. Run the post-deploy smoke test below using the deployed URL. Confirm the app
   displays the bilingual disclaimer, the pinned data version, and the expected
   workflow pages.
8. Record the deployed URL, commit SHA, data version, test evidence, access list,
   and release decision. Do not call the release complete while any blocker or
   unexplained warning remains.

Community Cloud executes from the repository root. This repository keeps the
`src` package importable from `app.py` so the same root entrypoint works in a
source-layout checkout and in the Linux deployment environment.

## Restricted-access acceptance | การทดสอบสิทธิ์แบบจำกัด

Use a private repository and the Community Cloud app's **Settings → Sharing**:

1. Set **Only specific people can view this app**.
2. Add one approved viewer and one non-approved test identity, if organizational
   policy permits. Do not use a real customer account for the negative test.
3. Verify the approved viewer can sign in and view the app, while the negative
   identity cannot view it.
4. Verify GitHub repository permissions and Community Cloud viewer permissions
   are documented separately. Remove the temporary test viewer after acceptance.
5. Capture only the result (pass/fail, timestamp, app URL, commit SHA); never
   capture tokens, cookies, or personal profile data.

If the app must be public, obtain explicit owner approval and repeat the test
with the public-sharing setting. A public URL must not expose secrets or
unapproved project data.

## Post-deploy smoke test | ตรวจสอบหลัง deploy

Use a desktop browser and a tablet-sized viewport (or a physical tablet). At
each viewport, verify:

- the landing page loads without an exception and the Help panel is reachable;
- the disclaimer is visible in Thai and English;
- navigation labels are bilingual and every page can be opened;
- Project Inputs labels are visible, inputs have help text, and Save reports the
  STALE state after an upstream change;
- Run design workflow completes and downstream pages show current results;
- warning, blocker, MISSING, REVIEW, and override-reason information is visible
  when the test fixture produces it;
- BOQ and Cost Summary tables fit the viewport or can be scrolled without losing
  row/column meaning;
- keyboard focus reaches all controls in a logical order and no action depends
  on color or an icon alone;
- refresh does not show an unhandled exception and the pinned data version is
  still visible.

Record browser, viewport, commit SHA, data version, pass/fail, and a short note
for each item in the release ticket. This manual check complements, and does not
replace, `tests/phase11/test_release.py` and the Streamlit AppTest suite.

## Rollback | การย้อนกลับรุ่น

The source of truth is the last approved Git commit, not a manual edit in the
running container.

1. Disable or communicate the release URL if the incident could mislead users.
2. Identify the last known-good commit SHA and its matching data version from
   the release ticket.
3. Revert the bad commit on the release branch with a reviewed GitHub pull
   request, or move the release branch back to the known-good commit according to
   repository policy. Do not rewrite shared history without owner approval.
4. Push the reviewed rollback commit. Community Cloud should rebuild from the
   branch; monitor Cloud logs until the app is healthy.
5. Re-run the full automated tests and the desktop/tablet smoke test. Confirm the
   URL shows the known-good commit/data version and that restricted access remains
   restricted.
6. If the failure is dependency-related, keep the previous working dependency
   constraints while investigating. If a Python version must change, follow the
   documented Community Cloud delete-and-redeploy process and preserve the app
   URL, secrets, and access list in the ticket before proceeding.
7. Record incident cause, rollback SHA, observed impact, access verification, and
   owner sign-off. Only then reopen the release decision.

## Official references | เอกสารอ้างอิง

- [Deploy your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [App dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [File organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization)
- [App settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings)
- [Share your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)
- [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Python version changes](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-python)
