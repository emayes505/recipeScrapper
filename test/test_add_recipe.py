from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend import add_recipe
from backend.add_recipe import DuplicateRecipeError, add_recipe_from_data
from backend.db.database import Base
from backend.db.models import Recipe, User


def test_does_not_add_recipe_with_matching_title_and_instructions(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(add_recipe, "SessionLocal", TestingSession)

    recipe_data = {
        "title": "Weeknight Pancakes",
        "instructions": "Mix the batter.\nCook until golden.",
        "ingredients": [],
        "prep_time_min": 10,
        "cook_time_min": 15,
        "servings": 4,
    }

    with TestingSession() as db:
        db.add(User(id=1, username="test-user"))
        db.add(
            Recipe(
                user_id=1,
                title="  weeknight pancakes  ",
                instructions="Mix the batter.  Cook until golden.",
            )
        )
        db.commit()

    try:
        add_recipe_from_data(1, recipe_data, [])
    except DuplicateRecipeError as exc:
        assert exc.recipe_id == 1
    else:
        raise AssertionError("Expected the matching recipe to be rejected as a duplicate.")

    with TestingSession() as db:
        assert db.query(Recipe).count() == 1

    Base.metadata.drop_all(engine)