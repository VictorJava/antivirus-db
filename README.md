# antivirus-db

Public repository that hosts signature databases for the Antivirus app as **GitHub Releases**.
Copy the contents of this folder into the root of the `antivirus-db` repository.

- Each release tag is a date (`2026.10.16`) and contains `manifest.json` + three `hypatia-*-bloom.bin` files.
- The app downloads `https://github.com/<owner>/antivirus-db/releases/latest/download/manifest.json`.
- The workflow below runs every 2 days: it fetches the MaintainTeam databases, verifies their GPG signatures and
  publishes a release only when the upstream files changed. Manual publishing: `tools/publish_db.sh <dir>` from the app repo.

## Safe packages list

`safe_packages.json` — packages the app must never report (known false positives, OEM/system components).
The app downloads it weekly from `https://raw.githubusercontent.com/VictorJava/antivirus-db/main/safe_packages.json`
and ships a bundled copy. A listed package is skipped only if it is a system app or was installed from a trusted
store, so sideloaded clones with the same package name are still scanned. Format: `{"version", "list": [...], "prefixes": [...]}`.
Edit, bump `version`, push to `main` — no app release needed.
