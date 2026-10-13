# T22 立绘生成与接入记录

10张均为内建 image_gen 生成的原创位图。复用前次任务已完成的9张，补生成界张飞1张；未删除原始输出，未改旧武将图片。

- 统一方向：竖版半身至大半身；宣纸肌理、水墨晕染与厚涂；三国时代服饰兵器；人物为主体，清晰面部，不做Q版、现代奇幻、霓虹或页游发光；不得复制官方立绘。
- 徐盛：重甲战刀、江东军阵，赤黑金，压迫与破阵感。
- 沮授：冷灰墨蓝暗金、文士战袍与策书，河北谋臣、沉静悲壮。
- 钟会：年轻俊雅魏晋名士、白灰玄黑淡紫金，野心内敛。
- 李儒：黑红暗褐冷金、火与阴影、克制危险的毒士。
- 凌统：蓝黑赤金、青年水军武将，双兵器与利落战姿。
- 朱然：赤褐玄甲、烽火城墙，坚毅守将。
- 法正：青黑灰金、卷轴书简，冷峻恩怨与复仇谋略。
- 曹休：魏蓝黑银暗金、肃整精骑统帅，区别于曹操。
- 魏延：暗红褐黑、长刀与山地突袭，桀骜猛将。
- 张飞：黑甲黑红暗金、丈八蛇矛、强烈动作张力。

上述为9张恢复图的用户提示方向与本批美术规格，非声称恢复了其逐字生成日志。界张飞本次使用的完整提示词如下：

Use case: historical-scene. Create ONE original vertical 1024x1536 Chinese Three Kingdoms card-game character portrait of Zhang Fei (界张飞). Match a premium set of painterly ink-wash and thick-brush portraits on textured xuan paper: realistic heroic figure, detailed black iron lamellar armor and dark-red cloth, muted antique gold accents, strong rugged bearded face with broad fierce features. Half-body to three-quarter-body composition, dynamic forward lunge with his iconic long serpent spear (丈八蛇矛), broad shoulders and vigorous sweeping motion. Stormy ancient Shu mountain battlefield suggested softly behind him, windblown banners and forceful black ink brush splashes integrated with painted atmosphere; clear distinctive character silhouette and readable face. Three Kingdoms era clothing/weapons only. Original artwork, no copying official Sanguosha illustrations. Avoid chibi, cartoon, modern fantasy, glowing magical weapons, neon, cheap game art, identical standing-pose template, text, letters, card frame, logo, watermark. The figure is the main subject; keep face and spear grip inside a centered portrait crop suitable for 768x1152 PNG and 600x900 WebP. Dramatic movement but natural anatomy and hands.

生产转换沿用已有 integrate_remaining_portraits.py 的配方：1024×1536源PNG、768×1152运行PNG、600×900 WebP，LANCZOS，PNG optimize，WebP quality=86/method=6。通过 assets/manifest.json 的 general.boundary_* 键供选将、席位、Web和PySide使用。

路径、尺寸、原图SHA256及视觉检查结果见 inventory.json；10张总览见 contact_sheet.png。
