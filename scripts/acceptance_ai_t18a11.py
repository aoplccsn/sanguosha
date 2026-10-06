"""Local unattended all-AI acceptance; imports the user's authoritative engine."""
import sys,json,time,traceback,gc,random
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

random_mode='--random' in sys.argv
output=ROOT/('docs/t18a11/random_simulations.json' if random_mode else 'docs/t18a11/ai_acceptance.json')
candidate={c.id:c for c in (*PLAYABLE_GENERAL_POOL,*REMAINING_DEV_GENERALS)}
report={'strategy':'legal-random' if random_mode else 'AI','status':'RUNNING','production_roster_count':len(PLAYABLE_GENERAL_POOL),'development_candidate_count':len(candidate),'games':[],'failures':[],'coverage':[]}
if output.exists() and '--resume' in sys.argv:
    report=json.loads(output.read_text(encoding='utf-8'));report['status']='RUNNING'
new=[c.id for c in REMAINING_DEV_GENERALS];coverage=set(report.get('coverage',[]))
done={(g['mode'],g['seed']) for g in report['games']}
start=time.monotonic()
for mode in ('military-five','military-eight'):
    for index in range(50):
        seed=(31000 if random_mode else 21000)+index+(1000 if mode=='military-eight' else 0)
        if (mode,seed) in done:continue
        try:
            setup=Pregame.create(seed,mode);seats=game_mode(mode).seats
            # Every new general participates repeatedly; remaining seats sample the full pool.
            selected=[new[(index*2)%27],new[(index*2+1)%27]]
            available=[cid for cid in candidate if cid not in selected]
            for _ in range(len(seats)-2):
                c=setup.rng.choice(available);available.remove(c);selected.append(c)
            setup.generals=dict(zip(seats,selected));setup.stage=SetupStage.COMPLETE
            s=GameSession.new_game(seed=seed,military=True,setup=setup)
            s.human_id='acceptance-no-human'
            audit_rng=random.Random(seed)
            steps=0;begin=time.monotonic();snapshots=0;projections=0;max_pending_duration=0;request_types=set();timeout_checks=0
            while s.state.status is not GameStatus.FINISHED:
                if steps>=200000 or s.state.turn_number>1500:raise RuntimeError('Full-game decision/turn limit reached')
                s.ai.observe_public_events(s.state,s.events.events)
                pending=s.engine.pending_request
                if pending:
                    assert s.state.players[pending.player_id].is_alive or pending.originating_action_id.endswith((":zhuiyi", ":wuhun")), f"dead pending owner: {pending!r}"
                    pending.validate(pending.timeout_value());timeout_checks+=1
                    request_types.add(pending.request_type.value)
                tick=time.monotonic()
                if steps%31==0 or pending and any(name in pending.prompt for name in ('魄袭','纵玄','惴恐','求援','巧说','夺锐','止啼')):
                    for pid in seats:
                        project_for_human(s.state,s.definitions,pid,s.character_names);projections+=1
                if steps and steps%257==0:
                    s=restore_session(snapshot_session(s));s.human_id='acceptance-no-human';snapshots+=1
                if random_mode and s.engine.pending_request:
                    from sanguosha.engine.requests import Decision,RequestType
                    r=s.engine.pending_request
                    value=r.timeout_value()
                    if r.request_type is RequestType.YES_NO:value=audit_rng.choice((True,False))
                    elif r.request_type is RequestType.CHOOSE_OPTION:value=audit_rng.choice(r.choices)
                    elif r.request_type is RequestType.CHOOSE_PLAYER:value=audit_rng.choice(r.allowed_player_ids)
                    elif r.request_type is RequestType.CHOOSE_CARD:value=audit_rng.choice(r.eligible_card_ids)
                    elif r.request_type is RequestType.CHOOSE_CARDS and r.legal_card_sets:value=audit_rng.choice(r.legal_card_sets)
                    elif r.request_type is RequestType.CHOOSE_CARDS and not r.exclusive_card_groups:
                        size=audit_rng.randint(r.min_count,min(r.max_count,len(r.eligible_card_ids)))
                        if size==0 or size>=r.minimum_nonempty_count:value=tuple(audit_rng.sample(r.eligible_card_ids,size))
                    elif r.request_type is RequestType.CHOOSE_PLAYERS:value=tuple(audit_rng.sample(r.allowed_player_ids,audit_rng.randint(r.min_count,min(r.max_count,len(r.allowed_player_ids)))))
                    r.validate(value)
                    s.engine.submit_decision(Decision(r.request_id,r.player_id,value))
                elif not s.step_auto():raise RuntimeError('No progress before game finished')
                max_pending_duration=max(max_pending_duration,time.monotonic()-tick)
                s.state.__post_init__()
                for p in s.state.players.values():
                    for ref,z in s.state.zones.items():
                        if ref.player_id==p.player_id and ref.zone_type is ZoneType.EQUIPMENT and ref.equipment_slot in p.abolished_equipment_slots and z.card_ids:
                            raise RuntimeError('Card in abolished equipment slot')
                steps+=1
            if s.engine.pending_request is not None:raise RuntimeError(f'Game finished with unresolved request: {s.engine.pending_request!r}')
            coverage.update(selected)
            game={'mode':mode,'seed':seed,'generals':selected,'turns':s.state.turn_number,'decisions_and_turns':steps,'seconds':round(time.monotonic()-begin,2),'projection_checks':projections,'reconnect_snapshots':snapshots,'max_pending_duration_seconds':round(max_pending_duration,6),'invalid_decision_count':0,'timeouts':0,'deadlocks':0,'unresolved_requests':0,'timeout_fallback_checks':timeout_checks,'request_types':sorted(request_types),'winner':s.state.victory.label if s.state.victory else None}
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
print('PASS: 100 complete games; new general coverage '+str(report['new_general_coverage']),flush=True)
