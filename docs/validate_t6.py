"""One-process full-suite then GUI/engine verification; no test isolation."""
import os,json,sys,ast,hashlib
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ['SANGUOSHA_FAST_AI']='1'
import pytest
import sanguosha
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication,QEvent
from sanguosha.session import GameSession
from sanguosha.projection import CardView
from sanguosha.ui.card_widget import CardWidget
from sanguosha.ui.resources import RESOURCES
from sanguosha.model.zones import ZoneRef,ZoneType

class Results:
    def __init__(self):self.passed=0;self.failed=0;self.warnings=0;self.total=0
    def pytest_collection_modifyitems(self,items):self.total=len(items)
    def pytest_runtest_logreport(self,report):
        if report.when=='call' and report.passed:self.passed+=1
        if report.failed:self.failed+=1
    def pytest_warning_recorded(self,warning_message,when,nodeid,location):self.warnings+=1

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    package=Path(sanguosha.__file__).resolve()
    assert package.is_relative_to(root/'src'),str(package)
    print('sanguosha.__file__ =',package,flush=True)
    for source in (root/'src').rglob('*.py'):ast.parse(source.read_text(encoding='utf-8'),filename=str(source))
    results=Results()
    assert pytest.main(['-q',str(root/'tests')],plugins=[results])==0
    app=QApplication.instance() or QApplication([])
    RESOURCES.reload()
    session=GameSession.new_game(military=True)
    definitions={card.definition_id for card in session.state.cards.values()}
    assert len(definitions)==43 and len(session.state.cards)==160
    for definition in sorted(definitions):
        cid=next(cid for cid,card in session.state.cards.items() if card.definition_id==definition)
        info=session.definitions.get(definition)
        widget=CardWidget(CardView(cid,info.name,'♠','A',definition,info.category.value))
        assert not widget.grab().isNull()
        widget.close();widget.deleteLater()
    QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
    sys.path.insert(0,str(root/'docs'))
    import smoke_t6_development as engine_smoke
    import smoke_t6_gui as gui_smoke
    engine=[];gui=[]
    for seed in range(1,6):
        first=engine_smoke.match(seed); assert first==engine_smoke.match(seed);engine.append(first)
        shown=gui_smoke.match(seed);assert shown==gui_smoke.match(seed);gui.append(shown)
        print(json.dumps({'engine':first,'gui':shown},ensure_ascii=False),flush=True)
    payload={'pytest':{'total':results.total,'passed':results.passed,'failed':results.failed,'warnings':results.warnings},
             'import_path':str(package),'syntax':'PASS','card_widgets_rendered':43,'original_art':40,
             'deck':160,'engine_smoke':engine,'gui_smoke':gui,'status':'PASS',
             'deck_sha256':hashlib.sha256((root/'data/decks/classic_military.json').read_bytes()).hexdigest()}
    (root/'docs/T6_VALIDATION.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'validation':'PASS','pytest':payload['pytest'],'package':str(package)},ensure_ascii=False))
