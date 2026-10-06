"""Source-scoped temporary grants coexist with native and earlier grants."""
def add_grant(state,pid,skill,source):
    player=state.players[pid]
    sources=state.metadata.setdefault('skill_grant_sources',{}).setdefault(pid,{}).setdefault(skill,[])
    current=player.granted_skills.get(skill)
    if current and current not in sources:sources.append(current)
    if source not in sources:sources.append(source)
    player.granted_skills.setdefault(skill,source)


def remove_grant(state,pid,skill,source):
    player=state.players[pid]
    all_sources=state.metadata.get('skill_grant_sources',{}).get(pid,{})
    sources=all_sources.get(skill,[])
    current=player.granted_skills.get(skill)
    if current and current not in sources:sources.append(current)
    sources=[s for s in sources if s!=source]
    if sources:
        all_sources[skill]=sources
        player.granted_skills[skill]=sources[0]
    else:
        all_sources.pop(skill,None)
        if current==source:player.granted_skills.pop(skill,None)


def grant_sources(state,pid,skill):
    sources=list(state.metadata.get('skill_grant_sources',{}).get(pid,{}).get(skill,[]))
    current=state.players[pid].granted_skills.get(skill)
    if current and current not in sources:sources.append(current)
    return tuple(sources)
