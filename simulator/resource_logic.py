def can_pay_cost(state, card):
    # Rule 7-5-2-2-2: Lv Condition
    total_resources = len(state.resource_area) + state.ex_resources
    if total_resources < card.lv:
        return False
        
    # Rule 7-5-2-2-3: Cost Payment
    active_resources = [r for r in state.resource_area if r.is_active]
    if len(active_resources) < card.cost:
        return False
        
    return True