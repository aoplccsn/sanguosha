"""Central skin roles, dimensions and ornamental palette."""
from .resources import ASSETS

class Theme:
    background = "#0d2426"
    panel = "#203a36"
    accent = "#d5ad65"
    danger = "#ad5146"
    card = "#f4e4bb"
    disabled = "#46514b"
    selected = "#ffe077"
    muted = "#9daea5"
    slash = "#9c3e37"
    dodge = "#3e7775"
    peach = "#98616b"
    card_edge = "#76654a"
    card_width = 116
    card_height = 174
    category_accents = {"basic":card_edge, "trick":"#65779b", "delayed_trick":"#846594", "equipment":"#8a7e46"}
    shade_fff3b7 = "#fff3b7"
    shade_ffdf8a = "#ffdf8a"
    shade_eab465 = "#eab465"
    shade_76d4d4 = "#76d4d4"
    shade_e3bf76 = "#e3bf76"
    shade_ddbd77 = "#ddbd77"
    shade_947b53 = "#947b53"
    shade_274944 = "#274944"
    shade_101f22 = "#101f22"
    shade_fff0a5 = "#fff0a5"
    shade_d9bd7a = "#d9bd7a"
    shade_975034 = "#975034"
    shade_356c75 = "#356c75"
    shade_fff0cf = "#fff0cf"
    shade_f3e1b8 = "#f3e1b8"
    shade_d1aa69 = "#d1aa69"
    shade_ed7464 = "#ed7464"
    shade_5c6560 = "#5c6560"
    shade_852f30 = "#852f30"
    shade_313b3b = "#313b3b"
    shade_efc787 = "#efc787"
    shade_72807a = "#72807a"
    shade_c5c9b4 = "#c5c9b4"
    shade_7d7761 = "#7d7761"
    shade_a9ae9c = "#a9ae9c"
    shade_e7b9a9 = "#e7b9a9"
    shade_a13a36 = "#a13a36"
    shade_263238 = "#263238"
    shade_ffe077 = "#ffe077"
    shade_f9f0d8 = "#f9f0d8"
    shade_d5bf91 = "#d5bf91"
    shade_fff1a6 = "#fff1a6"
    shade_f1d283 = "#f1d283"
    shade_6a492c = "#6a492c"
    shade_322720 = "#322720"
    shade_193634 = "#193634"
    shade_0d2426 = "#0d2426"
    shade_806c47 = "#806c47"
    shade_b39b67 = "#b39b67"
    shade_a9854d = "#a9854d"
    shade_d9bc7c = "#d9bc7c"
    shade_a99974 = "#a99974"
    shade_998c70 = "#998c70"
    shade_ead9aa = "#ead9aa"
    shade_ffe194 = "#ffe194"
    shade_42272b = "#42272b"
    shade_ffe5ac = "#ffe5ac"

FELT = Theme.background
GOLD = Theme.accent
PARCHMENT = Theme.card
MUTED = Theme.muted
DANGER = Theme.danger

try:
    QSS = (ASSETS / "ui" / "game.qss").read_text(encoding="utf-8")
except OSError:
    QSS = "QWidget { background: #0d2426; color: #f4e4bb; }"
