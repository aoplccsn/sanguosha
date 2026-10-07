"""Local unattended all-AI acceptance; imports the user's authoritative engine."""
import sys,json,time,traceback,gc
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from sanguosha.session import GameSession
from sanguosha.pregame import Pregame,SetupStage
from sanguosha.game_modes import game_mode
from sanguosha.content.characters.standard import PLAYABLE_GENERAL_POOL
from sanguosha.content.characters.remaining import REMAINING_DEV_GENERALS
from sanguosha.model.state import GameStatus
from sanguosha.model.zones import ZoneType
from sanguosha.projection import project_for_human
from sanguosha.snapshot import snapshot_session,restore_session

output=ROOT/'docs/t20_2/ai_acceptance.json'
candidate={c.id:c for c in (*PLAYABLE_GENERAL_POOL,*REMAINING_DEV_GENERALS)}
report={'status':'RUNNING','production_roster_count':len(PLAYABLE_GENERAL_POOL),'development_candidate_count':len(candidate),'games':[],'failures':[],'coverage':[]}
if output.exists() and '--resume' in sys.argv:
    report=json.loads(output.read_text(encoding='utf-8'));report['status']='RUNNING';report['failures']=[]
new=['mobile_god_lusu','mobile_god_taishici','mobile_god_sunce','mountain_god_simayi','mobile_god_guojia','mobile_god_xunyu'];coverage=set(report.get('coverage',[]))
done={(g['mode'],g['seed']) for g in report['games']}
start=time.monotonic()
for mode in ('military-five','military-eight','duel-1v1','team-2v2'):
    for index in range(20):
        seed=20200+index+('military-five','military-eight','duel-1v1','team-2v2').index(mode)*1000
        if (mode,seed) in done:continue
        try:
            setup=Pregame.create(seed,mode);seats=game_mode(mode).seats
            # Every new general participates repeatedly; remaining seats sample the full pool.
            selected=[new[(index*2)%6],new[(index*2+1)%6]]
            available=[cid for cid in candidate if cid not in selected]
            for _ in range(len(seats)-2):
                c=setup.rng.choice(available);available.remove(c);selected.append(c)
            setup.generals=dict(zip(seats,selected));setup.stage=SetupStage.COMPLETE
            s=GameSession.new_game(seed=seed,military=True,setup=setup)
            s.human_id='acceptance-no-human'
            audit=[]
            steps=0;begin=time.monotonic();snapshots=0;projections=0
            while s.state.status is not GameStatus.FINISHED:
                if steps>=200000 or s.state.turn_number>1500:raise RuntimeError('Full-game decision/turn limit reached')
                s.ai.observe_public_events(s.state,s.events.events)
                pending=s.engine.pending_request
                if steps%31==0 or pending and any(name in pending.prompt for name in ('魄袭','纵玄','惴恐','求援','巧说','夺锐','止啼')):
                    for pid in seats:
                        project_for_human(s.state,s.definitions,pid,s.character_names);projections+=1
                if steps and steps%257==0:
                    s=restore_session(snapshot_session(s));s.human_id='acceptance-no-human';snapshots+=1
                if index<3 and pending and len(audit)<160:
                    context=s.ai_response_context()
                    audit.append({'turn':s.state.turn_number,'actor':str(pending.player_id),'prompt':pending.prompt,'allowed_targets':list(pending.allowed_player_ids),'choice':str(s.ai.decide(s.state,pending,response_context=context).value),'target_scores':{str(q):s.ai._target_score(s.state,pending.player_id,q) for q in pending.allowed_player_ids if q!=pending.player_id}})
                if not s.step_auto():raise RuntimeError('No progress before game finished')
                s.state.__post_init__()
                for p in s.state.players.values():
                    for ref,z in s.state.zones.items():
                        if ref.player_id==p.player_id and ref.zone_type is ZoneType.EQUIPMENT and ref.equipment_slot in p.abolished_equipment_slots and z.card_ids:
                            raise RuntimeError('Card in abolished equipment slot')
                steps+=1
            if s.engine.pending_request is not None:raise RuntimeError('Game finished with unresolved request')
            coverage.update(selected)
            game={'mode':mode,'seed':seed,'generals':selected,'turns':s.state.turn_number,'decisions_and_turns':steps,'seconds':round(time.monotonic()-begin,2),'projection_checks':projections,'reconnect_snapshots':snapshots,'winner':s.state.victory.label if s.state.victory else None}
            if audit: (ROOT/f'docs/t20_2/audit_{mode}_{index}.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
            report['games'].append(game);report['coverage']=sorted(coverage)
            output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(game,ensure_ascii=False),flush=True)
            del s;gc.collect()
        except Exception as exc:
            failure={'mode':mode,'seed':seed,'error':repr(exc),'traceback':traceback.format_exc()}
            report['status']='FAIL';report['failures'].append(failure)
            output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(failure,ensure_ascii=False),flush=True)
            raise
report['status']='PASS';report['seconds']=round(time.monotonic()-start,2)
report['new_general_coverage']=len(set(new)&coverage)
output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: 80 complete games; new general coverage '+str(report['new_general_coverage']),flush=True)
