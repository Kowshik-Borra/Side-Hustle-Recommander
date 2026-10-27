# Smart Side Hustle Recommendation System

A Flask web application that recommends personalized side hustle opportunities
based on a user's skills, interests, available time, experience, and earning
goals — using a scikit-learn content-based matching engine plus rule-based
fit scoring.

## Features implemented

- User registration & login (Werkzeug password hashing, session-based auth)
- Profile collection: skills, interests, experience level, available time,
  earning goal, investment capacity
- JSON-file catalog of 28 side hustle opportunities, categorized by skills,
  investment level, time commitment, and difficulty
- Matching engine (`recommender.py`):
  - TF-IDF + cosine similarity (scikit-learn) for skill/interest matching
  - Rule-based fit scores for time, earnings, difficulty, and investment
  - Weighted suitability score (0-100%) combining all factors
- Estimated monthly earning ranges per opportunity
- Skill gap analysis (required skills vs. the user's stated skills)
- "Skills to learn first" suggestions, ranked by rarity/impact across the catalog
- Save/track side hustles with a status (Interested → Learning Skills →
  In Progress → Started Earning)
- Personalized report generation: text report + matplotlib bar chart of top matches,
  downloadable from the app
- Logging (`logs/app.log`) and custom exception handling throughout
- Input validation via regex (username, email, password strength, comma-separated
  skill/interest parsing)

## Project structure

```
side_hustle_recommender/
├── app.py                # Flask routes
├── models.py             # OOP models: User, SideHustle, RecommendationResult
├── data_manager.py        # JSON file I/O (users.json, side_hustles.json)
├── recommender.py         # Matching engine (scikit-learn + rule-based scoring)
├── report_generator.py    # Report text + matplotlib chart generation
├── utils.py               # Logging, regex validators, custom exceptions
├── requirements.txt
├── data/
│   └── side_hustles.json  # Seed catalog of 28 side hustles
├── static/
│   ├── css/style.css
│   ├── charts/             # Generated chart images (created at runtime)
│   └── reports/            # Generated report .txt files (created at runtime)
├── templates/              # Jinja2 HTML templates
└── logs/app.log            # Application log (created at runtime)
```

`data/users.json` is created automatically the first time someone registers.

## Setup

```bash
cd side_hustle_recommender
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## How the matching score works

For each side hustle, the suitability score is a weighted blend of:

| Factor          | Weight | How it's computed                                              |
|------------------|:------:|------------------------------------------------------------------|
| Skill match      | 40%    | TF-IDF vectorization of user skills+interests vs. hustle requirements, scored with cosine similarity |
| Earning fit      | 20%    | How well the hustle's earning ceiling can meet the user's monthly goal |
| Time fit         | 15%    | Whether the user's available hours/week fall in the hustle's required range |
| Difficulty fit   | 15%    | User's experience level vs. the hustle's difficulty level      |
| Investment fit   | 10%    | User's stated investment capacity vs. the hustle's investment level |

The final score is scaled to 0-100%. Skill gaps are computed as a set
difference between the hustle's required skills and the user's stated
skills (case-insensitive), and "skills to learn first" ranks the gap by
how rare/distinguishing each skill is across the whole catalog.

## Extending the project (ideas for the optional advanced features)

- **Income prediction**: train a regression model (scikit-learn) on
  historical earner data per hustle to predict a personalized earning
  estimate instead of using a fixed range.
- **Trending detection**: track save/interest counts per hustle over time
  and surface a "trending this month" section.
- **Location-based recommendations**: add a `location` field to hustles
  (e.g. local-service categories) and filter/boost by user city.
- **Chatbot**: wrap the recommender in a simple rule-based or LLM-backed
  Q&A layer for conversational discovery.
- **Real freelance/gig integration**: replace/augment the static JSON
  catalog with live API pulls from freelance marketplaces.

## Notes

- Passwords are hashed with Werkzeug's `generate_password_hash` — never
  stored in plain text.
- All file writes (users.json) use an atomic write-then-replace pattern to
  avoid data corruption.
- Change `app.secret_key` (via the `SECRET_KEY` environment variable) before
  any real deployment.
