from sqlalchemy import Column, Integer, String, Text, ForeignKey, Numeric, DateTime
from sqlalchemy.sql import func
from backend.db.database import Base
from sqlalchemy.orm import relationship


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    # nullable means if a username is not provided there will be an error
    username = Column(String(50), unique=True, nullable=False)
    #email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String(255), nullable=False)
    source_url = Column(Text)
    instructions = Column(Text, nullable=False)
    prep_time_min = Column(Integer)
    cook_time_min = Column(Integer)
    servings = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = relationship("Note", back_populates="recipe", cascade="all, delete-orphan")


class RecipeImport(Base):
    __tablename__ = "recipe_imports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    submitted_url = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    error_message = Column(Text)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

class Ingredient(Base):
    __tablename__ = "ingredients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))

class RecipeIngredient(Base):
    """Links recipes to ingredients with quantity and unit."""
    __tablename__ = "recipe_ingredients"
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"))
    quantity = Column(Numeric(10, 2), nullable=False)
    unit = Column(String(50), nullable=False)
    raw_text = Column(Text)
    
class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    note_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    recipe = relationship("Recipe", back_populates="notes")
    
class Rating(Base):
    __tablename__ = "ratings"
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    score = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Substitution(Base):
    __tablename__ = "substitutions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))
    original_ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="CASCADE"))
    new_ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"))
    new_quantity = Column(Numeric(10, 2), nullable=False)
    new_unit = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())