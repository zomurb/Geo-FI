import re
import unicodedata
import sympy
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor

# Mapping of Russian command names to SymPy/English equivalents
FUNCTION_MAPPINGS = {
    'синус': 'sin',
    'косинус': 'cos',
    'тангенс': 'tan',
    'котангенс': 'cot',
    'лог': 'log',
    'корень': 'sqrt',
    'экспонента': 'exp',
    'модуль': 'abs',
    'арксинус': 'asin',
    'арккосинус': 'acos',
    'арктангенс': 'atan',
}

GEOMETRY_KEYWORDS = {
    'круг': 'circle',
    'окружность': 'circle',
    'треугольник': 'triangle',
    'прямоугольник': 'rectangle',
    'эллипс': 'ellipse',
    'парабола': 'parabola' 
}

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)
ALLOWED_SYMBOLS = {
    'x': sympy.Symbol('x'),
    'y': sympy.Symbol('y'),
    'z': sympy.Symbol('z'),
    't': sympy.Symbol('t'),
    'theta': sympy.Symbol('theta'),
    'phi': sympy.Symbol('phi'),
}
ALLOWED_NAMES = {
    **ALLOWED_SYMBOLS,
    'sin': sympy.sin,
    'cos': sympy.cos,
    'tan': sympy.tan,
    'cot': sympy.cot,
    'asin': sympy.asin,
    'acos': sympy.acos,
    'atan': sympy.atan,
    'sinh': sympy.sinh,
    'cosh': sympy.cosh,
    'tanh': sympy.tanh,
    'log': sympy.log,
    'sqrt': sympy.sqrt,
    'cbrt': lambda t: sympy.root(t, 3),
    'exp': sympy.exp,
    'abs': sympy.Abs,
    'pi': sympy.pi,
    'e': sympy.E,
}
SAFE_GLOBALS = {
    "__builtins__": {},
    "Symbol": sympy.Symbol,
    "Integer": sympy.Integer,
    "Float": sympy.Float,
    "Rational": sympy.Rational,
}

POINT_RE = re.compile(r'([a-zа-я])?\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)', re.IGNORECASE)

def _safe_parse_expr(expr_str):
    """Parse user expression with restricted namespace."""
    candidate = expr_str.strip()
    if len(candidate) > 300:
        raise ValueError("Слишком длинное выражение.")
    if "__" in candidate or "lambda" in candidate.lower():
        raise ValueError("Недопустимые конструкции в выражении.")
    return parse_expr(
        candidate,
        local_dict=ALLOWED_NAMES,
        global_dict=SAFE_GLOBALS,
        transformations=TRANSFORMATIONS
    )


def _extract_points(text):
    points = []
    labels = []
    for match in POINT_RE.finditer(text):
        label = (match.group(1) or "").upper()
        x_val = float(match.group(2))
        y_val = float(match.group(3))
        points.append((x_val, y_val))
        labels.append(label if label else f"P{len(points)}")
    return points, labels


def _parse_transformations(text):
    transforms = []
    if not text:
        return transforms

    chunk = text.lower()
    translate_match = re.search(r'(?:translate|сдвиг)\s*[:=]?\s*dx\s*=?\s*(-?\d+(?:\.\d+)?)\s*(?:dy\s*=?\s*(-?\d+(?:\.\d+)?))?', chunk)
    if translate_match:
        transforms.append({
            "op": "translate",
            "dx": float(translate_match.group(1)),
            "dy": float(translate_match.group(2) or 0.0),
        })

    rotate_match = re.search(r'(?:rotate|поворот)\s*[:=]?\s*(?:угол\s*=?\s*)?(-?\d+(?:\.\d+)?)', chunk)
    if rotate_match:
        transforms.append({"op": "rotate", "angle": float(rotate_match.group(1)), "origin": (0.0, 0.0)})

    scale_match = re.search(r'(?:scale|масштаб)\s*[:=]?\s*(?:k\s*=?\s*)?(-?\d+(?:\.\d+)?)', chunk)
    if scale_match:
        transforms.append({"op": "scale", "k": float(scale_match.group(1)), "origin": (0.0, 0.0)})

    reflect_match = re.search(r'(?:reflect|отражение)\s*(?:относительно)?\s*(x|y|origin)', chunk)
    if reflect_match:
        transforms.append({"op": "reflect", "axis": reflect_match.group(1)})
    return transforms


