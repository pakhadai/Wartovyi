import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from bot.infrastructure.database import get_group_current_stats, get_group_stats
from bot.web_backend.deps import ensure_group_admin, get_authenticated_user_id

router = APIRouter()


@router.get("/api/stats/{chat_id}")
async def get_chat_statistics(
    chat_id: int,
    days: int = 30,
    user_id: int = Depends(get_authenticated_user_id),
):
    """Отримує статистику для конкретної групи."""
    ensure_group_admin(user_id, chat_id)
    historical_stats = get_group_stats(chat_id, days)
    current_stats = get_group_current_stats(chat_id)
    return {
        "historical": historical_stats,
        "current": current_stats,
    }


@router.get("/api/stats/{chat_id}/export")
async def export_chat_statistics(
    chat_id: int,
    format: str = "json",
    user_id: int = Depends(get_authenticated_user_id),
):
    """Експортує статистику групи в різних форматах."""
    ensure_group_admin(user_id, chat_id)
    stats = get_group_stats(chat_id, 90)

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Messages", "Deleted", "Users Joined", "Users Left"])
        for day in stats["daily"]:
            writer.writerow(
                [
                    day["date"],
                    day["messages_total"],
                    day["messages_deleted"],
                    day["users_joined"],
                    day["users_left"],
                ]
            )
        return JSONResponse(
            content={"csv": output.getvalue()},
            headers={"Content-Type": "text/csv"},
        )

    return stats
