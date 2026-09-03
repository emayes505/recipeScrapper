"""Persist and process recipe URL imports outside the share request."""

from datetime import datetime, timezone

from backend.add_recipe import DuplicateRecipeError, add_recipe_from_url
from backend.db.database import SessionLocal
from backend.db.models import RecipeImport
from backend.recipe_scraper import RecipeImportError


def submit_recipe_import(user_id: int, url: str) -> RecipeImport:
    """Create an import record and return its durable identifier."""
    with SessionLocal() as db:
        recipe_import = RecipeImport(
            user_id=user_id,
            submitted_url=url,
            status="queued",
        )
        db.add(recipe_import)
        db.commit()
        db.refresh(recipe_import)
        db.expunge(recipe_import)
        return recipe_import


def process_recipe_import(import_id: int) -> None:
    """Fetch, parse, and save a queued import without holding the HTTP response open."""
    with SessionLocal() as db:
        recipe_import = db.get(RecipeImport, import_id)
        if recipe_import is None or recipe_import.status != "queued":
            return

        recipe_import.status = "processing"
        db.commit()
        user_id = recipe_import.user_id
        submitted_url = recipe_import.submitted_url

    try:
        recipe = add_recipe_from_url(user_id=user_id, url=submitted_url)
    except DuplicateRecipeError as exc:
        _complete_import(import_id, "duplicate", str(exc), exc.recipe_id)
    except RecipeImportError as exc:
        _complete_import(import_id, "invalid", str(exc))
    except Exception:
        _complete_import(import_id, "failed", "The recipe could not be saved. Try again shortly.")
    else:
        _complete_import(import_id, "success", recipe_id=recipe.id)


def _complete_import(
    import_id: int,
    status: str,
    error_message: str | None = None,
    recipe_id: int | None = None,
) -> None:
    with SessionLocal() as db:
        recipe_import = db.get(RecipeImport, import_id)
        if recipe_import is None:
            return

        recipe_import.status = status
        recipe_import.error_message = error_message
        recipe_import.recipe_id = recipe_id
        recipe_import.completed_at = datetime.now(timezone.utc)
        db.commit()