import re
from .matching import normalize_skill

SKILLS = [
    "python","java","javascript","typescript","react","vue","node.js","sql","postgresql","mongodb",
    "docker","kubernetes","aws","azure","git","linux","machine learning","data analysis","etl",
    "airflow","pandas","numpy","fastapi","django","flask","spring boot","rest api"
]

def extract_skills(text: str) -> list[dict]:
    lowered = text.lower()
    found = {}
    for skill in SKILLS:
        pattern = r"(?<![a-z0-9])" + re.escape(skill).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
        match = re.search(pattern, lowered)
        if not match:
            continue
        window = lowered[max(0, match.start()-40):min(len(lowered), match.end()+40)]
        level = 1
        if re.search(r"\b(expert|lead|architect|10\+ years|8\+ years)\b", window): level = 5
        elif re.search(r"\b(advanced|senior|5\+ years|6\+ years|7\+ years)\b", window): level = 4
        elif re.search(r"\b(intermediate|experienced|3\+ years|4\+ years)\b", window): level = 3
        elif re.search(r"\b(basic|beginner|1 year|2 years)\b", window): level = 2
        found[normalize_skill(skill)] = {"name": normalize_skill(skill), "level": level, "confidence": 0.85 if level > 1 else 0.7}
    return sorted(found.values(), key=lambda x: (-x["confidence"], -x["level"], x["name"]))
