from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from bot.config import BOT_USERNAME
from bot.infrastructure.localization import load_translation_file

router = APIRouter()


@router.get("/api/meta")
async def public_meta():
    """Публічні посилання на бота (лендінг, онбординг у Web App)."""
    return {
        "bot_username": BOT_USERNAME,
        "bot_url": f"https://t.me/{BOT_USERNAME}",
        "add_bot_to_group_url": f"https://t.me/{BOT_USERNAME}?startgroup",
    }


@router.get("/api/translations/{lang_code}")
async def get_translations(lang_code: str):
    """Віддає файл перекладу у форматі JSON."""
    try:
        return JSONResponse(content=load_translation_file(lang_code))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load translations: {e}") from e
