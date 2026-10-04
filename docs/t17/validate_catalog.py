"""Targeted, read-only T17A design integrity checks; never imports new content."""
from pathlib import Path
import argparse
import copy
import json
import re
import sys
import collections

sys.dont_write_bytecode = True
REQUIRED = ('README.md roster.md version_matrix.md version_questions.md mechanic_matrix.md '
            'balance_matrix.md ai_matrix.md multiplayer_projection.md request_design.md '
            'implementation_order.md god_zhangliao_risk.md sources.md sources_manifest.json '
            'catalog.json source_excerpt.json validation.md checkpoint_report.md').split()
FIELDS = ('general_id chinese_name expansion year faction gender base_hp max_hp lord_skill '
          'native_skill_ids gained_skill_ids chosen_version version_status question_ids '
          'authority_status why_this_version estimated_power implementation_tier '
          'ai_complexity ai_strategy projection_risk multiplayer_risk engine_dependencies '
          'mechanic_design test_requirements skills').split()
REQUESTS = set(('YES_NO CHOOSE_OPTION CHOOSE_PLAYER CHOOSE_PLAYERS CHOOSE_CARD '
                'CHOOSE_CARDS RESPOND_WITH_CARD USE_CARD').split())
COUNTS = {'yj2011': 11, 'yj2012': 12, 'yj2013': 11, 'new_gods': 4}


def validate(data, general_ids, old_skills):
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    require(data['production'] is False and data['implemented'] is False and data['playable'] is False,
            'non-production flags')
    require(data['baseline'] == '88ca556', 'baseline')
    require(data['expected_counts'] == COUNTS, 'expected counts')
    records = data['records']
    require(len(records) == 38, '38 records')
    require(dict(collections.Counter(g['expansion'] for g in records)) == COUNTS, 'expansion counts')
    require(len(general_ids) == 65 and data['current_roster'] == 65
            and data['target_roster'] == 103, '65 + 38 = 103')
    ids = [g['general_id'] for g in records]
    require(len(ids) == len(set(ids)), 'duplicate general id')
    require(not set(ids) & set(general_ids), 'production general id collision')
    definitions = {}
    for g in records:
        require(set(FIELDS) <= set(g), 'missing general field')
        require(re.fullmatch('[a-z][a-z0-9_]*', g['general_id']), 'general id format')
        require(g['authority_status'] == 'COMMUNITY_ARCHIVE_PRIMARY_OFFICIAL_UNVERIFIED',
                'official evidence overstated')
        require(g['version_status'] in ('LOCKED',), 'version status')
        require(not g['question_ids'], 'unresolved general version')
        require(0 < g['base_hp'] <= g['max_hp'], 'base/max hp')
        require(g['ai_complexity'] in ('LOW', 'MEDIUM', 'HIGH', 'VERY HIGH'), 'ai rating')
        require(g['projection_risk'] in ('NONE', 'LOW', 'MEDIUM', 'HIGH'), 'projection rating')
        require(g['estimated_power'] in ('C', 'B', 'A', 'S'), 'power rating')
        require(g['implementation_tier'] in (1, 2, 3, 4), 'implementation tier')
        require(set(g['native_skill_ids']).isdisjoint(g['gained_skill_ids']), 'native/gained distinction')
        require(set(g['native_skill_ids'] + g['gained_skill_ids']) ==
                {s['skill_id'] for s in g['skills']}, 'skill coverage')
        for s in g['skills']:
            sid = s['skill_id']
            require(re.fullmatch('[a-z][a-z0-9_]*', sid), 'skill id format')
            require(len(s['exact_chosen_text']) >= 12 and s['chinese_name'], 'missing skill text')
            require(s['text_status'] == ('CANDIDATE_NOT_FINAL' if g['version_status'] == 'QUESTION'
                                        else 'FROZEN_REFERENCE_TEXT'), 'text status mismatch')
            require(set(s['request_types']) <= REQUESTS, 'nonexistent request enum')
            require(s['mechanic_design'] and s['test_requirements'] and s['dependency_keys'], 'skill audit missing')
            require(s['tooltip_metadata']['description'] == s['exact_chosen_text'], 'tooltip text drift')
            require(s['tooltip_metadata']['name'] == s['chinese_name'], 'tooltip name drift')
            require(all(isinstance(k, str) and v for k, v in s['choice_labels'].items()), 'choice labels')
            require(s['source_url'].startswith('https://github.com/') and '/blob/' in s['source_url'],
                    'unversioned source')
            pair = (s['chinese_name'], s['exact_chosen_text'])
            require(sid not in definitions or definitions[sid] == pair, 'incompatible duplicate skill id')
            definitions[sid] = pair
            if sid in old_skills:
                require(s['reuse_status'] == 'REUSE', 'old skill id incorrectly NEW')
                require(s['chinese_name'] == old_skills[sid].name, 'reused Chinese name mismatch')
                require(sid == 'mashu', 'unreviewed reuse semantics')
            else:
                require(s['reuse_status'] != 'REUSE', 'missing old definition to reuse')
    require(next(g for g in records if g['chinese_name'] == '神甘宁')['base_hp'] == 3,
            'god ganning initial HP')
    require(next(g for g in records if g['chinese_name'] == '钟会')['gained_skill_ids'] == ['paiyi'],
            'paiyi must be awakening grant')
    return {'roster': len(records), 'unique_skills': len(definitions), 'counts': COUNTS,
            'locked': sum(g['version_status'] == 'LOCKED' for g in records),
            'question': sum(g['version_status'] == 'QUESTION' for g in records),
            'target_roster': 103}


