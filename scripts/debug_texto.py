"""Volcado del texto que sale del PDF sintetico, para ver por que no matchea."""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from comparar_parser import _pdf_de_ejemplo  # noqa: E402

from core.comandas.parser import texto_del_pdf  # noqa: E402

raw = texto_del_pdf(_pdf_de_ejemplo())
print(repr(raw[:900]))
print("\n--- sin normalizar de saltos, crudo de pypdf ---")
from pypdf import PdfReader  # noqa: E402

lector = PdfReader(io.BytesIO(_pdf_de_ejemplo()))
crudo = "".join(p.extract_text() or "" for p in lector.pages)
print(repr(crudo[:900]))
