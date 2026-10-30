import os


class Config:
    # Directory of this file (backend/), then one level up = project root
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

    # BUG 2 FIX: use the instance/ folder at the project root.
    # Flask creates instance/ automatically; backend/database/ did not exist.
    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" +
        os.path.join(PROJECT_ROOT, "instance", "ecommerce.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
