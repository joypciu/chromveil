from chromveil.intelligence.llm_collect import parse_collect_intent


def test_heuristic_intent_extracts_keywords():
    intent = parse_collect_intent("show me live odds and market prices", use_llm=False)
    assert "odds" in intent["want"]
    assert "market" in intent["want"] or "prices" in intent["want"]
