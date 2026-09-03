"""Add normalized recipes to the database."""

import re

from sqlalchemy.orm import Session

from backend.db.database import SessionLocal
from backend.db.models import Ingredient, Recipe, RecipeIngredient
from backend.recipe_scraper import IngredientData, RecipeData, RecipeScraper


class DuplicateRecipeError(ValueError):
    """Raised when a user already has the same recipe content saved."""

    def __init__(self, recipe: Recipe) -> None:
        self.recipe_id = recipe.id
        super().__init__(f"'{recipe.title}' is already in your cookbook.")


def _normalize_recipe_text(value: str) -> str:
    return " ".join(re.sub(r"\s+", " ", value).casefold().split())


def find_duplicate_recipe(db: Session, user_id: int, recipe_data: RecipeData) -> Recipe | None:
    """Find a saved recipe with identical normalized title and instructions."""
    title = _normalize_recipe_text(recipe_data["title"])
    instructions = _normalize_recipe_text(recipe_data["instructions"])
    candidates = db.query(Recipe).filter(Recipe.user_id == user_id).all()
    return next(
        (
            recipe
            for recipe in candidates
            if _normalize_recipe_text(recipe.title) == title
            and _normalize_recipe_text(recipe.instructions) == instructions
        ),
        None,
    )

def get_or_create_ingredient(db: Session, name: str, category: str | None = None) -> Ingredient:
    """
    Get an existing ingredient or create a new one.
    Prevents duplicates.
    """
    # Check if ingredient exists (case-insensitive)
    ingredient = db.query(Ingredient).filter(
        Ingredient.name.ilike(name)
    ).first()
    
    if ingredient:
        return ingredient
    
    # Create new ingredient
    ingredient = Ingredient(name=name, category=category)
    db.add(ingredient)
    db.flush()
    return ingredient

def add_recipe_from_data(
    user_id: int,
    recipe_data: RecipeData,
    ingredients_data: list[IngredientData],
    source_url: str | None = None,
) -> Recipe:
    """
    Add a recipe to the database.
    
    Args:
        user_id: ID of user adding the recipe
        recipe_data: {'title': str, 'instructions': str, 'prep_time_min': int, ...}
        ingredients_data: [{'name': str, 'quantity': float, 'unit': str}, ...]
    
    Returns:
        Created Recipe object
    """
    db = SessionLocal()
    
    try:
        duplicate_recipe = find_duplicate_recipe(db, user_id, recipe_data)
        if duplicate_recipe is not None:
            raise DuplicateRecipeError(duplicate_recipe)

        # 1. Create the recipe
        recipe = Recipe(
            user_id=user_id,
            title=recipe_data['title'],
            source_url=source_url,
            instructions=recipe_data['instructions'],
            prep_time_min=recipe_data.get('prep_time_min'),
            cook_time_min=recipe_data.get('cook_time_min'),
            servings=recipe_data.get('servings')
        )
        db.add(recipe)
        db.flush()
        
        # 2. Add ingredients
        for ing_data in ingredients_data:
            # Get or create ingredient
            ingredient = get_or_create_ingredient(
                db, 
                name=ing_data['name'],
                category=ing_data.get('category')
            )
            
            # Link to recipe
            recipe_ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                ingredient_id=ingredient.id,
                quantity=ing_data['quantity'],
                unit=ing_data['unit'],
                raw_text=ing_data['raw_text'],
            )
            db.add(recipe_ingredient)
        
        db.commit()
        db.refresh(recipe)
        return recipe
        
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def add_recipe_from_url(user_id: int, url: str) -> Recipe:
    """
    Scrape a recipe from a URL and add to database.
    """
    scraper = RecipeScraper()
    
    data = scraper.scrape_url(url)
    return add_recipe_from_data(user_id, data, data['ingredients'], source_url=url)
