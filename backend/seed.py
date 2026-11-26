from app.database import initialize_database, SessionLocal
from app.models import User, Profile, Opportunity
from app.auth import hash_password
from app.embeddings import embed_text
from app.matching import normalize_skill

initialize_database()
db = SessionLocal()

if db.query(User).count():
    print("Database already seeded")
    db.close()
    raise SystemExit

admin = User(email="admin@example.com", password_hash=hash_password("admin123"), role="admin")
db.add(admin)

learners = [
    ("learner1@example.com", "Python and SQL data pipelines", [("Python", 4), ("SQL", 4), ("ETL", 3)]),
    ("learner2@example.com", "Frontend with React and JavaScript", [("JavaScript", 4), ("React", 4), ("CSS", 3)]),
    ("learner3@example.com", "Backend developer using Java and Spring", [("Java", 4), ("Spring Boot", 4), ("SQL", 3)]),
    ("learner4@example.com", "Cloud operations and Kubernetes", [("Kubernetes", 4), ("Docker", 4), ("AWS", 3)]),
    ("learner5@example.com", "Data science with Python and pandas", [("Python", 4), ("Pandas", 4), ("Machine Learning", 3)]),
]
for email, bio, skills in learners:
    user = User(email=email, password_hash=hash_password("learner123"), role="learner")
    db.add(user); db.flush()
    normalized = [{"name": normalize_skill(name), "level": level} for name, level in skills]
    text = f"{bio} " + " ".join(f"{s['name']} level {s['level']}" for s in normalized)
    db.add(Profile(user_id=user.id, bio=bio, skills=normalized, vector=embed_text(text)))

opportunities = [
    ("Junior Python Developer","job","Build REST APIs and data services with Python.","Bangalore / Hybrid",[("python",5,3),("sql",4,2),("fastapi",3,2)]),
    ("Backend Engineer","job","Develop scalable Java services and SQL databases.","Remote",[("java",5,4),("spring boot",4,3),("sql",3,3)]),
    ("React Frontend Engineer","job","Create accessible React interfaces in JavaScript.","London / Remote",[("react",5,3),("javascript",4,3),("css",3,2)]),
    ("Data Engineer","job","Move and transform data using ETL, Airflow and Python.","Bangalore / Hybrid",[("etl",5,3),("airflow",5,3),("python",4,3),("sql",4,3)]),
    ("DevOps Engineer","job","Operate Docker containers and Kubernetes clusters on AWS.","Berlin / Hybrid",[("docker",5,3),("kubernetes",5,4),("aws",4,3)]),
    ("Machine Learning Engineer","job","Train and deploy machine learning models with Python.","Remote",[("python",5,4),("machine learning",5,4),("pandas",3,3)]),
    ("Full Stack Developer","job","Build React frontends and Node.js backend APIs.","Singapore / Onsite",[("react",4,3),("node.js",5,3),("javascript",4,3)]),
    ("Cloud Solutions Architect","job","Design Azure and AWS cloud platforms.","Sydney / Hybrid",[("azure",5,4),("aws",5,4),("docker",3,2)]),
    ("Data Analyst","job","Analyze data with SQL and Python; build clear reports.","Mumbai / Hybrid",[("sql",5,3),("python",4,3),("data analysis",4,3)]),
    ("Java Microservices Engineer","job","Build Spring Boot microservices and deploy with Docker.","Remote",[("java",5,4),("spring boot",5,4),("docker",3,2)]),
    ("Python for Data Science","course","Practical Python, pandas and NumPy for beginners.","Online / Self-paced",[("python",5,2),("pandas",4,2),("numpy",3,1)]),
    ("Modern React Course","course","Learn components, hooks and TypeScript.","Online / Live",[("react",5,2),("javascript",3,2),("typescript",4,2)]),
    ("Kubernetes Fundamentals","course","Deploy container workloads and services.","Online / Live",[("kubernetes",5,2),("docker",4,2)]),
    ("Data Engineering with Airflow","course","Build ETL workflows and scheduled pipelines.","Online / Self-paced",[("etl",5,2),("airflow",5,2),("python",3,2)]),
    ("SQL and Database Design","course","Learn PostgreSQL, relational modeling and queries.","Online / Live",[("sql",5,2),("postgresql",5,2)]),
]
for title, kind, description, location, skills in opportunities:
    required = [{"name": normalize_skill(name), "weight": weight, "minimum_level": minimum} for name, weight, minimum in skills]
    text = f"{title} {description} {' '.join(s['name'] for s in required)}"
    db.add(Opportunity(title=title, type=kind, description=description, location_or_mode=location,
                       required_skills=required, vector=embed_text(text)))

db.commit()
db.close()
print("Seeded 1 admin, 5 learners, and 15 opportunities")
