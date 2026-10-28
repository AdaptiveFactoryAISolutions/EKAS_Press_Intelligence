"""Public, scenario-independent pairwise instrumentation model."""
from itertools import combinations
from ..domain import catalog, signals


def assess(available):
    available=set(available)
    classes=catalog()
    pairs=[]
    for a,b in combinations(classes,2):
        required=set(a['discriminating_signals'].get(b['event_class'],[])) | set(b['discriminating_signals'].get(a['event_class'],[]))
        # A discriminator set is conjunctive: every listed observation is needed.
        separated=bool(required) and required <= available
        pairs.append({'classes':[a['event_class'],b['event_class']], 'required_observations':sorted(required), 'available_observations':sorted(required & available), 'missing_discriminators':sorted(required-available), 'distinguishable':separated,'feature_rules':a.get('discrimination_rules',{}).get(b['event_class'],b.get('discrimination_rules',{}).get(a['event_class'],{}))})
    outcomes=[]
    for item in classes:
        relevant=[p for p in pairs if item['event_class'] in p['classes']]
        observed=sorted(set(item['observable_signals']) & available)
        separated=sum(p['distinguishable'] for p in relevant)
        state='NOT_OBSERVABLE' if not observed else ('FULLY_DISTINGUISHABLE' if separated==len(relevant) else ('PARTIALLY_DISTINGUISHABLE' if separated else 'INDISTINGUISHABLE'))
        outcomes.append({'event_class':item['event_class'],'status':state,'required_observations':item['observable_signals'],'available_observations':observed,'competing_fault_classes':item['competing_causes'],'separated_pairs':separated,'total_pairs':len(relevant)})
    # Connected components express unresolved ambiguity, not a claim that pairwise
    # indistinguishability is transitive. Exact unresolved edges remain in pairs.
    remaining={c['event_class'] for c in classes}; groups=[]
    while remaining:
        group={min(remaining)}
        while True:
            expanded=group|{name for p in pairs if not p['distinguishable'] and group.intersection(p['classes']) for name in p['classes']}
            if expanded==group: break
            group=expanded
        remaining-=group
        if len(group)>1: groups.append(sorted(group))
    full=sum(c['status']=='FULLY_DISTINGUISHABLE' for c in outcomes)
    count=sum(p['distinguishable'] for p in pairs)
    return {'classes':outcomes,'pairs':pairs,'unresolved_equivalence_groups':groups,'equivalence_group_semantics':'Connected unresolved-pair components; inspect pair edges for exact ambiguity.', 'coverage':{'numerator':full,'denominator':len(classes),'definition':'Classes separated from every other catalog class and observable'},'pair_coverage':{'numerator':count,'denominator':len(pairs),'definition':'Pairs with every required discriminator available'},'available_signals':sorted(available)}


def sensor_gaps(available):
    baseline=assess(available); current=baseline['pair_coverage']['numerator']; result=[]
    for signal in signals():
        name=signal['signal_id']
        if name in available: continue
        augmented=assess(list(available)+[name]); gain=augmented['pair_coverage']['numerator']-current
        if gain<=0: continue
        separated=[p['classes'] for p,q in zip(augmented['pairs'],baseline['pairs']) if p['distinguishable'] and not q['distinguishable']]
        result.append({'signal':name,'fault_classes_separated':separated,'ambiguity_reduced':separated,'current_source_available':signal.get('existing',False),'plc_input_possible':signal.get('kind') in ('discrete','analog','plc'),'kind':signal.get('kind'),'hardware_required':signal.get('hardware_required',True),'priority':signal.get('priority',6),'expected_diagnostic_gain':{'pairs':gain,'pair_denominator':len(baseline['pairs']),'fully_distinguishable_classes':augmented['coverage']['numerator']-baseline['coverage']['numerator']},'calculation':'Recompute assess(available + signal); gains are conditional and must not be added.'})
    return sorted(result,key=lambda g:(g['priority'],-g['expected_diagnostic_gain']['pairs'],g['signal']))
