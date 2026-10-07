"""
Tests del modulo de comandas.

    cd precarga2
    .venv\Scripts\python -m pytest tests -q

Que cubren estos tests y que NO:
  - `test_comparar_original.py` corre contra la app de Streamlit vieja y exige
    que este en disco. Si no esta, se salta. Es el que de verdad garantiza que
    el port no cambio el papel ni el parseo.
  - El resto corre solo, sin base de datos y sin PDFs reales.

Los valores esperados de los PDFs NO estan hardcodeados uno por uno: se
comprueba lo que es estructural (numero de paginas, textos que deben estar,
que la mortera no contamine a la vianda). Los numeros exactos de cada comanda
vienen del golden set de PDFs reales, que todavia no esta.
"""
