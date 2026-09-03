"""Recipe import status endpoints."""

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import RecipeImport


router = APIRouter(prefix="/api/imports", tags=["imports"])


class RecipeImportStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    submitted_url: str
    status: str
    error_message: str | None
    recipe_id: int | None


@router.get("/{import_id}", response_model=RecipeImportStatus)
def get_recipe_import(import_id: int, db: Session = Depends(get_db)) -> RecipeImport:
    user_id = int(os.getenv("COOKBOOK_DEFAULT_USER_ID", "1"))
    recipe_import = (
        db.query(RecipeImport)
        .filter(RecipeImport.id == import_id, RecipeImport.user_id == user_id)
        .first()
    )
    if recipe_import is None:
        raise HTTPException(status_code=404, detail="Recipe import not found.")
    return recipe_import