# templates_cfg.py
from datetime import date
from fastapi.templating import Jinja2Templates
from core.auth import dias_restantes # Importación absoluta limpia

# Usamos rutas relativas al archivo para evitar errores de directorio
import os
from pathlib import Path
_base_path = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(_base_path / "templates"))
templates.env.globals["dias_restantes"] = dias_restantes
templates.env.globals["now"] = lambda: date.today().strftime("%Y-%m-%d")
