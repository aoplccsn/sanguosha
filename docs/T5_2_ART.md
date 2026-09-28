# T5.2 artwork source and rebuild

The nine `assets/source_art/*.png` illustrations are original images generated with the built-in ImageGen tool. `python scripts/build_art.py` crops them to deployable portrait/card sizes and rebuilds the five identity seals. The manifest keeps the existing stable asset IDs, so a replacement illustration only needs the same source filename and a rebuild.

Generation brief shared by every illustration: refined, mature guofeng ink wash plus gongbi brushwork on textured rice paper, historical Chinese tabletop-game art; original composition; no text, logos, frames, watermarks, or copied game imagery.

| Source | Specific prompt subject |
| --- | --- |
| `caocao.png` | Cao Cao, sharp eyes, short beard, black crown, charcoal and indigo embroidered robes, calculating presence. |
| `liubei.png` | Liu Bei, gentle eyes, neat long beard, ochre and jade robes, clasped hands, benevolent authority. |
| `sunquan.png` | Sun Quan, young resolute Jiangdong ruler, trimmed beard, teal silk and bronze armor. |
| `lvbu.png` | Lü Bu, fierce warrior with long topknot, crimson and black armor and halberd. |
| `guanyu.png` | Guan Yu, ruddy face, long beard, green and deep red robes over armor. |
| `default_general.png` | Anonymous ancient scholar-warrior, visible mature face, slate and tan robes. |
| `slash.png` | Curved Chinese blade cutting through ink, sparks and crimson silk. |
| `dodge.png` | White crane evading an arrow through mist and blue-green ribbons. |
| `peach.png` | Ripe peaches and blossoms on a branch with dew and warm light. |

The source images are retained because AI generation itself is not deterministic; the deployable asset build is deterministic from those checked-in sources. The `simhei.ttf` font used by the seal generator is a Windows system font and is not bundled.
