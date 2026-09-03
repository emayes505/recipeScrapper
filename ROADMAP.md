# Cookbook Implementation Roadmap

## ✅ Phase 1: Database Schema (DONE!)
- [x] Define models (User, Recipe, Ingredient, etc.)
- [x] Set up PostgreSQL connection
- [x] Test connection

## 📋 Phase 2: Initialize Database (DO NOW!)

### Step 1: Create the tables on your Raspberry Pi
```powershell
python setup_database.py
```

This creates all 7 tables in your PostgreSQL database.

### Step 2: Create your first user
```python
# Create a test user
from database import SessionLocal
from models import User

db = SessionLocal()
user = User(username="admin")
db.add(user)
db.commit()
db.refresh(user)
print(f"Created user: {user.username} (ID: {user.id})")
db.close()
```

## 🌐 Phase 3: Web Scraping Setup (NEXT!)

### Install web scraping libraries
```powershell
pip install recipe-scrapers beautifulsoup4 requests lxml
```

### Test the scraper
```powershell
python recipe_scraper.py
```

### Libraries to use:
- **recipe-scrapers**: Pre-built parsers for 200+ recipe websites!
  - Supports AllRecipes, Food Network, NYT Cooking, etc.
  - Handles structured data extraction automatically
  
- **BeautifulSoup**: For custom parsing if needed

- **requests**: Fetch web pages

## 🔨 Phase 4: Recipe Parsing (BUILD THIS!)

### A. Use recipe-scrapers (easiest!)

```python
from recipe_scrapers import scrape_me

# Scrape a recipe
scraper = scrape_me('https://www.allrecipes.com/recipe/123/')

# Extract data
recipe_data = {
    'title': scraper.title(),
    'instructions': scraper.instructions(),
    'prep_time_min': scraper.prep_time(),
    'cook_time_min': scraper.cook_time(),
    'servings': scraper.yields()
}

# Get ingredients
for ingredient in scraper.ingredients():
    print(ingredient)  # "2 cups flour", "1/2 tsp salt", etc.
```

### B. Ingredient Parsing Challenge

The hard part: "2 cups all-purpose flour" → `{'name': 'flour', 'qty': 2, 'unit': 'cups'}`

Options:
1. **ingredient-parser-nlp** (AI-powered)
2. **recipe-scrapers** (gives you raw text)
3. **Custom regex** (simple but limited)

## 📊 Phase 5: Integration (FINAL STEP!)

### Complete workflow:

```python
from add_recipe import add_recipe_from_url

# Scrape and add a recipe in one command
recipe = add_recipe_from_url(
    user_id=1,
    url='https://www.allrecipes.com/recipe/12345/chocolate-cake/'
)

print(f"Added: {recipe.title}")
```

## 🎯 Current Status

**You are here:** ⬅️ Phase 2

**Next steps:**
1. Run `python setup_database.py` to create tables
2. Create a user
3. Install web scraping libraries
4. Test recipe-scrapers with a real URL
5. Integrate into add_recipe.py

## 📦 Tools You'll Need

| Tool | Purpose | Install |
|------|---------|---------|
| recipe-scrapers | Extract recipe data from websites | `pip install recipe-scrapers` |
| ingredient-parser-nlp | Parse ingredient text | `pip install ingredient-parser-nlp` |
| BeautifulSoup | HTML parsing (backup) | `pip install beautifulsoup4` |

## 🔗 Helpful Resources

- recipe-scrapers docs: https://github.com/hhursev/recipe-scrapers
- ingredient-parser: https://github.com/strangetom/ingredient-parser
- SQLAlchemy tutorial: https://docs.sqlalchemy.org/en/20/tutorial/

## ⚠️ Common Pitfalls

1. **Ingredient normalization**: "flour" vs "Flour" vs "all-purpose flour"
   - Solution: Use get_or_create_ingredient() function
   
2. **Failed parsing**: Some sites block scrapers
   - Solution: Save partial data to failed_parses table
   
3. **Inconsistent units**: "tbsp" vs "tablespoon" vs "T"
   - Solution: Create unit conversion table later

## 🚀 Future Features

- [ ] Document/image upload with OCR
- [ ] AI-powered recipe extraction
- [ ] Shopping list generator
- [ ] Meal planning
- [ ] Recipe recommendations
