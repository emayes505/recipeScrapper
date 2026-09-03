import logging
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api import share
from backend.db.database import Base, get_db
from backend.db.models import Ingredient, Rating, Recipe, RecipeImport, RecipeIngredient, User
from backend.main import app


client = TestClient(app)


def test_share_imports_url_embedded_in_android_text(monkeypatch, caplog) -> None:
    received: dict[str, object] = {}

    def fake_submit_recipe_import(user_id: int, url: str):
        received.update(user_id=user_id, url=url)
        return SimpleNamespace(id=42)

    monkeypatch.setattr(share, "submit_recipe_import", fake_submit_recipe_import)
    monkeypatch.setattr(share, "process_recipe_import", lambda import_id: None)
    caplog.set_level(logging.INFO, logger="uvicorn.error")

    response = client.post(
        "/api/share",
        data={"text": "Try this recipe https://recipes.example/pancakes"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/?share=queued&import_id=42"
    assert received == {"user_id": 1, "url": "https://recipes.example/pancakes"}
    assert "Received recipe URL: https://recipes.example/pancakes" in caplog.text


def test_share_rejects_request_without_url() -> None:
    response = client.post(
        "/api/share",
        data={"text": "This has no link"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/?share=missing"


def test_icon_fallbacks_redirect_to_the_app_icon() -> None:
    for icon_path in ("/apple-touch-icon.png", "/apple-touch-icon-precomposed.png", "/favicon.ico"):
        response = client.get(icon_path, follow_redirects=False)

        assert response.status_code == 307
        assert response.headers["location"] == "/icon.svg"


def test_recipe_list_returns_saved_recipes() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    with TestingSession() as db:
        db.add(User(id=1, username="test-user"))
        db.add(
            Recipe(
                user_id=1,
                title="Pancakes",
                source_url="https://recipes.example/pancakes",
                instructions="Mix and cook.",
                prep_time_min=10,
                cook_time_min=15,
                servings=4,
                created_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
            )
        )
        db.add(Rating(recipe_id=1, user_id=1, score=7))
        db.commit()

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/recipes")
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "title": "Pancakes",
            "source_url": "https://recipes.example/pancakes",
            "prep_time_min": 10,
            "cook_time_min": 15,
            "servings": 4,
            "created_at": "2026-08-18T00:00:00",
            "rating": 7,
        }
    ]


def test_recipe_list_orders_recipes_newest_first_when_dates_match() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    created_at = datetime(2026, 8, 18, tzinfo=timezone.utc)
    with TestingSession() as db:
        db.add(User(id=1, username="test-user"))
        db.add_all([
            Recipe(id=1, user_id=1, title="First", instructions="First.", created_at=created_at),
            Recipe(id=2, user_id=1, title="Second", instructions="Second.", created_at=created_at),
        ])
        db.commit()

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/recipes")
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)

    assert response.status_code == 200
    assert [recipe["id"] for recipe in response.json()] == [2, 1]


def test_recipe_detail_returns_ingredients_and_instructions() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    with TestingSession() as db:
        db.add(User(id=1, username="test-user"))
        recipe = Recipe(
            id=1,
            user_id=1,
            title="Pancakes",
            source_url="https://recipes.example/pancakes",
            instructions="Mix and cook.",
            prep_time_min=10,
            cook_time_min=15,
            servings=4,
            created_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
        )
        ingredient = Ingredient(id=1, name="flour")
        db.add_all([recipe, ingredient])
        db.flush()
        db.add(
            RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=1.5,
                unit="cups",
                raw_text="1 1/2 cups flour",
            )
        )
        db.commit()

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/recipes/1")
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)

    assert response.status_code == 200
    assert response.json()["instructions"] == "Mix and cook."
    assert response.json()["created_at"] == "2026-08-18T00:00:00"
    assert response.json()["ingredients"] == [
        {
            "quantity": 1.5,
            "unit": "cups",
            "raw_text": "1 1/2 cups flour",
            "name": "flour",
        }
    ]


def test_recipe_rating_notes_and_deletion() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    with TestingSession() as db:
        db.add(User(id=1, username="test-user"))
        db.add(Recipe(id=1, user_id=1, title="Pancakes", instructions="Mix and cook."))
        db.commit()

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        rating_response = client.put("/api/recipes/1/rating", json={"score": 8})
        note_response = client.post("/api/recipes/1/notes", json={"note_text": "Use buttermilk."})
        note_id = note_response.json()["id"]
        update_response = client.put(
            f"/api/recipes/1/notes/{note_id}",
            json={"note_text": "Use cultured buttermilk."},
        )
        detail_response = client.get("/api/recipes/1")
        delete_note_response = client.delete(f"/api/recipes/1/notes/{note_id}")
        delete_recipe_response = client.delete("/api/recipes/1")
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)

    assert rating_response.json() == {"score": 8}
    assert note_response.status_code == 201
    assert update_response.json()["note_text"] == "Use cultured buttermilk."
    assert detail_response.json()["rating"] == 8
    assert detail_response.json()["notes"][0]["note_text"] == "Use cultured buttermilk."
    assert delete_note_response.status_code == 204
    assert delete_recipe_response.status_code == 204


def test_import_status_returns_the_current_users_import() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    with TestingSession() as db:
        db.add(User(id=1, username="test-user"))
        db.add(
            RecipeImport(
                id=7,
                user_id=1,
                submitted_url="https://recipes.example/pancakes",
                status="invalid",
                error_message="The page does not contain a readable recipe.",
            )
        )
        db.commit()

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/imports/7")
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)

    assert response.status_code == 200
    assert response.json() == {
        "id": 7,
        "submitted_url": "https://recipes.example/pancakes",
        "status": "invalid",
        "error_message": "The page does not contain a readable recipe.",
        "recipe_id": None,
    }