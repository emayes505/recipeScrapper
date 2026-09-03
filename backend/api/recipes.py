"""Read-only recipe endpoints."""

import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Ingredient, Note, Rating, Recipe, RecipeImport, RecipeIngredient


router = APIRouter(prefix="/api/recipes", tags=["recipes"])


class RecipeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_url: str | None
    prep_time_min: int | None
    cook_time_min: int | None
    servings: int | None
    created_at: datetime | None
    rating: int | None


class RecipeIngredientDetail(BaseModel):
    quantity: float
    unit: str
    raw_text: str | None
    name: str


class RecipeNote(BaseModel):
    id: int
    note_text: str
    created_at: datetime | None


class NotePayload(BaseModel):
    note_text: str = Field(min_length=1, max_length=5_000)


class RatingPayload(BaseModel):
    score: int = Field(ge=1, le=10)


class RecipeDetail(RecipeSummary):
    instructions: str
    ingredients: list[RecipeIngredientDetail]
    rating: int | None
    notes: list[RecipeNote]


def _get_owned_recipe(db: Session, recipe_id: int, user_id: int) -> Recipe:
    recipe = (
        db.query(Recipe)
        .filter(Recipe.id == recipe_id, Recipe.user_id == user_id)
        .first()
    )
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found.")
    return recipe


@router.get("", response_model=list[RecipeSummary])
def list_recipes(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    user_id = int(os.getenv("COOKBOOK_DEFAULT_USER_ID", "1"))
    recipes = (
        db.query(Recipe)
        .filter(Recipe.user_id == user_id)
        .order_by(Recipe.created_at.desc(), Recipe.id.desc())
        .all()
    )
    recipe_ids = [recipe.id for recipe in recipes]
    ratings = (
        db.query(Rating)
        .filter(Rating.user_id == user_id, Rating.recipe_id.in_(recipe_ids))
        .order_by(Rating.id.desc())
        .all()
        if recipe_ids
        else []
    )
    ratings_by_recipe = {}
    for rating in ratings:
        ratings_by_recipe.setdefault(rating.recipe_id, rating.score)

    return [
        {
            "id": recipe.id,
            "title": recipe.title,
            "source_url": recipe.source_url,
            "prep_time_min": recipe.prep_time_min,
            "cook_time_min": recipe.cook_time_min,
            "servings": recipe.servings,
            "created_at": recipe.created_at,
            "rating": ratings_by_recipe.get(recipe.id),
        }
        for recipe in recipes
    ]


@router.get("/{recipe_id}", response_model=RecipeDetail)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    user_id = int(os.getenv("COOKBOOK_DEFAULT_USER_ID", "1"))
    recipe = _get_owned_recipe(db, recipe_id, user_id)

    ingredient_rows = (
        db.query(RecipeIngredient, Ingredient)
        .join(Ingredient, RecipeIngredient.ingredient_id == Ingredient.id)
        .filter(RecipeIngredient.recipe_id == recipe.id)
        .order_by(RecipeIngredient.id)
        .all()
    )
    notes = (
        db.query(Note)
        .filter(Note.recipe_id == recipe.id, Note.user_id == user_id)
        .order_by(Note.created_at.desc(), Note.id.desc())
        .all()
    )
    rating = (
        db.query(Rating)
        .filter(Rating.recipe_id == recipe.id, Rating.user_id == user_id)
        .order_by(Rating.id.desc())
        .first()
    )
    return {
        "id": recipe.id,
        "title": recipe.title,
        "source_url": recipe.source_url,
        "instructions": recipe.instructions,
        "prep_time_min": recipe.prep_time_min,
        "cook_time_min": recipe.cook_time_min,
        "servings": recipe.servings,
        "created_at": recipe.created_at,
        "rating": rating.score if rating else None,
        "notes": [
            {"id": note.id, "note_text": note.note_text, "created_at": note.created_at}
            for note in notes
        ],
        "ingredients": [
            {
                "quantity": float(recipe_ingredient.quantity),
                "unit": recipe_ingredient.unit,
                "raw_text": recipe_ingredient.raw_text,
                "name": ingredient.name,
            }
            for recipe_ingredient, ingredient in ingredient_rows
        ],
    }


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)) -> Response:
    user_id = int(os.getenv("COOKBOOK_DEFAULT_USER_ID", "1"))
    recipe = _get_owned_recipe(db, recipe_id, user_id)
    db.query(RecipeImport).filter(RecipeImport.recipe_id == recipe.id).update({"recipe_id": None})
    db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe.id).delete()
    db.query(Note).filter(Note.recipe_id == recipe.id).delete()
    db.query(Rating).filter(Rating.recipe_id == recipe.id).delete()
    db.delete(recipe)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{recipe_id}/rating", response_model=RatingPayload)
def save_rating(recipe_id: int, payload: RatingPayload, db: Session = Depends(get_db)) -> RatingPayload:
    user_id = int(os.getenv("COOKBOOK_DEFAULT_USER_ID", "1"))
    _get_owned_recipe(db, recipe_id, user_id)
    rating = (
        db.query(Rating)
        .filter(Rating.recipe_id == recipe_id, Rating.user_id == user_id)
        .order_by(Rating.id.desc())
        .first()
    )
    if rating is None:
        rating = Rating(recipe_id=recipe_id, user_id=user_id, score=payload.score)
        db.add(rating)
    else:
        rating.score = payload.score
    db.commit()
    return RatingPayload(score=payload.score)


@router.post("/{recipe_id}/notes", response_model=RecipeNote, status_code=status.HTTP_201_CREATED)
def create_note(recipe_id: int, payload: NotePayload, db: Session = Depends(get_db)) -> Note:
    user_id = int(os.getenv("COOKBOOK_DEFAULT_USER_ID", "1"))
    _get_owned_recipe(db, recipe_id, user_id)
    note = Note(recipe_id=recipe_id, user_id=user_id, note_text=payload.note_text.strip())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.put("/{recipe_id}/notes/{note_id}", response_model=RecipeNote)
def update_note(
    recipe_id: int,
    note_id: int,
    payload: NotePayload,
    db: Session = Depends(get_db),
) -> Note:
    user_id = int(os.getenv("COOKBOOK_DEFAULT_USER_ID", "1"))
    _get_owned_recipe(db, recipe_id, user_id)
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.recipe_id == recipe_id, Note.user_id == user_id)
        .first()
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    note.note_text = payload.note_text.strip()
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{recipe_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(recipe_id: int, note_id: int, db: Session = Depends(get_db)) -> Response:
    user_id = int(os.getenv("COOKBOOK_DEFAULT_USER_ID", "1"))
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.recipe_id == recipe_id, Note.user_id == user_id)
        .first()
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found.")
    db.delete(note)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)