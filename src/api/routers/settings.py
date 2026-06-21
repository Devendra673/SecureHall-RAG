"""
Settings Router - Handles user preferences endpoints
Phase 5B - Endpoint for saving and retrieving user settings.
"""

import logging
import html

from fastapi import APIRouter, Depends

from ..models.schemas import (
    UserSettingsRequest,
    UserSettingsResponse,
)
from ..db.dependencies import get_current_user
from ..db.models import User

logger = logging.getLogger("securehall-rag.settings")
router = APIRouter()

# In-memory settings store keyed by user_id
_user_settings: dict[str, UserSettingsRequest] = {}


@router.post(
    "",
    response_model=UserSettingsResponse,
    summary="Save user preferences",
    description=(
        "Save user preferences such as theme, response length, "
        "citation display, confidence threshold, and font size."
    ),
)
async def save_settings(
    body: UserSettingsRequest,
    current_user: User = Depends(get_current_user),
):
    """Save user preference settings."""
    # Sanitize string fields against XSS
    if body.theme:
        body.theme = html.escape(body.theme)
    if body.font_size:
        body.font_size = html.escape(body.font_size)
    
    _user_settings[current_user.id] = body
    logger.info(f"Settings updated for {current_user.id}: theme={body.theme}, length={body.response_length}")
    return UserSettingsResponse(
        settings=body,
        message="Settings saved successfully.",
    )


@router.get(
    "",
    response_model=UserSettingsResponse,
    summary="Get user preferences",
    description="Retrieve current user preference settings.",
)
async def get_settings(current_user: User = Depends(get_current_user)):
    """Retrieve the current user settings."""
    settings = _user_settings.get(current_user.id, UserSettingsRequest())
    return UserSettingsResponse(
        settings=settings,
        message="Current settings retrieved.",
    )
