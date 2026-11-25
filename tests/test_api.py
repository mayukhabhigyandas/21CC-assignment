import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["EMBEDDING_PROVIDER"] = "off"
from fastapi.testclient import TestClient
from app.database import Base, engine, SessionLocal
from app.main import app

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
client = TestClient(app)

def signup(email="learner@test.local", role="learner", password="password123"):
    response = client.post("/auth/signup", json={"email":email,"password":password,"role":role})
    assert response.status_code == 200
    return response.json()["access_token"]

def auth(token): return {"Authorization": f"Bearer {token}"}

def test_signup_login_and_profile_isolation():
    token1 = signup("one@test.local")
    token2 = signup("two@test.local")
    client.put("/profile", headers=auth(token1), json={"bio":"Python", "skills":[{"name":" JS ","level":4}]})
    client.put("/profile", headers=auth(token2), json={"bio":"Java", "skills":[{"name":"Java","level":5}]})
    assert client.get("/profile", headers=auth(token1)).json()["skills"][0]["name"] == "javascript"
    assert client.get("/profile", headers=auth(token2)).json()["skills"][0]["name"] == "java"

def test_admin_only_crud():
    learner = signup("learner@test.local")
    admin = signup("admin@test.local", "admin")
    payload={"title":"Python Engineer","type":"job","description":"Python APIs","location_or_mode":"Remote","required_skills":[{"name":"Python","weight":5,"minimum_level":3}]}
    assert client.post("/opportunities", headers=auth(learner), json=payload).status_code == 403
    created = client.post("/opportunities", headers=auth(admin), json=payload)
    assert created.status_code == 201

def test_rules_matching_and_empty_skills():
    token = signup("rules@test.local")
    admin = signup("rules-admin@test.local", "admin")
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
