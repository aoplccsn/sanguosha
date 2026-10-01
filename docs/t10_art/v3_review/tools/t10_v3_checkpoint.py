"""Save a truthful checkpoint when image generation reaches its usage limit."""

import hashlib
import json
from pathlib import Path

ROOT = Path(r"C:\Sanguosha")
ART = ROOT / "docs" / "t10_art"
REVIEW = ART / "v3_review"
path = REVIEW / "portrait_inventory.json"
rows = json.loads(path.read_text(encoding="utf-8"))
readiness = json.loads((REVIEW / "candidate_readiness.json").read_text(encoding="utf-8"))
expected = {"standard": 25, "wind": 7, "fire": 0, "forest": 0, "mountain": 0}
actual = {pack: data["ready_count"] for pack, data in readiness["packs"].items()}
assert actual == expected, actual
assert sum(actual.values()) == 32

for row in rows:
    candidate = ART / "v3_candidates" / f"{row['general_id']}.png"
    source = ROOT / row["snapshot_path"]
    live = ROOT / row["当前资源路径"]
    digest = row["sha256"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest, source
    assert hashlib.sha256(live.read_bytes()).hexdigest() == digest, live
    if candidate.exists():
        row["candidate_path"] = str(candidate.relative_to(ROOT)).replace("\\", "/")
        row["candidate_status"] = "keep_identical" if row["general_id"] == "wind_zhang_jiao" else (
            "ready_after_visual_review" if row["pack"] == "standard" else "individual_review_passed_batch_pending"
        )
    elif row["general_id"] == "wind_xiao_qiao":
        row["candidate_status"] = "blocked_image_usage_limit_needs_redraw"
    else:
        row["candidate_status"] = "pending"
assert hashlib.sha256((ART / "v3_candidates" / "wind_zhang_jiao.png").read_bytes()).hexdigest() == next(
    row["sha256"] for row in rows if row["general_id"] == "wind_zhang_jiao"
)
path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

lines = [
    "# T10 V3 头像清单", "",
    "当前状态指正式资源初筛；candidate_status 指独立候选图进度。", "",
    "| general_id | 中文名 | pack | faction | 当前资源路径 | 当前状态 | candidate_status | 审查备注 |",
    "| --- | --- | --- | --- | --- | --- | --- | --- |",
]
for row in rows:
    lines.append("| " + " | ".join([
        row["general_id"], row["中文名"], row["pack"], row["faction"], row["当前资源路径"],
        row["当前状态"], row["candidate_status"], row["review_note"]
    ]) + " |")
(REVIEW / "portrait_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

checkpoint = """# T10 V3 checkpoint — image usage limit

Image generation returned HTTP 429 `usage_limit_reached` while redrawing `wind_xiao_qiao`. The service reported reset at **2026-10-01 10:10:42 Asia/Shanghai**. No placeholder or source image was promoted as the Xiao Qiao candidate.

## Candidate counts

| Pack | Candidate count | Required | Review state |
| --- | ---: | ---: | --- |
| Standard | 25 | 25 | Individual and contact-sheet review complete |
| Wind | 7 | 8 | Zhang Jiao identical; six new portraits individually checked; Xiao Qiao pending |
| Fire | 0 | 8 | Pending |
| Forest | 0 | 8 | Pending |
| Mountain | 0 | 8 | Pending |
| **Overall** | **32** | **57** | Formal asset gate closed |

## Wind work completed

- `wind_zhang_jiao.png`: copied unchanged; snapshot and candidate SHA-256 match the live resource.
- New individually reviewed candidates: `wind_xiahou_yuan`, `wind_cao_ren`, `wind_huang_zhong`, `wind_wei_yan`, `wind_zhou_tai`, `wind_yuji`.
- `wind_xiao_qiao`: one draft in `v3_review/wind_xiao_qiao_rejected_similarity_v1.png`; it resembled Da Qiao in face and floral hair design. Redraw requested without that reference; generation then hit the usage limit. No candidate file exists.

## Next actions after image service recovers

1. Redraw and visually review `wind_xiao_qiao`, then generate `wind_sheet.png` and complete the wind review.
2. Proceed through fire, forest and mountain packs in that order, with candidate sheets and visual review after each pack.
3. Only after 57/57 pass cross-pack review, replace formal resources, verify readers/tests, and consider a commit.

All 57 source snapshots still match the original inventoried hashes. All live formal portrait files still match those hashes. `assets/manifest.json` has not been edited by this task.
"""
(REVIEW / "checkpoint_usage_limit.md").write_text(checkpoint, encoding="utf-8")
print("checkpoint saved; 57 source and live hashes verified; Zhang Jiao identical")
