"""
report_generator.py
Builds a personalized recommendation report for a user: a text/HTML summary
plus a bar chart (matplotlib) visualizing the top matches' suitability scores.
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # headless rendering for the Flask server
import matplotlib.pyplot as plt

from utils import get_logger
from models import User

logger = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(BASE_DIR, "static", "charts")
REPORTS_DIR = os.path.join(BASE_DIR, "static", "reports")
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_chart(user: User, results, top_n=5):
    """Render a horizontal bar chart of the top-N suitability scores."""
    top_results = results[:top_n]
    names = [r.hustle.name for r in top_results][::-1]
    scores = [r.suitability_score for r in top_results][::-1]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(names, scores, color="#2f6f4f")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Suitability Score (%)")
    ax.set_title(f"Top {len(top_results)} Side Hustle Matches for {user.username}")
    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                 f"{score:.1f}%", va="center", fontsize=9)
    fig.tight_layout()

    filename = f"chart_{user.user_id}.png"
    filepath = os.path.join(CHARTS_DIR, filename)
    fig.savefig(filepath, dpi=110)
    plt.close(fig)
    logger.info("Generated recommendation chart for user %s at %s", user.username, filepath)
    return f"charts/{filename}"


def build_report_text(user: User, results, engine, top_n=5):
    """Build a plain-text personalized report (also used for the download)."""
    top_results = results[:top_n]
    lines = []
    lines.append("=" * 70)
    lines.append("PERSONALIZED SIDE HUSTLE RECOMMENDATION REPORT")
    lines.append("=" * 70)
    lines.append(f"Generated for: {user.full_name or user.username} (@{user.username})")
    lines.append(f"Generated on : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("YOUR PROFILE")
    lines.append("-" * 70)
    lines.append(f"Skills            : {', '.join(user.skills) or 'Not specified'}")
    lines.append(f"Interests         : {', '.join(user.interests) or 'Not specified'}")
    lines.append(f"Experience level  : {user.experience_level}")
    lines.append(f"Available time    : {user.available_time_hours} hrs/week")
    lines.append(f"Earning goal      : Rs. {user.earning_goal_monthly:,}/month")
    lines.append(f"Investment budget : {user.investment_capacity}")
    lines.append("")
    lines.append(f"TOP {len(top_results)} RECOMMENDATIONS")
    lines.append("-" * 70)

    for rank, r in enumerate(top_results, start=1):
        h = r.hustle
        lo, hi = r.estimated_earning_range
        lines.append(f"\n{rank}. {h.name}  (Suitability: {r.suitability_score}%)")
        lines.append(f"   Category         : {h.category}")
        lines.append(f"   Difficulty       : {h.difficulty}")
        lines.append(f"   Time required    : {h.time_required_hours_per_week[0]}-{h.time_required_hours_per_week[1]} hrs/week")
        lines.append(f"   Investment level : {h.investment_level}")
        lines.append(f"   Estimated earning: Rs. {lo:,} - Rs. {hi:,} /month")
        lines.append(f"   Time to first income: ~{h.time_to_first_income_weeks} weeks")
        lines.append(f"   Required skills  : {', '.join(h.required_skills)}")
        lines.append(f"   Resources needed : {', '.join(h.resources_needed)}")
        if r.skill_gap:
            suggested = engine.skills_to_learn(user, h, limit=5)
            lines.append(f"   Skill gap        : {', '.join(r.skill_gap)}")
            lines.append(f"   Suggested to learn first: {', '.join(suggested)}")
        else:
            lines.append("   Skill gap        : None -- you already meet the core skill requirements!")

    lines.append("")
    lines.append("=" * 70)
    lines.append("Tip: Save the hustles you're most interested in from the app to")
    lines.append("track your progress toward getting started.")
    lines.append("=" * 70)
    return "\n".join(lines)


def save_report_file(user: User, report_text):
    filename = f"report_{user.user_id}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)
    logger.info("Saved report file for user %s at %s", user.username, filepath)
    return filepath, f"reports/{filename}"
