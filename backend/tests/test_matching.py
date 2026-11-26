from app.matching import normalize_skill, rule_scores

def test_skill_normalization():
    assert normalize_skill(" JS ") == "javascript"
    assert normalize_skill("Java_Script") == "java script"

def test_weighted_rule_score_and_ties():
    opportunity = {"id":1,"title":"B","required_skills":[{"name":"python","weight":5,"minimum_level":4},{"name":"sql","weight":3,"minimum_level":3}]}
    result = rule_scores([{"name":"Python","level":4},{"name":"SQL","level":1}], [opportunity])[0]
    assert result["score"] == 75.0
    assert "python" in result["matched"]
