"""Record the completed visual review of standard-pack candidates."""

import json
from pathlib import Path

ROOT = Path(r"C:\Sanguosha")
ART = ROOT / "docs" / "t10_art"
review = ART / "v3_review"
inventory_path = review / "portrait_inventory.json"
rows = json.loads(inventory_path.read_text(encoding="utf-8"))
ready = json.loads((review / "candidate_readiness.json").read_text(encoding="utf-8"))
assert ready["packs"]["standard"]["ready_count"] == 25

for row in rows:
    cid = row["general_id"]
    if row["pack"] == "standard":
        row["candidate_path"] = f"docs/t10_art/v3_candidates/{cid}.png"
        row["candidate_status"] = "ready_after_visual_review"
        row["review_note"] = "原图已保护；V3 候选完成，标准包总览已复核"
    elif cid == "wind_zhang_jiao":
        row["candidate_path"] = f"docs/t10_art/v3_candidates/{cid}.png"
        row["candidate_status"] = "keep_identical"
inventory_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

lines = [
    "# T10 V3 现有头像审查清单", "",
    "当前状态描述正式资源的初筛，candidate_status 描述独立候选图的进度；两者不可混同。", "",
    "| general_id | 中文名 | pack | faction | 当前资源路径 | 当前状态 | candidate_status | 审查备注 |",
    "| --- | --- | --- | --- | --- | --- | --- | --- |",
]
for row in rows:
    lines.append("| " + " | ".join([
        row["general_id"], row["中文名"], row["pack"], row["faction"],
        row["当前资源路径"], row["当前状态"], row.get("candidate_status", "pending"), row["review_note"]
    ]) + " |")
(review / "portrait_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

report = """# Standard V3 visual review

## Counts

- Standard candidates: 25 / 25 ready after individual and contact-sheet review.
- Overall candidates: 26 / 57 including the unchanged Zhang Jiao.
- Formal `assets/generals/` and `assets/manifest.json`: not changed by this V3 preparation.

## Visual checks

- **Faces and age:** Cao Cao, Liu Bei, Sun Quan, Sima Yi, Hua Tuo and Huang Gai read at their intended stages of life. Guo Jia was redrawn after the first versions read too androgynous; final has a lean adult male face and illness cues. No obvious duplicate face remains at contact-sheet scale.
- **Pose and camera:** cavalry action, command, care, craft, river combat and covert strategy have distinct framing. Cao Cao and Sima Yi first drafts shared a table scene; Sima Yi was redrawn on a watchtower.
- **Environment and palette:** river, mountain, fortress, garden, workshop, palace and shelter scenes support identity. The pack spans blue-black, jade, crimson, warm gold, violet and winter white. Common painterly detail and material treatment keep it coherent.
- **Women:** Zhen Ji, Huang Yueying, Da Qiao, Sun Shangxiang and Diao Chan have separate actions and character signals. Diao Chan was redrawn after her initial face and hair resembled Zhen Ji.
- **Role identity:** scholars, rulers, cavalry, veterans, the physician and engineer are legible. Zhang Jiao remains the quality benchmark and is untouched.

## Replacement decisions

- `caocao_rejected_composition_v1.png`: first draft too close to Zhang Jiao's low-angle reach.
- `simayi_rejected_map_pose_v1.png`: first draft repeated Cao Cao's table framing.
- `guojia_ambiguous_age_v1.png` and `guojia_rejected_ambiguous_age_v2.png`: earlier faces too androgynous.
- `diaochan_rejected_same_face_v1.png`: earlier face and floral high hair too similar to Zhen Ji.

## Remaining gate

The standard set is ready as a pack, but formal asset replacement remains gated on all 57 candidates and the cross-pack review.
"""
(review / "standard_review.md").write_text(report, encoding="utf-8")
print("standard review recorded")
