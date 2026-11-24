import os


class Config:

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))


    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" +
        os.path.join(PROJECT_ROOT, "instance", "ecommerce.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