def _unicode_math_aliases(text):
    """
    Unicode-символы из Word/телефона → вид, понятный SymPy.
    Вызывается до .lower(), чтобы сохранить π→pi и т.п.
    """
    # Степени до NFKC: иначе ²→2 и получится x2 вместо x**2
    sup_map = {
        "\u2070": "0",
        "\u00b9": "1",
        "\u00b2": "2",
        "\u00b3": "3",
        "\u2074": "4",
        "\u2075": "5",
        "\u2076": "6",
        "\u2077": "7",
        "\u2078": "8",
        "\u2079": "9",
    }
    for u, d in sup_map.items():
        text = text.replace(u, f"**{d}")
    text = unicodedata.normalize("NFKC", text)
    # Частые операторы и константы
    text = text.replace("\u00d7", "*")  # ×
    text = text.replace("\u22c5", "*")  # ⋅
    text = text.replace("\u00b7", "*")  # ·
    text = text.replace("\u2212", "-")  # −
    text = text.replace("\u2013", "-")
    text = text.replace("\u2014", "-")
    text = text.replace("\u2264", "<=")
    text = text.replace("\u2265", ">=")
    text = text.replace("\u2260", "!=")
    text = text.replace("\u221e", "oo")  # ∞ → SymPy oo
    text = text.replace("\u03c0", "pi")  # π
    text = text.replace("\u03a0", "pi")  # Π как константа
    _cbrt = "\u221b"  # ∛
    _sqrt = "\u221a"  # √
    _dvert = "\u2016"  # ‖
    # Кубический корень ∛
    while _cbrt + "(" in text:
        text = text.replace(_cbrt + "(", "cbrt(", 1)
    text = re.sub(
        _cbrt + r"(\d+(?:[.,]\d+)?)",
        lambda m: "cbrt(" + m.group(1).replace(",", ".") + ")",
        text,
    )
    text = re.sub(_cbrt + "([xyztp])", r"cbrt(\1)", text)
    # Квадратный корень √
    while _sqrt + "(" in text:
        text = text.replace(_sqrt + "(", "sqrt(", 1)
    text = re.sub(
        _sqrt + r"(\d+(?:[.,]\d+)?)",
        lambda m: "sqrt(" + m.group(1).replace(",", ".") + ")",
        text,
    )
    text = re.sub(_sqrt + "([xyztp])", r"sqrt(\1)", text)
    # Модуль ‖…‖ (двойная вертикаль)
    text = re.sub(_dvert + "([^" + _dvert + "]+)" + _dvert, r"abs(\1)", text)
    return text


def preprocess_input(text):
    text = text.strip()
    text = _unicode_math_aliases(text)
    text = text.lower().strip()
    # Replace weird power syntax
    text = text.replace('^^', '**')
    
    # Replace |expr| with abs(expr)
    # Greedy match might be an issue for |x| + |y|, so use non-greedy
    text = re.sub(r'\|([^|]+)\|', r'abs(\1)', text)

    for rus, eng in FUNCTION_MAPPINGS.items():
        text = text.replace(rus, eng)
    return text

