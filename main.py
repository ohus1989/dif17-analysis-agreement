from fastapi import FastAPI
from router import analysis, gptChat

app = FastAPI()
app.include_router(analysis.router)
app.include_router(gptChat.router)
