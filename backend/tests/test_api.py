import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["EMBEDDING_PROVIDER"] = "off"
from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal
from app.auth import create_token, hash_password
from app.main import app
from app.models import User

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)

def signup(email="learner@test.local", password="password123"):
    response = client.post("/auth/signup", json={"email":email,"password":password})
    assert response.status_code == 200
    return response.json()["access_token"]

def create_admin(email):
    db = SessionLocal()
    user = User(email=email, password_hash=hash_password("password123"), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user)
    db.close()
    return token

def auth(token): return {"Authorization": f"Bearer {token}"}

def test_frontend_cors_preflight():
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

def test_signup_login_and_profile_isolation():
    token1 = signup("one@test.local")
    token2 = signup("two@test.local")
    client.put("/profile", headers=auth(token1), json={"bio":"Python", "skills":[{"name":" JS ","level":4}]})
    client.put("/profile", headers=auth(token2), json={"bio":"Java", "skills":[{"name":"Java","level":5}]})
    assert client.get("/profile", headers=auth(token1)).json()["skills"][0]["name"] == "javascript"
    assert client.get("/profile", headers=auth(token2)).json()["skills"][0]["name"] == "java"

def test_signup_rejects_client_selected_role():
    response = client.post(
        "/auth/signup",
        json={"email":"role-override@test.local","password":"password123","role":"admin"},
    )
    assert response.status_code == 422
    assert signup("role-override@test.local")

def test_admin_only_crud():
    learner = signup("learner@test.local")
    admin = create_admin("admin@test.local")
    payload={"title":"Python Engineer","type":"job","description":"Python APIs","location_or_mode":"Remote","required_skills":[{"name":"Python","weight":5,"minimum_level":3}]}
    assert client.post("/opportunities", headers=auth(learner), json=payload).status_code == 403
    created = client.post("/opportunities", headers=auth(admin), json=payload)
    assert created.status_code == 201

def test_explain_match_returns_only_the_requested_opportunity():
    learner = signup("explain@test.local")
    admin = create_admin("explain-admin@test.local")
    headers = auth(admin)
    payload = {
        "title":"Python Engineer",
        "type":"job",
        "description":"Build Python APIs",
        "location_or_mode":"Remote",
        "required_skills":[{"name":"Python","weight":5,"minimum_level":3}],
    }
    created = client.post("/opportunities", headers=headers, json=payload)
    assert created.status_code == 201
    opportunity_id = created.json()["id"]

    response = client.get(f"/matches/{opportunity_id}", headers=auth(learner))
    assert response.status_code == 200
    assert response.json()["opportunity"]["id"] == opportunity_id
    assert "vector" not in response.json()["opportunity"]
    assert response.json()["explanation"]
    assert client.get("/matches/99999", headers=auth(learner)).status_code == 404
    hybrid = client.get("/matches?mode=hybrid", headers=auth(learner))
    assert hybrid.status_code == 200

def test_rules_matching_and_empty_skills():
    token = signup("rules@test.local")
    admin = create_admin("rules-admin@test.local")
    payload={"title":"Skillless Course","type":"course","description":"Introductory course","location_or_mode":"Online","required_skills":[]}
    client.post("/opportunities", headers=auth(admin), json=payload)
    client.put("/profile", headers=auth(token), json={"bio":"","skills":[]})
    result = client.get("/matches?mode=rules", headers=auth(token))
    assert result.status_code == 200
    assert len(result.json()["items"]) >= 1

def test_extraction_no_llm_and_validation():
    token = signup("extract@test.local")
    result = client.post("/profile/extract-skills", headers=auth(token), json={"resume_text":"Senior Python developer with 5+ years and Docker experience"})
    names = {x["name"] for x in result.json()["skills"]}
    assert "python" in names
    assert client.post("/profile/extract-skills", headers=auth(token), json={"resume_text":""}).status_code == 200
