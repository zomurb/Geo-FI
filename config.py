import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Plotting configuration
PLOT_SIZE = (10, 8)  # Inches
DPI = 100
DEFAULT_X_RANGE = (-10, 10)
DEFAULT_Y_RANGE = (-10, 10)

# 3D surface defaults (камера и окно; меняются кнопками)
DEFAULT_3D_ELEV = 22
DEFAULT_3D_AZIM = 45
DEFAULT_3D_RANGE = 5.0
DEFAULT_3D_GRID = 50
DEFAULT_3D_MODE = "surface"  # surface | wireframe | both

# Path to fonts if needed, otherwise matplotlib defaults
# FONT_PATH = "arial.ttf" 

# Error messages
ERROR_PARSING = "Не удалось разобрать формулу. Проверьте синтаксис."
ERROR_UNSUPPORTED = "Фунция не поддерживается."
ERROR_GENERIC = "Произошла ошибка при построении графика."

ALGEBRA_SOLVE_TEMPLATE = "Корни (веществ.): {result}"
ALGEBRA_DIFF_TEMPLATE = "f′(x) = {result}"
ALGEBRA_INTEGRATE_TEMPLATE = "∫ f(x) dx = {result} + C"
EXPLAIN_TEMPLATE = (
    "f(x) = {expr}\n"
    "f′(x) = {derivative}\n"
    "Корни f(x)=0 (все, что выдал SymPy): {roots}"
)