def check_docs(root, data):
    for name in REQUIRED:
        if not (root / name).is_file() or not (root / name).stat().st_size:
            raise ValueError('missing document: ' + name)
    docs = {name: (root / name).read_text(encoding='utf-8') for name in REQUIRED if name.endswith('.md')}
    for name, content in docs.items():
        for target in re.findall(r'\]\(([^)]+)\)', content):
            if target.startswith(('http:', 'https:', '#')):
                continue
            target, _, anchor = target.partition('#')
            if target and not (root / target).is_file():
                raise ValueError('broken local link in ' + name + ': ' + target)
            if target == 'roster.md' and anchor and ('## ' + anchor) not in docs['roster.md']:
                raise ValueError('broken roster anchor in ' + name + ': ' + anchor)
    qtext = docs['version_questions.md']
    for g in data['records']:
        if ('## ' + g['general_id']) not in docs['roster.md']:
            raise ValueError('roster missing id: ' + g['general_id'])
        for name in ('balance_matrix.md', 'ai_matrix.md', 'multiplayer_projection.md',
                     'implementation_order.md', 'version_matrix.md'):
            if g['chinese_name'] not in docs[name]:
                raise ValueError('matrix missing general: ' + name + ' / ' + g['chinese_name'])
        for qid in g['question_ids']:
            if '## ' + qid not in qtext:
                raise ValueError('missing question: ' + qid)
        for s in g['skills']:
            if s['exact_chosen_text'] not in docs['roster.md']:
                raise ValueError('roster text mismatch: ' + s['skill_id'])
            for name in ('mechanic_matrix.md', 'request_design.md'):
                if (g['chinese_name'] + '/' + s['skill_id']) not in docs[name]:
                    raise ValueError('matrix missing skill: ' + name + ' / ' + s['skill_id'])


