"""
Setup script to create all database tables.
Run this ONCE to initialize your database on the Raspberry Pi.
"""
import os

from backend.db.database import Base, SessionLocal, engine
from backend.db.models import User, Recipe, RecipeImport, Ingredient, RecipeIngredient, Note, Rating, Substitution

def create_all_tables():
    """Create all tables defined in models.py"""
    print("Creating database tables...")
    print(f"Connecting to: {engine.url}")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)

    user_id = int(os.getenv("COOKBOOK_DEFAULT_USER_ID", "1"))
    username = os.getenv("COOKBOOK_DEFAULT_USERNAME", "admin")
    with SessionLocal() as db:
        if db.get(User, user_id) is None:
            db.add(User(id=user_id, username=username))
            db.commit()
    
    print("\n✅ SUCCESS! All tables created:")
    print("   - users")
    print("   - recipes")
    print("   - recipe_imports")
    print("   - ingredients")
    print("   - recipe_ingredients")
    print("   - notes")
    print("   - ratings")
    print("   - substitutions")
    print(f"   - default user: {username} (ID: {user_id})")
    print("\nYour database is ready to use!")

def drop_all_tables():
    """Drop all tables (CAUTION: deletes all data!)"""
    response = input("⚠️  WARNING: This will delete ALL data. Type 'DELETE' to confirm: ")
    if response == "DELETE":
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ All tables dropped.")
    else:
        print("❌ Cancelled.")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--drop":
        drop_all_tables()
    else:
        create_all_tables()
