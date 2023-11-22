import os
import gradio as gr
from fastapi import FastAPI
from src.gradio_ui import ui
from app.endpoints import ols, base_llm_completion, feedback

app = FastAPI()

gr.mount_gradio_app(app, ui, path="/ui")
app.include_router(ols.router)
app.include_router(base_llm_completion.router)
app.include_router(feedback.router)
