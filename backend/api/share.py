"""Web Share Target endpoint."""

import logging
import os
import re

from fastapi import APIRouter, BackgroundTasks, Form
from fastapi.responses import RedirectResponse

from backend.recipe_imports import process_recipe_import, submit_recipe_import


logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api", tags=["sharing"])
URL_PATTERN = re.compile(r"https?://[^\s<>\"]+")


def extract_shared_url(url: str | None, text: str | None) -> str | None:
    if url and URL_PATTERN.fullmatch(url.strip()):
        return url.strip()
    if text:
        match = URL_PATTERN.search(text)
        if match:
            return match.group().rstrip(".,);]")
    return None


@router.post("/share")
def receive_shared_recipe(
    background_tasks: BackgroundTasks,
    title: str | None = Form(default=None),
    text: str | None = Form(default=None),
    url: str | None = Form(default=None),
) -> RedirectResponse:
    del title
    target_url = extract_shared_url(url, text)
    if target_url is None:
        return RedirectResponse(url="/?share=missing", status_code=303)

    user_id = int(os.getenv("COOKBOOK_DEFAULT_USER_ID", "1"))
    recipe_import = submit_recipe_import(user_id=user_id, url=target_url)
    logger.info("Received recipe URL: %s", target_url)
    background_tasks.add_task(process_recipe_import, recipe_import.id)
    return RedirectResponse(url=f"/?share=queued&import_id={recipe_import.id}", status_code=303)