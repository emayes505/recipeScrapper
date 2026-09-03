import json

import pytest

from backend.recipe_scraper import RecipeImportError, RecipeScraper


class HtmlRecipeScraper(RecipeScraper):
    def __init__(self, html: str) -> None:
        self.html = html

    def _fetch_html(self, url: str) -> tuple[str, str]:
        return self.html, url


def test_scrape_url_normalizes_schema_recipe() -> None:
    recipe = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": "Weeknight Pancakes",
        "recipeIngredient": ["1 1/2 cups flour", "3 large eggs"],
        "recipeInstructions": [
            {"@type": "HowToStep", "text": "Mix the batter."},
            {"@type": "HowToStep", "text": "Cook until golden."},
        ],
        "prepTime": "PT10M",
        "cookTime": "PT15M",
        "recipeYield": "Makes 4 servings",
    }
    html = f'<script type="application/ld+json">{json.dumps(recipe)}</script>'

    result = HtmlRecipeScraper(html).scrape_url("https://recipes.example/pancakes")

    assert result["title"] == "Weeknight Pancakes"
    assert result["prep_time_min"] == 10
    assert result["cook_time_min"] == 15
    assert result["servings"] == 4
    assert result["ingredients"][0] == {
        "name": "flour",
        "quantity": 1.5,
        "unit": "cups",
        "raw_text": "1 1/2 cups flour",
    }
    assert result["ingredients"][1]["name"] == "large eggs"
    assert result["ingredients"][1]["unit"] == "item"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1/admin"])
def test_fetch_rejects_non_public_urls(url: str) -> None:
    scraper = RecipeScraper(
        resolver=lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 80))]
    )

    with pytest.raises(RecipeImportError):
        scraper._fetch_html(url)


def test_extracts_external_recipe_source_from_pinterest_pin() -> None:
    html = """
    <meta property="pinterestapp:source"
          content="https://recipes.example/loaded-potato-taco-bowl/">
    """

    source_url = RecipeScraper._pinterest_source_url(
        "https://www.pinterest.com/pin/123456/",
        html,
    )

    assert source_url == "https://recipes.example/loaded-potato-taco-bowl/"


def test_extracts_measured_reserved_pasta_water_from_instructions() -> None:
    ingredient = RecipeScraper()._reserved_pasta_water_ingredient(
        "Cook pasta according to package directions. Reserve ½ cup pasta water and drain."
    )

    assert ingredient == {
        "name": "pasta water, reserved as needed",
        "quantity": 0.5,
        "unit": "cup",
        "raw_text": "½ cup pasta water, reserved as needed",
    }