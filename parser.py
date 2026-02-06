import sympy
import re
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor

# Mapping of Russian command names to SymPy/English equivalents
FUNCTION_MAPPINGS = {
    'синус': 'sin',
    'косинус': 'cos',
    'тангенс': 'tan',
    'лог': 'log',
    'корень': 'sqrt',
    'экспонента': 'exp',
    'модуль': 'abs'
}

GEOMETRY_KEYWORDS = {
    'круг': 'circle',
    'окружность': 'circle',
    'треугольник': 'triangle',
    'прямоугольник': 'rectangle',
    'эллипс': 'ellipse',
    'парабола': 'parabola' 
}

def preprocess_input(text):
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
    
    # Check for geometry commands first
    for ru_keyword, shape_type in GEOMETRY_KEYWORDS.items():
        if text.startswith(ru_keyword):
            return parse_geometry(text, shape_type)
    
    # Check for 3D: "z = x^2 + y^2"
    # Look for assignment to z (strictly z=, likely containing x and y)
    if re.search(r'\bz\s*(?<![<>!])=(?![=])', text):
        # Extract the RHS
        rhs = re.split(r'\bz\s*=', text, 1)[1].strip()
        return parse_3d(rhs)
        
    # Check for Polar: "r = 1 + cos(t)" or "r = t"
    if re.search(r'\br\s*(?<![<>!])=(?![=])', text):
        rhs = re.split(r'\br\s*=', text, 1)[1].strip()
        return parse_polar(rhs)

    # Check for parametric equations: "x = cos(t), y = sin(t)"
    # Simplistic check: must contain both "x=" and "y=" assignments
    # Use regex to avoid matching x>=0 as x=
    # We look for x followed by = (not >=, <=, ==, !=)
    has_x_assign = re.search(r'\bx\s*(?<![<>!])=(?![=])', text)
    has_y_assign = re.search(r'\by\s*(?<![<>!])=(?![=])', text)
    
    if has_x_assign and has_y_assign:
        # Allow semicolon or comma separation
        parts = re.split(r'[;,]', text)
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
    return parse_multiple_functions(text)

def parse_geometry(text, shape_type):
    try:
        if shape_type == 'circle':
            # "круг r=5" or "окружность радиус 3"
            r_match = re.search(r'(?:r|радиус)\s*=\s*(\d+(\.\d+)?)', text)
            if r_match:
                return {'type': 'geometry', 'shape': 'circle', 'r': float(r_match.group(1))}
            else:
                return {'type': 'error', 'message': "Укажите радиус, например: круг r=5"}
                
        elif shape_type == 'triangle':
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

def parse_parametric(x_str, y_str):
    transformations = (standard_transformations + (implicit_multiplication_application, convert_xor))
    try:
        x_expr = parse_expr(x_str, transformations=transformations)
        y_expr = parse_expr(y_str, transformations=transformations)
        return {
            'type': 'parametric',
            'data': {'x': x_expr, 'y': y_expr},
            'raw': f"x={x_str}, y={y_str}"
        }
    except Exception as e:
        return {'type': 'error', 'message': f"Ошибка разбора параметрического уравнения: {e}"}

def parse_polar(r_str):
    transformations = (standard_transformations + (implicit_multiplication_application, convert_xor))
    try:
        # Support theta, phi, t as variables
        # We need to ensure SymPy treats them as symbols? parse_expr does that automatically.
        expr = parse_expr(r_str, transformations=transformations)
        return {
            'type': 'polar',
            'data': expr,
            'raw': r_str
        }
    except Exception as e:
        return {'type': 'error', 'message': f"Ошибка разбора полярного уравнения: {e}"}

def parse_3d(z_str):
    transformations = (standard_transformations + (implicit_multiplication_application, convert_xor))
    try:
        expr = parse_expr(z_str, transformations=transformations)
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
    
    transformations = (standard_transformations + (implicit_multiplication_application, convert_xor))
    
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
                        expr = parse_expr(expr_str.strip(), transformations=transformations)
                        
                        # Handle condition: replace =, <, > with sympy logic if possible or just parse
                        # Sympy parsing usually handles >=, <=, etc.
                        cond = parse_expr(cond_str.strip(), transformations=transformations)
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
            expr = parse_expr(part, transformations=transformations)
            functions.append(expr)
        except Exception as e:
            return {'type': 'error', 'message': f"Не удалось разобрать формулу '{part}': {str(e)}"}
            
    if functions:
        return {'type': 'function', 'data': functions}
    else:
        return {'type': 'error', 'message': "Введите формулу."}
