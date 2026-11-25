import json
from app.matching import rule_scores, semantic_rank, hybrid_rank
from app.embeddings import embed_text

# Opportunity text and relevance labels are synthetic and contain no personal data.
opportunities = [
    {"id": i + 1, "title": title, "type": kind, "description": desc, "location_or_mode": "Online", "required_skills": skills,
     "vector": embed_text(title + " " + desc)}
    for i, (title, kind, desc, skills) in enumerate([
        ("Data Engineer","job","ETL Airflow Python SQL",[{"name":"etl","weight":5,"minimum_level":3},{"name":"airflow","weight":5,"minimum_level":3},{"name":"python","weight":4,"minimum_level":3}]),
        ("Python Developer","job","FastAPI Python REST SQL",[{"name":"python","weight":5,"minimum_level":3},{"name":"sql","weight":3,"minimum_level":2},{"name":"fastapi","weight":3,"minimum_level":2}]),
        ("React Engineer","job","JavaScript React CSS frontend",[{"name":"javascript","weight":5,"minimum_level":3},{"name":"react","weight":5,"minimum_level":3},{"name":"css","weight":2,"minimum_level":2}]),
        ("Java Engineer","job","Java Spring Boot SQL",[{"name":"java","weight":5,"minimum_level":3},{"name":"spring boot","weight":5,"minimum_level":3},{"name":"sql","weight":3,"minimum_level":2}]),
        ("DevOps Engineer","job","Docker Kubernetes AWS",[{"name":"docker","weight":5,"minimum_level":3},{"name":"kubernetes","weight":5,"minimum_level":3},{"name":"aws","weight":4,"minimum_level":3}]),
        ("Machine Learning","course","Python pandas machine learning",[{"name":"python","weight":5,"minimum_level":2},{"name":"pandas","weight":4,"minimum_level":2},{"name":"machine learning","weight":5,"minimum_level":2}]),
        ("SQL Course","course","PostgreSQL database modeling",[{"name":"sql","weight":5,"minimum_level":1},{"name":"postgresql","weight":5,"minimum_level":1}]),
        ("Cloud Course","course","Azure AWS infrastructure",[{"name":"azure","weight":5,"minimum_level":1},{"name":"aws","weight":5,"minimum_level":1}]),
        ("JavaScript Course","course","JavaScript TypeScript basics",[{"name":"javascript","weight":5,"minimum_level":1},{"name":"typescript","weight":4,"minimum_level":1}]),
        ("Full Stack","job","React Node JavaScript",[{"name":"react","weight":4,"minimum_level":3},{"name":"node.js","weight":5,"minimum_level":3},{"name":"javascript","weight":4,"minimum_level":3}]),
        ("Linux Admin","job","Linux systems shell",[{"name":"linux","weight":5,"minimum_level":3},{"name":"git","weight":2,"minimum_level":2}]),
        ("Business Analyst","job","Reporting data analysis SQL",[{"name":"data analysis","weight":5,"minimum_level":3},{"name":"sql","weight":4,"minimum_level":2}]),
    ])]

learners = [
    {"name":"data-pipeline","bio":"Data engineering ETL Airflow SQL","skills":[{"name":"ETL","level":4},{"name":"Airflow","level":4},{"name":"Python","level":3},{"name":"SQL","level":4}],"relevant":[1]},
    {"name":"python-api","bio":"Python FastAPI REST APIs","skills":[{"name":"Python","level":4},{"name":"FastAPI","level":4},{"name":"SQL","level":3}],"relevant":[2]},
    {"name":"frontend","bio":"JavaScript React frontend","skills":[{"name":"JavaScript","level":4},{"name":"React","level":4},{"name":"CSS","level":3}],"relevant":[3,10]},
    {"name":"java","bio":"Java Spring backend","skills":[{"name":"Java","level":4},{"name":"Spring Boot","level":4},{"name":"SQL","level":3}],"relevant":[4]},
    {"name":"devops","bio":"Docker Kubernetes AWS cloud","skills":[{"name":"Docker","level":4},{"name":"Kubernetes","level":4},{"name":"AWS","level":3}],"relevant":[5]},
    {"name":"ml","bio":"Python pandas machine learning","skills":[{"name":"Python","level":4},{"name":"Pandas","level":4},{"name":"Machine Learning","level":3}],"relevant":[6]},
    {"name":"sql","bio":"SQL PostgreSQL databases","skills":[{"name":"SQL","level":4},{"name":"PostgreSQL","level":4}],"relevant":[7]},
    {"name":"cloud","bio":"Azure AWS infrastructure","skills":[{"name":"Azure","level":4},{"name":"AWS","level":4}],"relevant":[8]},
    {"name":"javascript","bio":"JavaScript TypeScript web","skills":[{"name":"JavaScript","level":4},{"name":"TypeScript","level":3}],"relevant":[9,3,10]},
    {"name":"analyst","bio":"SQL reporting data analysis","skills":[{"name":"SQL","level":4},{"name":"Data Analysis","level":4}],"relevant":[12]},
]

def metrics(ranked_ids, relevant):
    relevant = set(relevant)
    top = ranked_ids[:5]
    hits = sum(1 for oid in top if oid in relevant)
    precision = hits / 5
    dcg = sum((1 / __import__("math").log2(i + 2)) for i, oid in enumerate(top) if oid in relevant)
    ideal = sum(1 / __import__("math").log2(i + 2) for i in range(min(5, len(relevant))))
    return precision, dcg / ideal

totals = {"rules": [0,0], "semantic": [0,0], "hybrid":[0,0]}
with open("evaluation/labelled_data.json", "w", encoding="utf-8") as f:
    json.dump(learners, f, indent=2)
for learner in learners:
    profile_vector = embed_text(learner["bio"] + " " + " ".join(s["name"] for s in learner["skills"]))
    rules = rule_scores(learner["skills"], opportunities)
    semantic = semantic_rank(profile_vector, opportunities)
    hybrid = hybrid_rank(rules, semantic, 5)
    sets = {
        "rules": [r["opportunity"]["id"] for r in rules[:5]],
        "semantic": [r["opportunity"]["id"] for r in semantic[:5]],
        "hybrid": [r["opportunity"]["id"] for r in hybrid[:5]],
    }
    for name, ids in sets.items():
        p, n = metrics(ids, learner["relevant"])
        totals[name][0] += p; totals[name][1] += n

result = {name: {"precision_at_5": round(values[0]/len(learners),4), "ndcg_at_5": round(values[1]/len(learners),4)}
          for name, values in totals.items()}
print(json.dumps(result, indent=2))
