# T6.5 visual assets

The T6.5 table and Eight Trigrams illustrations were generated as original images with the built-in image generation tool. The prompts specified an ink-wash Three Kingdoms atmosphere and explicitly excluded commercial game assets, logos, text and copied interface elements.

| Manifest ID | File | Use | Source |
| --- | --- | --- | --- |
| `table.background`, `default.table` | `assets/backgrounds/table/ink_wash_v1.png` | Quiet paper center and mountain / walnut perimeter for the five-seat table | Original generated image |
| `equipment.armor.eight_trigrams` | `assets/cards/military/equipment.armor.eight_trigrams-v2.png` | Formation-focused Eight Trigrams art | Original generated image replacing the prior art while keeping the T6 resource contract |

The portrait files and other card paintings remain from the T6 original asset set. Seat plaques, HP beads, equipment slots, judgment markers, target outlines and center composition are drawn by Qt from the theme palette. They scale without separate raster variants.

To update an illustration, generate an original replacement using the same visual brief, inspect it, copy it into the listed path, and keep the manifest ID stable. The table prompt calls for a 16:9 overhead xuan-paper tabletop, clean in the central 65%, with dark walnut, antique bronze and ink landscapes around the perimeter. The Eight Trigrams prompt calls for a portrait ink formation diagram with yin-yang center, eight trigrams, mist, distant banners and no person as its focal point.

ResourceManager resolves all manifest paths within the assets directory, detects replacement files and falls back to defaults or generated artwork if a file is absent or unreadable. The stable T6 card definitions and engine rules are unchanged.
