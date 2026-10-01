# T10 Portrait V3 final integration

## Result

**PASS — 57 / 57 playable portraits integrated.** Standard 25/25, Wind 8/8, Fire 8/8, Forest 8/8, Mountain 8/8. God portraits 0/8, reserved for the future animated pipeline. Zhang Jiao was not regenerated or changed; its formal image, candidate and original inventory SHA-256 are identical.

## Safety and recovery

- The preflight verified 57 unique general IDs and PNG content hashes, readable full PNG files, correct manifest mappings, no missing assets and no default placeholder.
- Before replacement, all 57 formal images were copied and hash-checked under `docs/t10_art/v3_preintegration_backup/`, named by `general_id`. This is a local recovery copy independent of Git. Its `backup_manifest.json` records original paths and SHA-256 values.
- The 56 changed formal PNG files now byte-match reviewed V3 candidates; Zhang Jiao remained byte-identical. Candidate PNGs were not modified. Paths, manifest keys, runtime IDs, playable roster, game rules and god portraits were not changed.
- The project asset synchronization script updated `web/public/assets`; the Vite production build updated `web/dist`. All 57 Web public and production portrait files byte-match the formal assets.
- Local candidate, source-snapshot and backup image directories remain on disk and are Git-ignored to avoid adding duplicate binary copies to the commit. The review metadata and all contact sheets are tracked.

## Formal visual smoke

The following sheets were built from `assets/generals` via `assets/manifest.json`, with a per-image SHA-256 check against the candidate and Web public copy:

- `v3_contact_sheets/standard_sheet_final.png`
- `v3_contact_sheets/wind_sheet_final.png`
- `v3_contact_sheets/fire_sheet_final.png`
- `v3_contact_sheets/forest_sheet_final.png`
- `v3_contact_sheets/mountain_sheet_final.png`
- `v3_contact_sheets/all_57_final.png`
- `v3_contact_sheets/all_57_playerpanel_crop_final.png` — compact Web PlayerPanel framing preview.

The whole-set and compact previews were inspected for headwear and dual-character clipping, dark portraits and small-size recognition. PySide PlayerPanel now uses aspect-preserving cover cropping instead of direct stretching. Web draft cards and detail/player portraits already use `object-fit: cover`.

## Verification

- Python portrait, manifest, roster and PySide targeted suite: **25 passed**.
- Additional actual PySide window/loading suite after crop adjustment: **14 passed**.
- Vitest: **16 passed in 7 files**.
- Playwright Chromium multiplayer smoke: **1 passed**. It opened a room, completed the ten-choice draft, checked loaded PlayerPanel portraits and opened GeneralDetail. Screenshot: `v3_review/web_ui_smoke/player_detail_final.png`.
- Vite TypeScript and production build: **passed**.
- Production `web/dist/assets` 57-image hash comparison: **passed**.

Cloudflare 20-game rule regression was not run, as requested for this art-only integration.
