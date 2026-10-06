import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows=json.loads((root/'docs/t18a11/golden_scenarios.json').read_text(encoding='utf-8'))
raise SystemExit(subprocess.call([sys.executable,'-m','pytest','-q',*[r['test'] for r in rows]],cwd=root))
