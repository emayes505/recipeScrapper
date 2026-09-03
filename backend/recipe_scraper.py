"""Fetch and normalize recipe data from public web pages."""

from collections.abc import Callable
from fractions import Fraction
import ipaddress
import re
import socket
from typing import NotRequired, TypedDict
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from recipe_scrapers import scrape_html
from recipe_scrapers._exceptions import FieldNotProvidedByWebsiteException


class IngredientData(TypedDict):
    name: str
    quantity: float
    unit: str
    raw_text: str
    category: NotRequired[str]


class RecipeData(TypedDict):
    title: str
    instructions: str
    ingredients: list[IngredientData]
    prep_time_min: int | None
    cook_time_min: int | None
    servings: int | None


class RecipeImportError(ValueError):
    """Raised when a URL cannot be safely converted into recipe data."""


Resolver = Callable[..., list[tuple]]


_UNITS = {
    "cup", "cups", "g", "gram", "grams", "kg", "kilogram", "kilograms",
    "ml", "milliliter", "milliliters", "l", "liter", "liters", "lb", "lbs",
    "pound", "pounds", "oz", "ounce", "ounces", "tsp", "teaspoon", "teaspoons",
    "tbsp", "tablespoon", "tablespoons", "pinch", "clove", "cloves", "can", "cans",
}

_UNICODE_FRACTIONS = {
    "¼": "1/4", "½": "1/2", "¾": "3/4", "⅓": "1/3", "⅔": "2/3",
    "⅛": "1/8", "⅜": "3/8", "⅝": "5/8", "⅞": "7/8",
}

_RESERVED_PASTA_WATER_PATTERN = re.compile(
    r"\breserve\s+("
    r"(?:\d+(?:\.\d+)?(?:\s+\d+/\d+)?|\d+/\d+|[¼½¾⅓⅔⅛⅜⅝⅞])"
    r"\s+(?:cup|cups|ml|milliliters?|l|liters?)\s+pasta water)\b",
    re.IGNORECASE,
)

class RecipeScraper:
    """Scrape supported sites and generic pages containing schema.org Recipe data."""

    def __init__(self, resolver: Resolver = socket.getaddrinfo) -> None:
        self._resolver = resolver

    def scrape_url(self, url: str) -> RecipeData:
        html, final_url = self._fetch_html(url)

        try:
            scraper = scrape_html(html, final_url, supported_only=False)
            title = scraper.title().strip()
            instructions = scraper.instructions().strip()
            raw_ingredients = scraper.ingredients()
        except Exception as exc:
            raise RecipeImportError("The page does not contain a readable recipe.") from exc

        if not title or not instructions or not raw_ingredients:
            raise RecipeImportError("The recipe is missing a title, instructions, or ingredients.")

        ingredients = [self.parse_ingredient_text(item) for item in raw_ingredients]
        reserved_pasta_water = self._reserved_pasta_water_ingredient(instructions)
        if reserved_pasta_water and not any(
            ingredient["name"].casefold().startswith("pasta water")
            for ingredient in ingredients
        ):
            ingredients.append(reserved_pasta_water)

        return {
            "title": title,
            "instructions": instructions,
            "ingredients": ingredients,
            "prep_time_min": self._optional_number(scraper.prep_time),
            "cook_time_min": self._optional_number(scraper.cook_time),
            "servings": self._parse_servings(self._optional_text(scraper.yields)),
        }

    def _fetch_html(self, url: str) -> tuple[str, str]:
        current_url = url.strip()

        for _ in range(6):
            self._validate_public_url(current_url)
            response = requests.get(
                current_url,
                allow_redirects=False,
                headers={"User-Agent": "PiCookbook/1.0 (+personal recipe importer)"},
                timeout=(5, 15),
            )

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise RecipeImportError("The recipe site returned an invalid redirect.")
                current_url = urljoin(current_url, location)
                continue

            response.raise_for_status()
            if len(response.content) > 5_000_000:
                raise RecipeImportError("The recipe page is larger than 5 MB.")

            pinterest_source_url = self._pinterest_source_url(current_url, response.text)
            if pinterest_source_url:
                current_url = pinterest_source_url
                continue

            return response.text, current_url

        raise RecipeImportError("The recipe site redirected too many times.")

    @staticmethod
    def _pinterest_source_url(url: str, html: str) -> str | None:
        """Return a pin's public source page without automating Pinterest's UI."""
        hostname = urlparse(url).hostname or ""
        if hostname != "pinterest.com" and not hostname.endswith(".pinterest.com"):
            return None

        soup = BeautifulSoup(html, "html.parser")
        for property_name in ("pinterestapp:source", "og:see_also"):
            tag = soup.find("meta", attrs={"property": property_name})
            source_url = tag.get("content") if tag else None
            if source_url:
                return source_url.strip()
        return None

    def _validate_public_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise RecipeImportError("Recipe URLs must use http or https.")
        if parsed.username or parsed.password:
            raise RecipeImportError("Recipe URLs cannot contain credentials.")

        try:
            addresses = {
                ipaddress.ip_address(result[4][0])
                for result in self._resolver(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
            }
        except (OSError, ValueError) as exc:
            raise RecipeImportError("The recipe site could not be resolved.") from exc

        if not addresses or any(not address.is_global for address in addresses):
            raise RecipeImportError("Recipe URLs must resolve to a public internet address.")

    def _reserved_pasta_water_ingredient(self, instructions: str) -> IngredientData | None:
        match = _RESERVED_PASTA_WATER_PATTERN.search(instructions)
        if not match:
            return None
        return self.parse_ingredient_text(f"{match.group(1)}, reserved as needed")

    def parse_ingredient_text(self, ingredient_text: str) -> IngredientData:
        raw_text = ingredient_text.strip()
        normalized = raw_text
        for symbol, fraction in _UNICODE_FRACTIONS.items():
            normalized = normalized.replace(symbol, f" {fraction}")
        normalized = " ".join(normalized.split())

        match = re.match(r"^(\d+(?:\.\d+)?(?:\s+\d+/\d+)?|\d+/\d+)\s+(.+)$", normalized)
        if not match:
            return {"name": raw_text, "quantity": 1.0, "unit": "item", "raw_text": raw_text}

        quantity_text, remainder = match.groups()
        quantity = sum(float(Fraction(part)) for part in quantity_text.split())
        first_word, separator, rest = remainder.partition(" ")

        if separator and first_word.lower().rstrip(".") in _UNITS:
            unit = first_word.rstrip(".")
            name = rest
        else:
            unit = "item"
            name = remainder

        return {"name": name.strip(), "quantity": quantity, "unit": unit, "raw_text": raw_text}

    @staticmethod
    def _optional_number(getter: Callable[[], int]) -> int | None:
        try:
            return getter()
        except FieldNotProvidedByWebsiteException:
            return None

    @staticmethod
    def _optional_text(getter: Callable[[], str]) -> str | None:
        try:
            return getter()
        except FieldNotProvidedByWebsiteException:
            return None

    @staticmethod
    def _parse_servings(value: str | None) -> int | None:
        if not value:
            return None
        match = re.search(r"\d+", value)
        return int(match.group()) if match else None
