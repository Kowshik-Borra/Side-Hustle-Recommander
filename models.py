"""
models.py
Core OOP domain classes for the Side Hustle Recommendation System.
"""

from datetime import datetime
from utils import normalize_skill


class User:
    """Represents a registered user and their profile for matching."""

    def __init__(
        self,
        user_id,
        username,
        email,
        password_hash,
        full_name="",
        skills=None,
        interests=None,
        experience_level="Beginner",
        available_time_hours=5,
        earning_goal_monthly=5000,
        investment_capacity="None",
        saved_hustles=None,
        created_at=None,
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.skills = skills or []
        self.interests = interests or []
        self.experience_level = experience_level  # Beginner/Intermediate/Advanced
        self.available_time_hours = int(available_time_hours)
        self.earning_goal_monthly = int(earning_goal_monthly)
        self.investment_capacity = investment_capacity  # None/Low/Medium/High
        self.saved_hustles = saved_hustles or []  # list of {hustle_id, status, saved_at}
        self.created_at = created_at or datetime.utcnow().isoformat()

    # -- profile helpers -----------------------------------------------
    def normalized_skills(self):
        return {normalize_skill(s) for s in self.skills}

    def has_profile(self):
        """True once the user has filled in the matching-relevant fields."""
        return bool(self.skills or self.interests)

    def update_profile(self, skills=None, interests=None, experience_level=None,
                        available_time_hours=None, earning_goal_monthly=None,
                        investment_capacity=None, full_name=None):
        if skills is not None:
            self.skills = skills
        if interests is not None:
            self.interests = interests
        if experience_level is not None:
            self.experience_level = experience_level
        if available_time_hours is not None:
            self.available_time_hours = int(available_time_hours)
        if earning_goal_monthly is not None:
            self.earning_goal_monthly = int(earning_goal_monthly)
        if investment_capacity is not None:
            self.investment_capacity = investment_capacity
        if full_name is not None:
            self.full_name = full_name

    # -- saved hustle tracking -------------------------------------------
    def save_hustle(self, hustle_id, status="Interested"):
        for entry in self.saved_hustles:
            if entry["hustle_id"] == hustle_id:
                entry["status"] = status
                return
        self.saved_hustles.append({
            "hustle_id": hustle_id,
            "status": status,
            "saved_at": datetime.utcnow().isoformat(),
        })

    def remove_saved_hustle(self, hustle_id):
        self.saved_hustles = [e for e in self.saved_hustles if e["hustle_id"] != hustle_id]

    def update_saved_status(self, hustle_id, status):
        for entry in self.saved_hustles:
            if entry["hustle_id"] == hustle_id:
                entry["status"] = status
                return True
        return False

    # -- serialization ---------------------------------------------------
    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "full_name": self.full_name,
            "skills": self.skills,
            "interests": self.interests,
            "experience_level": self.experience_level,
            "available_time_hours": self.available_time_hours,
            "earning_goal_monthly": self.earning_goal_monthly,
            "investment_capacity": self.investment_capacity,
            "saved_hustles": self.saved_hustles,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            email=data["email"],
            password_hash=data["password_hash"],
            full_name=data.get("full_name", ""),
            skills=data.get("skills", []),
            interests=data.get("interests", []),
            experience_level=data.get("experience_level", "Beginner"),
            available_time_hours=data.get("available_time_hours", 5),
            earning_goal_monthly=data.get("earning_goal_monthly", 5000),
            investment_capacity=data.get("investment_capacity", "None"),
            saved_hustles=data.get("saved_hustles", []),
            created_at=data.get("created_at"),
        )


class SideHustle:
    """Represents a single side hustle opportunity in the catalog."""

    def __init__(self, id, name, category, required_skills, interests,
                 investment_level, investment_amount_range, time_required_hours_per_week,
                 difficulty, earning_range_monthly, time_to_first_income_weeks,
                 resources_needed, description):
        self.id = id
        self.name = name
        self.category = category
        self.required_skills = required_skills
        self.interests = interests
        self.investment_level = investment_level
        self.investment_amount_range = investment_amount_range
        self.time_required_hours_per_week = time_required_hours_per_week
        self.difficulty = difficulty
        self.earning_range_monthly = earning_range_monthly
        self.time_to_first_income_weeks = time_to_first_income_weeks
        self.resources_needed = resources_needed
        self.description = description

    def normalized_required_skills(self):
        return {normalize_skill(s) for s in self.required_skills}

    def skill_gap(self, user: User):
        """Skills required by this hustle that the user doesn't currently have."""
        user_skills = user.normalized_skills()
        gap = []
        for skill in self.required_skills:
            if normalize_skill(skill) not in user_skills:
                gap.append(skill)
        return gap

    def combined_text(self):
        """Text blob of skills+interests used for TF-IDF vectorization."""
        return " ".join(self.required_skills + self.interests)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "required_skills": self.required_skills,
            "interests": self.interests,
            "investment_level": self.investment_level,
            "investment_amount_range": self.investment_amount_range,
            "time_required_hours_per_week": self.time_required_hours_per_week,
            "difficulty": self.difficulty,
            "earning_range_monthly": self.earning_range_monthly,
            "time_to_first_income_weeks": self.time_to_first_income_weeks,
            "resources_needed": self.resources_needed,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            required_skills=data.get("required_skills", []),
            interests=data.get("interests", []),
            investment_level=data.get("investment_level", "None"),
            investment_amount_range=data.get("investment_amount_range", [0, 0]),
            time_required_hours_per_week=data.get("time_required_hours_per_week", [1, 10]),
            difficulty=data.get("difficulty", "Beginner"),
            earning_range_monthly=data.get("earning_range_monthly", [0, 0]),
            time_to_first_income_weeks=data.get("time_to_first_income_weeks", 4),
            resources_needed=data.get("resources_needed", []),
            description=data.get("description", ""),
        )


class RecommendationResult:
    """Wraps a SideHustle with its computed suitability breakdown for a user."""

    def __init__(self, hustle: SideHustle, suitability_score, skill_match_score,
                 time_fit_score, earning_fit_score, difficulty_fit_score,
                 investment_fit_score, skill_gap, estimated_earning_range):
        self.hustle = hustle
        self.suitability_score = suitability_score
        self.skill_match_score = skill_match_score
        self.time_fit_score = time_fit_score
        self.earning_fit_score = earning_fit_score
        self.difficulty_fit_score = difficulty_fit_score
        self.investment_fit_score = investment_fit_score
        self.skill_gap = skill_gap
        self.estimated_earning_range = estimated_earning_range

    def to_dict(self):
        return {
            "hustle": self.hustle.to_dict(),
            "suitability_score": round(self.suitability_score, 1),
            "breakdown": {
                "skill_match": round(self.skill_match_score, 2),
                "time_fit": round(self.time_fit_score, 2),
                "earning_fit": round(self.earning_fit_score, 2),
                "difficulty_fit": round(self.difficulty_fit_score, 2),
                "investment_fit": round(self.investment_fit_score, 2),
            },
            "skill_gap": self.skill_gap,
            "estimated_earning_range": self.estimated_earning_range,
        }
