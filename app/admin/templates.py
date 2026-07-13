from pathlib import Path

from fastapi.templating import Jinja2Templates


ADMIN_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(
    directory=ADMIN_DIR / "templates",
)