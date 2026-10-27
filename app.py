"""
app.py
Flask web application tying together the User/SideHustle models, the JSON
data manager, the scikit-learn recommendation engine, and report generation.
"""

import os
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash

from utils import (
    get_logger, validate_username, validate_email, validate_password,
    parse_comma_list, ValidationError, DataStoreError,
)
from models import User
from data_manager import SideHustleRepository, UserRepository
from recommender import RecommenderEngine
from report_generator import generate_chart, build_report_text, save_report_file

logger = get_logger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

hustle_repo = SideHustleRepository()
user_repo = UserRepository()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    try:
        return user_repo.get_by_id(user_id)
    except DataStoreError as exc:
        logger.error("Error loading current user: %s", exc)
        return None


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", hustle_count=len(hustle_repo.load_all()))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        try:
            validate_username(username)
            validate_email(email)
            validate_password(password)

            if user_repo.get_by_username(username):
                raise ValidationError("That username is already taken.")
            if user_repo.get_by_email(email):
                raise ValidationError("An account with that email already exists.")

            new_user = User(
                user_id=None,
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                full_name=full_name,
            )
            user_repo.create(new_user)
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))

        except (ValidationError, DataStoreError) as exc:
            flash(str(exc), "danger")
        except Exception:
            logger.exception("Unexpected error during registration")
            flash("Something went wrong while creating your account. Please try again.", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            user = user_repo.get_by_username(username)
            if not user or not check_password_hash(user.password_hash, password):
                raise ValidationError("Invalid username or password.")

            session["user_id"] = user.user_id
            flash(f"Welcome back, {user.username}!", "success")
            logger.info("User %s logged in", user.username)

            if not user.has_profile():
                return redirect(url_for("profile"))
            return redirect(url_for("recommendations"))

        except (ValidationError, DataStoreError) as exc:
            flash(str(exc), "danger")
        except Exception:
            logger.exception("Unexpected error during login")
            flash("Something went wrong while logging in. Please try again.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        try:
            skills = parse_comma_list(request.form.get("skills", ""))
            interests = parse_comma_list(request.form.get("interests", ""))
            experience_level = request.form.get("experience_level", "Beginner")
            available_time_hours = int(request.form.get("available_time_hours", 5) or 5)
            earning_goal_monthly = int(request.form.get("earning_goal_monthly", 5000) or 5000)
            investment_capacity = request.form.get("investment_capacity", "None")
            full_name = request.form.get("full_name", "").strip()

            if not skills:
                raise ValidationError("Please list at least one skill.")
            if available_time_hours <= 0:
                raise ValidationError("Available time must be greater than 0 hours/week.")

            user.update_profile(
                skills=skills,
                interests=interests,
                experience_level=experience_level,
                available_time_hours=available_time_hours,
                earning_goal_monthly=earning_goal_monthly,
                investment_capacity=investment_capacity,
                full_name=full_name,
            )
            user_repo.update(user)
            flash("Profile saved!", "success")
            return redirect(url_for("recommendations"))

        except (ValidationError, ValueError, DataStoreError) as exc:
            flash(str(exc), "danger")
        except Exception:
            logger.exception("Unexpected error saving profile")
            flash("Something went wrong while saving your profile.", "danger")

    return render_template("profile.html", user=user)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------
@app.route("/recommendations")
@login_required
def recommendations():
    user = current_user()
    if not user.has_profile():
        flash("Please complete your profile first so we can match you with side hustles.", "info")
        return redirect(url_for("profile"))

    engine = RecommenderEngine(hustle_repo.load_all())
    results = engine.recommend(user)
    saved_ids = {e["hustle_id"] for e in user.saved_hustles}
    return render_template("recommendations.html", user=user, results=results, saved_ids=saved_ids)


@app.route("/hustle/<hustle_id>")
@login_required
def hustle_detail(hustle_id):
    user = current_user()
    hustle = hustle_repo.get_by_id(hustle_id)
    if not hustle:
        flash("That side hustle could not be found.", "danger")
        return redirect(url_for("recommendations"))

    engine = RecommenderEngine(hustle_repo.load_all())
    result = engine.recommend_one(user, hustle_id)
    suggested_skills = engine.skills_to_learn(user, hustle)
    is_saved = any(e["hustle_id"] == hustle_id for e in user.saved_hustles)
    return render_template(
        "hustle_detail.html", user=user, hustle=hustle, result=result,
        suggested_skills=suggested_skills, is_saved=is_saved,
    )


# ---------------------------------------------------------------------------
# Saved / tracked hustles
# ---------------------------------------------------------------------------
@app.route("/save/<hustle_id>", methods=["POST"])
@login_required
def save_hustle(hustle_id):
    user = current_user()
    hustle = hustle_repo.get_by_id(hustle_id)
    if not hustle:
        flash("That side hustle could not be found.", "danger")
        return redirect(url_for("recommendations"))

    user.save_hustle(hustle_id, status="Interested")
    user_repo.update(user)
    flash(f"'{hustle.name}' saved to your tracked list.", "success")
    return redirect(request.referrer or url_for("recommendations"))


@app.route("/unsave/<hustle_id>", methods=["POST"])
@login_required
def unsave_hustle(hustle_id):
    user = current_user()
    user.remove_saved_hustle(hustle_id)
    user_repo.update(user)
    flash("Removed from your tracked list.", "info")
    return redirect(request.referrer or url_for("saved"))


@app.route("/saved")
@login_required
def saved():
    user = current_user()
    catalog = {h.id: h for h in hustle_repo.load_all()}
    entries = []
    for e in user.saved_hustles:
        hustle = catalog.get(e["hustle_id"])
        if hustle:
            entries.append({"hustle": hustle, "status": e["status"], "saved_at": e["saved_at"]})
    return render_template("saved.html", user=user, entries=entries)


@app.route("/saved/status/<hustle_id>", methods=["POST"])
@login_required
def update_status(hustle_id):
    user = current_user()
    status = request.form.get("status", "Interested")
    user.update_saved_status(hustle_id, status)
    user_repo.update(user)
    flash("Status updated.", "success")
    return redirect(url_for("saved"))


# ---------------------------------------------------------------------------
# Personalized report
# ---------------------------------------------------------------------------
@app.route("/report")
@login_required
def report():
    user = current_user()
    if not user.has_profile():
        flash("Please complete your profile first.", "info")
        return redirect(url_for("profile"))

    engine = RecommenderEngine(hustle_repo.load_all())
    results = engine.recommend(user)
    chart_rel_path = generate_chart(user, results, top_n=5)
    report_text = build_report_text(user, results, engine, top_n=5)
    _, report_rel_path = save_report_file(user, report_text)

    return render_template(
        "report.html", user=user, results=results[:5], chart_path=chart_rel_path,
        report_download=report_rel_path,
    )


@app.route("/static/reports/<path:filename>")
def download_report(filename):
    from report_generator import REPORTS_DIR
    return send_from_directory(REPORTS_DIR, filename, as_attachment=True)


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    logger.exception("Internal server error")
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