def parse_input(text):
    """
    Parses the user input and determines if it's a function plotting request
    (standard, parametric, piecewise) or a geometry visualization request.
    """
    text = preprocess_input(text)
    base_text = text
    transform_text = ""
    if "|" in text:
        base_text, transform_text = [part.strip() for part in text.split("|", 1)]
    transformations = _parse_transformations(transform_text)

    if base_text.startswith("реши:"):
        return parse_algebra("solve", base_text.split(":", 1)[1].strip())
    if base_text.startswith("объясни:"):
        return parse_algebra("explain", base_text.split(":", 1)[1].strip())
    if base_text.startswith("diff:") or base_text.startswith("производная:"):
        return parse_algebra("diff", base_text.split(":", 1)[1].strip())
    if base_text.startswith("integrate:") or base_text.startswith("интеграл:"):
        return parse_algebra("integrate", base_text.split(":", 1)[1].strip())
    
    # Check for geometry commands first
    for ru_keyword, shape_type in GEOMETRY_KEYWORDS.items():
        if base_text.startswith(ru_keyword):
            result = parse_geometry(base_text, shape_type)
            if result.get("type") == "geometry":
                result["transformations"] = transformations
            return result

    if base_text.startswith("прямая"):
        result = parse_geometry(base_text, "line")
        if result.get("type") == "geometry":
            result["transformations"] = transformations
        return result
    if base_text.startswith("многоугольник"):
        result = parse_geometry(base_text, "polygon")
        if result.get("type") == "geometry":
            result["transformations"] = transformations
        return result
    
    # Check for 3D: "z = x^2 + y^2"
    # Look for assignment to z (strictly z=, likely containing x and y)
    if re.search(r'\bz\s*(?<![<>!])=(?![=])', base_text):
        # Extract the RHS
        rhs = re.split(r'\bz\s*=', base_text, 1)[1].strip()
        return parse_3d(rhs)
        
    # Check for Polar: "r = 1 + cos(t)" or "r = t"
    if re.search(r'\br\s*(?<![<>!])=(?![=])', base_text):
        rhs = re.split(r'\br\s*=', base_text, 1)[1].strip()
        return parse_polar(rhs)

    # Check for parametric equations: "x = cos(t), y = sin(t)"
    # Simplistic check: must contain both "x=" and "y=" assignments
    # Use regex to avoid matching x>=0 as x=
    # We look for x followed by = (not >=, <=, ==, !=)
    has_x_assign = re.search(r'\bx\s*(?<![<>!])=(?![=])', base_text)
    has_y_assign = re.search(r'\by\s*(?<![<>!])=(?![=])', base_text)
    
    if has_x_assign and has_y_assign:
        # Allow semicolon or comma separation
        parts = re.split(r'[;,]', base_text)
        if len(parts) >= 2:
            x_part = None
            y_part = None
            for p in parts:
                p = p.strip()
                # Check strict assignment again for parts
                if re.match(r'^x\s*(?<![<>!])=(?![=])', p):
                    x_part = p.split('=', 1)[1].strip()
                elif re.match(r'^y\s*(?<![<>!])=(?![=])', p):
                    y_part = p.split('=', 1)[1].strip()
            
            if x_part and y_part:
                return parse_parametric(x_part, y_part)

    # Default to standard/piecewise function parsing
    return parse_multiple_functions(base_text)

