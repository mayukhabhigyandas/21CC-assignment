from fastapi import FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import User, Profile, Opportunity
from .schemas import *
from .auth import hash_password, verify_password, create_token, current_user, admin_user
from .embeddings import embed_text
from .matching import normalize_skill, rule_scores, semantic_rank, hybrid_rank
from .extraction import extract_skills

app = FastAPI(title="Skill Opportunity Matcher", version="1.0")

@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status.HTTP_422_UNPROCESSABLE_ENTITY, {"error": {"code": "VALIDATION_ERROR", "message": "Invalid request", "details": exc.errors()}})

@app.exception_handler(HTTPException)
async def http_handler(request: Request, exc: HTTPException):
    return JSONResponse(exc.status_code, {"error": {"code": "HTTP_ERROR", "message": exc.detail}})

@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)

@app.post("/auth/signup", response_model=Token)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter_by(email=payload.email.lower()).first():
        raise HTTPException(409, "Email already registered")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.flush()
    if user.role == "learner":
        db.add(Profile(user_id=user.id, bio="", skills=[]))
    db.commit()
    db.refresh(user)
    return Token(access_token=create_token(user))

@app.post("/auth/login", response_model=Token)
def login(payload: Login, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return Token(access_token=create_token(user))

@app.post("/opportunities", status_code=201)
def create_opportunity(payload: OpportunityCreate, db: Session = Depends(get_db), admin: User = Depends(admin_user)):
    skills = [s.model_dump() for s in payload.required_skills]
    seen = {}
    for skill in skills:
        skill["name"] = normalize_skill(skill["name"])
        seen[skill["name"]] = skill
    opportunity = Opportunity(**payload.model_dump(exclude={"required_skills"}), required_skills=list(seen.values()))
    text = f"{opportunity.title} {opportunity.description} {' '.join(normalize_skill(s['name']) for s in seen.values())}"
    opportunity.vector = embed_text(text)
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity_row(opportunity)

@app.get("/opportunities")
def search_opportunities(q: str = "", type: str | None = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    query = db.query(Opportunity)
    if type:
        if type not in ("job", "course"): raise HTTPException(422, "type must be job or course")
        query = query.filter(Opportunity.type == type)
    if q:
        term = f"%{q.lower()}%"
        query = query.filter(or_(Opportunity.title.ilike(term), Opportunity.description.ilike(term)))
    total = query.count()
    rows = query.order_by(Opportunity.title, Opportunity.id).offset((page-1)*limit).limit(limit).all()
    return {"items": [opportunity_row(row) for row in rows], "page": page, "limit": limit, "total": total}

@app.get("/opportunities/{opportunity_id}")
def get_opportunity(opportunity_id: int, db: Session = Depends(get_db)):
    row = db.get(Opportunity, opportunity_id)
    if not row: raise HTTPException(404, "Opportunity not found")
    return opportunity_row(row)

@app.put("/opportunities/{opportunity_id}")
def update_opportunity(opportunity_id: int, payload: OpportunityUpdate, db: Session = Depends(get_db), admin: User = Depends(admin_user)):
    row = db.get(Opportunity, opportunity_id)
    if not row: raise HTTPException(404, "Opportunity not found")
    updates = payload.model_dump(exclude_unset=True)
    if "required_skills" in updates:
        seen = {}
        for skill in updates["required_skills"]:
            skill = skill.model_dump()
            skill["name"] = normalize_skill(skill["name"])
            seen[skill["name"]] = skill
        updates["required_skills"] = list(seen.values())
    for key, value in updates.items(): setattr(row, key, value)
    text = f"{row.title} {row.description} {' '.join(normalize_skill(s['name']) for s in row.required_skills)}"
    row.vector = embed_text(text)
    db.commit()
    db.refresh(row)
    return opportunity_row(row)

@app.delete("/opportunities/{opportunity_id}", status_code=204)
def delete_opportunity(opportunity_id: int, db: Session = Depends(get_db), admin: User = Depends(admin_user)):
    row = db.get(Opportunity, opportunity_id)
    if not row: raise HTTPException(404, "Opportunity not found")
    db.delete(row)
    db.commit()
    return None

@app.get("/profile")
def get_profile(db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role != "learner": raise HTTPException(403, "Learner profile required")
    profile = db.query(Profile).filter_by(user_id=user.id).first()
    if not profile:
        profile = Profile(user_id=user.id, bio="", skills=[], vector=embed_text(""))
        db.add(profile); db.commit(); db.refresh(profile)
    return {"bio": profile.bio, "skills": profile.skills}

@app.put("/profile")
def update_profile(payload: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role != "learner": raise HTTPException(403, "Learner profile required")
    profile = db.query(Profile).filter_by(user_id=user.id).first()
    if not profile:
        profile = Profile(user_id=user.id); db.add(profile)
    seen = {}
    for skill in payload.skills:
        data = skill.model_dump()
        data["name"] = normalize_skill(data["name"])
        seen[data["name"]] = data
    profile.bio = payload.bio
    profile.skills = list(seen.values())
    skill_text = " ".join(f"{s['name']} level {s['level']}" for s in profile.skills)
    profile.vector = embed_text(f"{profile.bio} {skill_text}")
    db.commit()
    db.refresh(profile)
    return {"bio": profile.bio, "skills": profile.skills}

@app.post("/profile/extract-skills")
def extract_profile_skills(payload: dict, user: User = Depends(current_user)):
    text = payload.get("resume_text", "")
    if not isinstance(text, str) or len(text) > 20000:
        raise HTTPException(422, "resume_text must be a string of at most 20000 characters")
    # Resume text is treated only as data: no instructions or templates are executed.
    return {"skills": extract_skills(text)}

def opportunity_row(row: Opportunity) -> dict:
    return {"id": row.id, "title": row.title, "type": row.type, "description": row.description,
            "location_or_mode": row.location_or_mode, "required_skills": row.required_skills}

def opportunity_dict(row: Opportunity) -> dict:
    return {**opportunity_row(row), "vector": row.vector}

@app.get("/matches")
def matches(mode: str = "hybrid", type: str | None = None, limit: int = Query(20, ge=1, le=100),
            db: Session = Depends(get_db), user: User = Depends(current_user)):
    if user.role != "learner": raise HTTPException(403, "Learner role required")
    if mode not in ("rules", "hybrid"): raise HTTPException(422, "mode must be rules or hybrid")
    if type and type not in ("job", "course"): raise HTTPException(422, "type must be job or course")
    profile = db.query(Profile).filter_by(user_id=user.id).first()
    if not profile:
        profile = Profile(user_id=user.id, bio="", skills=[], vector=embed_text(""))
    query = db.query(Opportunity)
    if type: query = query.filter(Opportunity.type == type)
    opportunities = [opportunity_dict(row) for row in query.all()]
    rules = rule_scores(profile.skills or [], opportunities)
    semantic = semantic_rank(profile.vector or [], opportunities)
    if mode == "rules":
        return {"items": [{
            "opportunity": r["opportunity"],
            "score": r["score"],
            "matched_skills": r["matched"],
            "missing_skills": r["missing"],
            "explanation": r["explanation"],
            "signals": {"rule": r["score"], "semantic": None}
        } for r in rules[:limit]]}
    return {"items": [{
        "opportunity": r["rule"]["opportunity"],
        "score": r["score"],
        "matched_skills": r["rule"]["matched"],
        "missing_skills": r["rule"]["missing"],
        "explanation": r["rule"]["explanation"],
        "signals": {"rule_contribution": r["rule_contribution"], "semantic_contribution": r["semantic_contribution"]}
    } for r in hybrid_rank(rules, semantic, limit)]}

@app.get("/agent/tools")
def agent_tools():
    import json, pathlib
    path = pathlib.Path(__file__).parent.parent / "agent" / "tools.json"
    return JSONResponse(json.loads(path.read_text()))

@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(__import__("sqlalchemy").text("SELECT 1"))
    return {"status": "ok"}
