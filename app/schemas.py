from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

SkillName = str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["admin", "learner"] = "learner"

class Login(BaseModel):
    email: str
    password: str

class RequiredSkill(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    weight: int = Field(ge=1, le=5)
    minimum_level: int = Field(ge=1, le=5)

class OpportunityCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: Literal["job", "course"]
    description: str = Field(min_length=1, max_length=10000)
    location_or_mode: str = Field(min_length=1, max_length=200)
    required_skills: list[RequiredSkill] = []

class OpportunityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    type: Literal["job", "course"] | None = None
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    location_or_mode: str | None = Field(default=None, min_length=1, max_length=200)
    required_skills: list[RequiredSkill] | None = None

class LearnerSkill(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    level: int = Field(ge=1, le=5)

class ProfileUpdate(BaseModel):
    bio: str = Field(default="", max_length=500)
    skills: list[LearnerSkill] = []