def check_sources(root, data):
    proof = json.loads((root / 'source_excerpt.json').read_text(encoding='utf-8'))
    manifest = json.loads((root / 'sources_manifest.json').read_text(encoding='utf-8'))
    if proof['qs_revision'] != manifest['qs_revision'] or proof['noname_revision'] != manifest['noname_revision']:
        raise ValueError('source revision drift')
    if 'int max_hp = 4, bool male = true' not in proof['general_constructor_excerpt']:
        raise ValueError('constructor defaults not evidenced')
    for g in data['records']:
        for s in g['skills']:
            key = s['source_key']
            if s.get('source_evidence'):
                evidence = s['source_evidence']
                original = proof['final_lock_alternate_excerpts'][s['skill_id']]
                if (original['text'] != evidence['text'] or original['url'] != evidence['url']
                        or original['key'] != key):
                    raise ValueError('independent fixed source excerpt drift: ' + s['skill_id'])
                alternatives = s['alternative_versions']
                if not any(a['text'] == evidence['text'] and a['source'] == evidence['url']
                           and a['source_key'] == key for a in alternatives):
                    raise ValueError('alternate source evidence drift: ' + s['skill_id'])
                if s['exact_chosen_text'] != evidence['text'] or s['source_url'] != evidence['url']:
                    raise ValueError('chosen alternate source drift: ' + s['skill_id'])
                rev = proof['qs_revision'] if 'Mogara/' in evidence['url'] else proof['noname_revision']
                if '/blob/' + rev + '/' not in evidence['url']:
                    raise ValueError('alternate revision drift: ' + s['skill_id'])
                continue
            if g['year'] == 2018:
                texts = proof['extra_translations']
                text = texts[key + '_info']
                name = texts[key]
                rev = proof['noname_revision']
            else:
                file = 'StandardGeneralPackage.lua' if s['skill_id'] == 'mashu' else 'YJCMPackage.lua' if s['skill_id'] in ('quanji','zili','paiyi') else {2011:'YJCMPackage.lua',2012:'YJCM2012Package.lua',2013:'YJCM2013Package.lua'}[g['year']]
                texts = proof['lua'][file]
                text = texts[':' + key]
                name = texts[key]
                rev = proof['qs_revision']
            if text.replace('\\n','\n').replace('\\"','"') != s['exact_chosen_text'] or name != s['chinese_name']:
                raise ValueError('source text/name drift: ' + s['skill_id'])
            if '/blob/' + rev + '/' not in s['source_url']:
                raise ValueError('source URL revision mismatch: ' + s['skill_id'])
        if g['year'] != 2018:
            slug = g['general_id'].split('_', 1)[1].replace('_','')
            year = 2011 if slug == 'zhonghui' else g['year']
            line = next((line for line in proof['yjcm_constructor_excerpts'][str(year)].splitlines()
                         if '"' + slug + '"' in line), '')
            match = re.search(r'new General\(this, "[^"]+", "([^"]+)"(?:, (\d+))?(?:, (true|false))?\)', line)
            if not match:
                raise ValueError('missing constructor: ' + slug)
            faction, hp, male = match.groups()
            if faction != g['faction'] or int(hp or 4) != g['max_hp'] or ('female' if male == 'false' else 'male') != g['gender']:
                raise ValueError('constructor metadata drift: ' + slug)
        else:
            slug = g['general_id'].split('_god_', 1)[1]
            line = next((line for line in proof['extra_character_excerpt'].splitlines()
                         if 'shen_' + slug + ':' in line), '')
            match = re.search(r'\["(male|female)",\s*"shen",\s*("[0-9/]+"|\d+)', line)
            if not match:
                raise ValueError('missing god character: ' + slug)
            gender, hp_value = match.groups()
            hp_parts = hp_value.strip('"').split('/')
            initial_hp = int(hp_parts[0])
            max_hp = int(hp_parts[-1])
            if gender != g['gender'] or initial_hp != g['base_hp'] or max_hp != g['max_hp'] or g['faction'] != 'god' or g['runtime_faction'] != 'qun':
                raise ValueError('god character metadata drift: ' + slug)


def self_test(data, general_ids, old_skills):
    tests = []
    def reject(name, mutate, ids=general_ids):
        damaged = copy.deepcopy(data)
        mutate(damaged)
        try:
            validate(damaged, ids, old_skills)
        except (ValueError, KeyError):
            tests.append(name)
        else:
            raise AssertionError('mutation was accepted: ' + name)
    reject('production enabled', lambda d: d.update(production=True))
    reject('missing general', lambda d: d['records'].pop())
    reject('duplicate general id', lambda d: d['records'][1].update(general_id=d['records'][0]['general_id']))
    reject('production id collision', lambda d: d['records'][0].update(general_id=general_ids[0]))
    reject('wrong expansion', lambda d: d['records'][0].update(expansion='yj2012'))
    reject('unknown request enum', lambda d: d['records'][0]['skills'][0].update(request_types=['PINDIAN']))
    reject('missing skill text', lambda d: d['records'][0]['skills'][0].update(exact_chosen_text=''))
    reject('unresolved general version', lambda d: d['records'][0].update(question_ids=['Q02']))
    reject('tooltip drift', lambda d: d['records'][1]['skills'][0]['tooltip_metadata'].update(description='wrong'))
    def incompatible(d):
        d['records'][0]['skills'][1]['skill_id'] = 'jueqing'
        d['records'][0]['native_skill_ids'] = ['jueqing']
    reject('incompatible skill collision', incompatible)
    return tests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(args.repo / 'src'))
    from sanguosha.content.characters.standard import ALL_65_GENERAL_POOL, ALL_SKILL_CATALOGUE
    data = json.loads((root / 'catalog.json').read_text(encoding='utf-8'))
    gids = [str(g.id) for g in ALL_65_GENERAL_POOL]
    skills = {str(s.id): s for s in ALL_SKILL_CATALOGUE}
    result = validate(data, gids, skills)
    check_docs(root, data)
    check_sources(root, data)
    if args.self_test:
        result['rejected_mutations'] = self_test(data, gids, skills)
    print(json.dumps({'status': 'PASS', **result}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
