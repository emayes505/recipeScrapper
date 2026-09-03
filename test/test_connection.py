from backend.db.database import engine
from sqlalchemy import text

def test_db_connection():
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1