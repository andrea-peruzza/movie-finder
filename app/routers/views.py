import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
templates = Jinja2Templates(directory=templates_dir)

views_router = APIRouter()

@views_router.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