def parse_geometry(text, shape_type):
    try:
        points, labels = _extract_points(text)
        if shape_type == 'circle':
            # "круг r=5" or "окружность радиус 3"
            r_match = re.search(r'(?:r|радиус)\s*=\s*(\d+(\.\d+)?)', text)
            center_match = re.search(r'центр\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)', text)
            center = (0.0, 0.0)
            if center_match:
                center = (float(center_match.group(1)), float(center_match.group(2)))
            if r_match:
                return {'type': 'geometry', 'shape': 'circle', 'r': float(r_match.group(1)), 'center': center}
            else:
                return {'type': 'error', 'message': "Укажите радиус, например: круг r=5"}
                
        elif shape_type == 'triangle':
            if len(points) == 3:
                return {'type': 'geometry', 'shape': 'triangle_points', 'points': points, 'labels': labels[:3]}
            # "треугольник a=3 b=4 c=5"
            params = {}
            for param in ['a', 'b', 'c']:
                match = re.search(f'{param}\s*=\s*(\d+(\.\d+)?)', text)
                if match:
                    params[param] = float(match.group(1))
            
            if len(params) == 3:
                return {'type': 'geometry', 'shape': 'triangle', **params}
            else:
                return {'type': 'error', 'message': "Укажите стороны a, b, c, например: треугольник a=3 b=4 c=5"}
        elif shape_type == 'line':
            if len(points) >= 2:
                return {'type': 'geometry', 'shape': 'line_points', 'points': points[:2], 'labels': labels[:2]}
            return {'type': 'error', 'message': "Укажите 2 точки, например: прямая через A(0,0) B(3,4)"}
        elif shape_type == 'polygon':
            if len(points) >= 3:
                return {'type': 'geometry', 'shape': 'polygon_points', 'points': points, 'labels': labels}
            return {'type': 'error', 'message': "Укажите минимум 3 точки, например: многоугольник (0,0),(2,1),(3,4)"}

        elif shape_type == 'rectangle':
             # "прямоугольник a=5 b=3" or "width=5 height=3"
            match_a = re.search(r'(?:a|width|ширина)\s*=\s*(\d+(\.\d+)?)', text)
            match_b = re.search(r'(?:b|height|высота)\s*=\s*(\d+(\.\d+)?)', text)
            
            if match_a and match_b:
                return {'type': 'geometry', 'shape': 'rectangle', 'width': float(match_a.group(1)), 'height': float(match_b.group(1))}
            else:
                return {'type': 'error', 'message': "Укажите стороны, например: прямоугольник a=5 b=3"}

        elif shape_type == 'ellipse':
             # "эллипс a=4 b=2"
            match_a = re.search(r'a\s*=\s*(\d+(\.\d+)?)', text)
            match_b = re.search(r'b\s*=\s*(\d+(\.\d+)?)', text)
            
            if match_a and match_b:
                return {'type': 'geometry', 'shape': 'ellipse', 'width': float(match_a.group(1)) * 2, 'height': float(match_b.group(1)) * 2}
            else:
                 return {'type': 'error', 'message': "Укажите полуоси a и b, например: эллипс a=4 b=2"}
                 
        return {'type': 'error', 'message': f"Фигура {shape_type} пока не поддерживается полностью."}
        
    except Exception as e:
        return {'type': 'error', 'message': f"Ошибка разбора параметров фигуры: {str(e)}"}


def parse_algebra(operation, raw_expr):
    from algebra_steps import explain_expression_with_steps, solve_equation_with_steps
    try:
        if operation == "solve":
            data = solve_equation_with_steps(raw_expr)
            return {
                "type": "algebra",
                "operation": "solve",
                "raw": raw_expr,
                "result": data["solutions"],
                "steps_text": data.get("steps_text", ""),
                "formula_help": data.get("formula_help", ""),
            }
        if operation == "diff":
            expr = _safe_parse_expr(raw_expr)
            from algebra_steps import _get_main_symbol
            x = _get_main_symbol(expr, "x")
            res = sympy.diff(expr, x)
            steps = (
                f"Правило: d/dx f(x) для вашего f.\n"
                f"f(x) = {sympy.pretty(expr, use_unicode=True)}\n"
                f"f′(x) = {sympy.pretty(res, use_unicode=True)}"
            )
            return {
                "type": "algebra",
                "operation": "diff",
                "raw": raw_expr,
                "result": res,
                "steps_text": steps,
                "formula_help": "Производные: (xⁿ)′=n·xⁿ⁻¹, (sin x)′=cos x, (cos x)′=−sin x, (eˣ)′=eˣ.",
            }
        if operation == "integrate":
            expr = _safe_parse_expr(raw_expr)
            from algebra_steps import _get_main_symbol
            x = _get_main_symbol(expr, "x")
            res = sympy.integrate(expr, x)
            steps = (
                f"Интегрируем по x.\n"
                f"f(x) = {sympy.pretty(expr, use_unicode=True)}\n"
                f"∫ f(x) dx = {sympy.pretty(res, use_unicode=True)} + C"
            )
            return {
                "type": "algebra",
                "operation": "integrate",
                "raw": raw_expr,
                "result": res,
                "steps_text": steps,
                "formula_help": "∫xⁿ dx = xⁿ⁺¹/(n+1) при n≠−1; ∫sin x dx = −cos x; ∫cos x dx = sin x.",
            }
        if operation == "explain":
            data = explain_expression_with_steps(raw_expr)
            ex = data["expr"]
            from algebra_steps import _get_main_symbol, _collect_real_solutions
            x_sym = _get_main_symbol(ex, "x")
            roots = _collect_real_solutions(ex, x_sym) if ex.free_symbols else []
            return {
                "type": "algebra",
                "operation": "explain",
                "raw": raw_expr,
                "result": {
                    "expr": ex,
                    "roots": roots,
                    "derivative": data["derivative"],
                },
                "steps_text": data.get("steps_text", ""),
                "formula_help": data.get("formula_help", ""),
            }
        return {"type": "error", "message": "Неизвестная алгебраическая операция."}
    except Exception as e:
        return {"type": "error", "message": f"Ошибка алгебраического запроса: {e}"}

