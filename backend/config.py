import os


class Config:

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))


    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" +
        os.path.join(PROJECT_ROOT, "instance", "ecommerce.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Bargaining session + rate limit settings
    BARGAINING_SESSION_TIMEOUT_MINUTES = 15
    RATE_LIMIT_SESSIONS_PER_DAY = 3
    COOLING_OFF_MINUTES =0

    # Phase 2: Dynamic Bargaining Floor Settings
    # Maximum markup over cost price when pressure is LOW (e.g., 10% markup).
    # When pressure is HIGH, this markup approaches 0%, meaning floor = cost_price.
    BARGAINING_FLOOR_MAX_MARKUP_PCT = 0.10
