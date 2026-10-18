from dotenv import load_dotenv

load_dotenv()
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")

    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is required. "
            "Set it before starting the application."
        )

    MONGO_URI = os.getenv(
        "MONGO_URI",
        "mongodb://127.0.0.1:27017/"
    )

    DB_NAME = os.getenv("DB_NAME", "food_waste_db")

    DEBUG = os.getenv("DEBUG", "False").lower() in (
        "true", "1", "yes"
    )