def parse_parametric(x_str, y_str):
    try:
        x_expr = _safe_parse_expr(x_str)
        y_expr = _safe_parse_expr(y_str)
        return {
            'type': 'parametric',
            'data': {'x': x_expr, 'y': y_expr},
            'raw': f"x={x_str}, y={y_str}"
        }
    except Exception as e:
        return {'type': 'error', 'message': f"Ошибка разбора параметрического уравнения: {e}"}

def parse_polar(r_str):
    try:
        expr = _safe_parse_expr(r_str)
        return {
            'type': 'polar',
            'data': expr,
            'raw': r_str
        }
    except Exception as e:
        return {'type': 'error', 'message': f"Ошибка разбора полярного уравнения: {e}"}

def parse_3d(z_str):
    try:
        expr = _safe_parse_expr(z_str)
        return {
            'type': '3d',
            'data': expr,
            'raw': z_str
        }
    except Exception as e:
        return {'type': 'error', 'message': f"Ошибка разбора 3D функции: {e}"}

def parse_multiple_functions(text):
    # Handle piecewise functions having semicolons inside { }
    # We replace ; inside {} with a placeholder
    def replacement(match):
        return match.group(0).replace(';', '##SEMICOLON##')
    
    # Regex to find { ... } blocks and replace ; inside them
    # Non-nested
    text_processed = re.sub(r'\{[^}]*\}', replacement, text)
    
    # Split by semicolon for multiple functions
    parts = text_processed.split(';')
    functions = []
    
    for part in parts:
        # Restore semicolon
        part = part.replace('##SEMICOLON##', ';')
        part = part.strip()
        if not part: continue
        
        # Remove "y =" or "f(x) =" if present
        part = re.sub(r'^(?:y|f\(x\))\s*=\s*', '', part)
        
        try:
            # Check for piecewise syntax: { expr1, cond1; expr2, cond2 }
            if part.startswith('{') and part.endswith('}'):
                content = part[1:-1]
                # We replaced ; with ##SEMICOLON##, so split by that
                segments = content.split('##SEMICOLON##')
                piecewise_args = []
                for segment in segments:
                    if ',' in segment:
                        expr_str, cond_str = segment.split(',', 1)
                        # Sympy expects (expr, cond) tuples
                        expr = _safe_parse_expr(expr_str.strip())
                        
                        # Handle condition: replace =, <, > with sympy logic if possible or just parse
                        # Sympy parsing usually handles >=, <=, etc.
                        cond = _safe_parse_expr(cond_str.strip())
                        piecewise_args.append((expr, cond))
                    else:
                        # Fallback or error?
                        pass
                
                if piecewise_args:
                    # Create Sympy Piecewise object
                    expr = sympy.Piecewise(*piecewise_args)
                    functions.append(expr)
                    continue

            # Standard function
            expr = _safe_parse_expr(part)
            functions.append(expr)
        except Exception as e:
            return {'type': 'error', 'message': f"Не удалось разобрать формулу '{part}': {str(e)}"}
            
    if functions:
        return {'type': 'function', 'data': functions}
    else:
        return {'type': 'error', 'message': "Введите формулу."}
