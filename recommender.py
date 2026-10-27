"""
recommender.py
The recommendation engine. Combines a scikit-learn content-based skill/interest
match (TF-IDF + cosine similarity) with rule-based fit scores for time,
earnings, difficulty and investment to produce a weighted suitability score
for every side hustle in the catalog, for a given user.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils import get_logger
from models import User, SideHustle, RecommendationResult

logger = get_logger(__name__)

# Weights for the final weighted suitability score (must sum to 1.0)
WEIGHTS = {
    "skill_match": 0.40,
    "earning_fit": 0.20,
    "time_fit": 0.15,
    "difficulty_fit": 0.15,
    "investment_fit": 0.10,
}

EXPERIENCE_RANK = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
DIFFICULTY_RANK = {"Beginner": 0, "Medium": 1, "Advanced": 2}
INVESTMENT_RANK = {"None": 0, "Low": 1, "Medium": 2, "High": 3}


class RecommenderEngine:
    """Stateless engine: pass in a user and the catalog, get back ranked results."""

    def __init__(self, hustles):
        self.hustles = hustles

    # ------------------------------------------------------------------
    # Skill + interest match via TF-IDF / cosine similarity
    # ------------------------------------------------------------------
    def _skill_match_scores(self, user: User):
        user_text = " ".join(user.skills + user.interests)
        corpus = [user_text] + [h.combined_text() for h in self.hustles]

        if not user_text.strip():
            return {h.id: 0.0 for h in self.hustles}

        vectorizer = TfidfVectorizer(lowercase=True, token_pattern=r"[A-Za-z0-9\+\#\.]+")
        try:
            tfidf_matrix = vectorizer.fit_transform(corpus)
        except ValueError:
            # Empty vocabulary (e.g. only stopword-like tokens)
            return {h.id: 0.0 for h in self.hustles}

        user_vec = tfidf_matrix[0:1]
        hustle_vecs = tfidf_matrix[1:]
        sims = cosine_similarity(user_vec, hustle_vecs).flatten()
        return {h.id: float(sims[i]) for i, h in enumerate(self.hustles)}

    # ------------------------------------------------------------------
    # Rule-based fit sub-scores (each normalized to 0.0 - 1.0)
    # ------------------------------------------------------------------
    @staticmethod
    def _time_fit_score(user: User, hustle: SideHustle):
        lo, hi = hustle.time_required_hours_per_week
        available = user.available_time_hours
        if lo <= available <= hi:
            return 1.0
        if available < lo:
            # Partial credit shrinking the further short the user falls
            deficit = lo - available
            return max(0.0, 1.0 - deficit / max(lo, 1))
        # user has more time than the max required -- still a full fit
        return 1.0

    @staticmethod
    def _earning_fit_score(user: User, hustle: SideHustle):
        goal = user.earning_goal_monthly
        lo, hi = hustle.earning_range_monthly
        hi = max(hi, 0)
        if goal <= 0:
            return 1.0
        if hi >= goal:
            # can potentially meet or exceed the goal
            return 1.0
        # falls short -- score by how close the ceiling gets to the goal
        return max(0.0, hi / goal)

    @staticmethod
    def _difficulty_fit_score(user: User, hustle: SideHustle):
        user_rank = EXPERIENCE_RANK.get(user.experience_level, 0)
        hustle_rank = DIFFICULTY_RANK.get(hustle.difficulty, 1)
        diff = user_rank - hustle_rank
        if diff >= 0:
            return 1.0  # user is at or above the required experience level
        if diff == -1:
            return 0.5  # one level under-qualified, still workable with effort
        return 0.15  # two levels under-qualified

    @staticmethod
    def _investment_fit_score(user: User, hustle: SideHustle):
        user_rank = INVESTMENT_RANK.get(user.investment_capacity, 0)
        hustle_rank = INVESTMENT_RANK.get(hustle.investment_level, 0)
        if user_rank >= hustle_rank:
            return 1.0
        gap = hustle_rank - user_rank
        return max(0.0, 1.0 - gap / 3.0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def recommend(self, user: User, top_n=None):
        skill_scores = self._skill_match_scores(user)
        results = []

        for hustle in self.hustles:
            skill_match = skill_scores.get(hustle.id, 0.0)
            time_fit = self._time_fit_score(user, hustle)
            earning_fit = self._earning_fit_score(user, hustle)
            difficulty_fit = self._difficulty_fit_score(user, hustle)
            investment_fit = self._investment_fit_score(user, hustle)

            weighted = (
                WEIGHTS["skill_match"] * skill_match
                + WEIGHTS["earning_fit"] * earning_fit
                + WEIGHTS["time_fit"] * time_fit
                + WEIGHTS["difficulty_fit"] * difficulty_fit
                + WEIGHTS["investment_fit"] * investment_fit
            )
            suitability_score = round(float(np.clip(weighted, 0, 1)) * 100, 1)

            gap = hustle.skill_gap(user)

            result = RecommendationResult(
                hustle=hustle,
                suitability_score=suitability_score,
                skill_match_score=skill_match,
                time_fit_score=time_fit,
                earning_fit_score=earning_fit,
                difficulty_fit_score=difficulty_fit,
                investment_fit_score=investment_fit,
                skill_gap=gap,
                estimated_earning_range=hustle.earning_range_monthly,
            )
            results.append(result)

        results.sort(key=lambda r: r.suitability_score, reverse=True)
        logger.info("Generated %d recommendations for user %s", len(results), user.username)
        return results[:top_n] if top_n else results

    def recommend_one(self, user: User, hustle_id):
        """Compute the recommendation breakdown for a single specific hustle."""
        hustle = next((h for h in self.hustles if h.id == hustle_id), None)
        if not hustle:
            return None
        single_engine = RecommenderEngine([hustle])
        return single_engine.recommend(user)[0]

    def skills_to_learn(self, user: User, hustle: SideHustle, limit=5):
        """
        Suggest the most impactful skills to learn: the skill gap for this
        hustle, ordered by how rare/specific they are across the catalog
        (rarer skills are more distinguishing / worth prioritizing).
        """
        gap = hustle.skill_gap(user)
        if not gap:
            return []

        from utils import normalize_skill
        skill_doc_count = {}
        for h in self.hustles:
            for s in set(normalize_skill(x) for x in h.required_skills):
                skill_doc_count[s] = skill_doc_count.get(s, 0) + 1

        def rarity(skill):
            return skill_doc_count.get(normalize_skill(skill), len(self.hustles))

        ranked = sorted(gap, key=rarity)
        return ranked[:limit]
