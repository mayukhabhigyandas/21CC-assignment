from collections import defaultdict
from .embeddings import cosine

ALIASES = {
    "js": "javascript", "javascript ": "javascript", "javascript": "javascript",
    "ts": "typescript", "typescript": "typescript",
    "py": "python", "python": "python",
    "postgres": "postgresql", "postgresql": "postgresql",
    "k8s": "kubernetes", "kubernetes": "kubernetes",
    "reactjs": "react", "react": "react",
    "vuejs": "vue", "vue": "vue",
}

def normalize_skill(name: str) -> str:
    cleaned = " ".join(name.strip().lower().replace("_", " ").replace("-", " ").split())
    return ALIASES.get(cleaned, cleaned)

def rule_scores(profile_skills: list[dict], opportunities: list[dict]) -> list[dict]:
    learner = {normalize_skill(s["name"]): int(s["level"]) for s in profile_skills}
    results = []
    for opportunity in opportunities:
        required = opportunity["required_skills"] or []
        total_weight = sum(int(s["weight"]) for s in required)
        earned = 0.0
        matched, missing = [], []
        for skill in required:
            name = normalize_skill(skill["name"])
            minimum = int(skill["minimum_level"])
            weight = int(skill["weight"])
            learner_level = learner.get(name)
            if learner_level is not None and learner_level >= minimum:
                earned += weight
                matched.append(name)
            else:
                if learner_level is not None:
                    partial = learner_level / minimum
                    earned += weight * min(partial, 1.0)
                missing.append({"name": name, "required": minimum, "learner": learner_level})
        score = round((earned / total_weight * 100) if total_weight else 0.0, 2)
        if not required:
            explanation = "No required skills are specified."
        elif matched and missing:
            explanation = f"Matched {len(matched)} skill(s); partial credit or gaps remain for {len(missing)}."
        elif matched:
            explanation = f"Meets all {len(matched)} required skill level(s)."
        else:
            explanation = "No required skill level is met."
        results.append({"opportunity": opportunity, "score": score, "matched": matched, "missing": missing, "explanation": explanation})
    results.sort(key=lambda r: (-r["score"], r["opportunity"]["title"].lower(), r["opportunity"]["id"]))
    return results

def semantic_rank(profile_vector: list[float], opportunities: list[dict]) -> list[dict]:
    if not profile_vector:
        return [{"opportunity": o, "semantic_score": 0.0} for o in sorted(opportunities, key=lambda x: (x["title"].lower(), x["id"]))]
    ranked = [{"opportunity": o, "semantic_score": cosine(profile_vector, o.get("vector") or [])} for o in opportunities]
    ranked.sort(key=lambda r: (-r["semantic_score"], r["opportunity"]["title"].lower(), r["opportunity"]["id"]))
    return ranked[:20]

def hybrid_rank(rule_ranked: list[dict], semantic_ranked: list[dict], limit: int) -> list[dict]:
    rrf = defaultdict(float)
    rule_contrib = {}
    semantic_contrib = {}
    for rank, item in enumerate(rule_ranked, start=1):
        oid = item["opportunity"]["id"]
        rrf[oid] += 60.0 / (60 + rank)
        rule_contrib[oid] = 60.0 / (60 + rank)
    for rank, item in enumerate(semantic_ranked, start=1):
        oid = item["opportunity"]["id"]
        rrf[oid] += 60.0 / (60 + rank)
        semantic_contrib[oid] = 60.0 / (60 + rank)
    rule_by_id = {r["opportunity"]["id"]: r for r in rule_ranked}
    opportunity_by_id = {r["opportunity"]["id"]: r["opportunity"] for r in rule_ranked}
    ranked = sorted(rrf, key=lambda oid: (-rrf[oid], opportunity_by_id[oid]["title"].lower(), oid))[:limit]
    return [{
        "opportunity": opportunity_by_id[oid],
        "score": round(rrf[oid] * 100, 2),
        "rule": rule_by_id[oid],
        "rule_contribution": round(rule_contrib.get(oid, 0.0) * 100, 2),
        "semantic_contribution": round(semantic_contrib.get(oid, 0.0) * 100, 2),
    } for oid in ranked]
