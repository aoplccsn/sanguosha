# T17C development checkpoint

Status: IN_PROGRESS. This is not a COMPLETE report. Production remains 76 accepted generals; the 27 additions remain development-only.

Implemented prototypes: Qice, Zhiyu, Miji, Jiangchi, Quanji, Zili/Paiyi, Dangxian/Fuli, Anxu/Zhuiyi, Gongqi/Jiefan, Zishou/Zongshi, Shiyong, Jingce, Duodao/Anjian, Juece, Chengxiang/Renxin, Junxing/Yuce, Longyin; Mashu reuses the existing shared modifier with grant/disable checks. All still require combined acceptance and full AI game coverage. Exact per-skill status is in skill_progress.json.

Every new active choice uses PendingRequest and ResolutionStack, with snapshot restoration tests. Qice consumes the complete current hand at commitment, prohibits recast in its target request, carries full VirtualCard colors to Weimu, and reuses normal trick/counter/effect handlers. No-recast behavior is verified against the frozen source. Shiyong now reads virtual Slash colors and carries wine bonuses through optional weapon damage paths. Quan faces are public: the frozen Quanji call uses addToPile with the open=true default. Earlier owner-only hiding has been corrected.

Art: 23 ordinary originals are generated and locally integrated; four supplied Masters are untouched and mapped to cleaned detail/panel videos plus first-frame fallback. The panel runtime size is 360x640 and detail is 720x1280. The final frontend, mobile playback, and 103-general draft/detail checks are pending. Source and QA reports are under docs/t18b. Optimization scratch backups are not delivery assets.

Validation at this checkpoint: 1197 Python tests passed (121.12s), including the resynchronized local Worker mirror; 87 Vitest tests passed; TypeScript and Vite production build passed with the project virtual environment on PATH. System Python lacks Pillow, so prebuild must use the project virtual environment. This is a regression checkpoint, not final 103-general acceptance. No public deployment or infrastructure configuration was changed.

Remaining work: all NOT_IMPLEMENTED skills in the matrix; authority for borrowed/suppressed skills and abolished equipment slots; multiplayer privacy/reconnect checks; AI for every skill; 103-entry production gate; final 60 complete AI games; frontend Vitest/TypeScript/build, Playwright mobile/reconnect, PySide smoke, and local asset HTTP verification.

Boundary audit: authority_boundaries.json records fixed-source hashes and resolved edge cases. No claim of publisher verification is made. The second prototype batch is covered by the latest 1197-test complete-suite checkpoint. All 27 new portraits and all eight new video variants are locally accessible, including video range responses. The final 103-roster UI/mobile/AI acceptance remains pending.
