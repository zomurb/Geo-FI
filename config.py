import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Plotting configuration
PLOT_SIZE = (10, 8)  # Inches
DPI = 100
DEFAULT_X_RANGE = (-10, 10)
DEFAULT_Y_RANGE = (-10, 10)

# Path to fonts if needed, otherwise matplotlib defaults
# FONT_PATH = "arial.ttf" 

# Error messages
ERROR_PARSING = "Не удалось разобрать формулу. Проверьте синтаксис."
ERROR_UNSUPPORTED = "Фунция не поддерживается."
ERROR_GENERIC = "Произошла ошибка при построении графика."
