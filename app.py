from fastapi import FastAPI
from live_chat.api.ticket_draft_api import router as ticket_router
from live_chat.api.livechat_suggestion_api import router as livechat_router
from live_chat.config import load_project_env


load_project_env()

app = FastAPI()
app.include_router(ticket_router)
app.include_router(livechat_router)
