"""
Пошаговые объяснения для режимов «реши» и «объясни».
"""
import sympy
from sympy import Eq, expand, together


def _symstr(expr):
    return sympy.pretty(expr, use_unicode=True)


def _latex(expr):
    try:
        return sympy.latex(expr)
    except Exception:
        return str(expr)


def _parse(s: str):
    from parser import _safe_parse_expr

    return _safe_parse_expr(s.strip())


def _get_main_symbol(f, preferred="x"):
    """Совпадение с SymPy-sимволом из parser._safe_parse_expr (тот же name, другой id)."""
    syms = list(f.free_symbols)
    if not syms:
        return sympy.Symbol(preferred, real=True)
    for s in syms:
        if s.name == preferred:
            return s
    return syms[0]


def _collect_real_solutions(f, x):
    """Собираем вещественные корни f(x)=0 (x — тот же символ, что в f)."""
    sol = sympy.solve(f, x)
    if not isinstance(sol, list):
        sol = [sol] if sol not in (None, []) else []
    out = []
    for s in sol:
        if s is None:
            continue
        if getattr(s, "is_real", None) is False:
            continue
        out.append(s)
    return out


def solve_equation_with_steps(raw: str) -> dict:
    """
    Уравнение 'левая=правая' или выражение f(x)=0: ответ + пошагово + проверка.
    """
    steps = []

    if "=" in raw:
        left, right = raw.split("=", 1)
        left_e = _parse(left)
        right_e = _parse(right)
        eq = Eq(left_e, right_e)
        f = expand(left_e - right_e)
        steps.append(f"1) Исходное уравнение: {_symstr(eq)}")
        steps.append(f"2) Приводим к виду f(x) = 0: f(x) = {_symstr(expand(f))}")
    else:
        f = expand(_parse(raw))
        steps.append(f"1) Ищем x, при котором f(x) = 0, где f(x) = {_symstr(f)}")

    f = together(sympy.simplify(f))
    x = _get_main_symbol(f, "x")
    steps.append(f"3) Упрощённо: f(x) = {_symstr(f)}")

    if f == 0 or not f.free_symbols:
        steps.append("4) f не зависит от x (или тождественно 0) — уточните запрос.")
        return {
            "solutions": [],
            "steps_text": "\n".join(steps),
            "formula_help": "Для 'реши' используй равенство, например: реши: x^2-5*x+6=0",
        }

    deg = sympy.degree(f, x) if f.is_polynomial(x) else None
    if deg == 2 and f.is_polynomial(x):
        poly = sympy.Poly(f, x)
        a, b, c = poly.all_coeffs()
        d = b**2 - 4 * a * c
        steps.append(
            f"4) Квадратное уравнение: a={_symstr(a)}, b={_symstr(b)}, c={_symstr(c)}"
        )
        steps.append(f"   D = b² − 4ac = {_symstr(sympy.simplify(d))}")
        try:
            d_val = float(sympy.N(sympy.simplify(d)))
        except (TypeError, ValueError):
            d_val = None
        if d_val is not None and d_val >= 0:
            x1 = (-b + sympy.sqrt(d)) / (2 * a)
            x2 = (-b - sympy.sqrt(d)) / (2 * a)
            steps.append(f"   x₁ = (-b+√D)/(2a) = {_symstr(sympy.simplify(x1))}")
            steps.append(f"   x₂ = (-b-√D)/(2a) = {_symstr(sympy.simplify(x2))}")
        elif d_val is not None and d_val < 0:
            steps.append("   D < 0 — в вещественных числах корней нет (есть комплексные).")
        else:
            steps.append("   D без численной оценки — смотрите корни, посчитанные ниже (SymPy).")

    solutions = _collect_real_solutions(f, x)
    steps.append(f"5) Корни (веществ., SymPy): {solutions if solutions else 'нет'}")

    checks = []
    for sol in solutions[:8]:
        val = sympy.simplify(f.subs(x, sol))
        ok = val == 0
        if not ok:
            try:
                ok = abs(float(sympy.N(val))) < 1e-8
            except (TypeError, ValueError):
                ok = bool(sympy.simplify(val) == 0)
        checks.append("OK" if ok else f"f({_symstr(sol)}) = {_symstr(val)}")

    if checks:
        steps.append("6) Проверка подстановкой: " + ", ".join(checks))

    formula_help = (
        "Формулы: приведение к f(x)=0; для ax²+bx+c=0: D=b²−4ac, x=(-b±√D)/(2a)."
    )
    if deg == 1 and f.is_polynomial(x):
        formula_help = "Линейное: ax+b=0 → x=-b/a."

    return {
        "solutions": solutions,
        "steps_text": "\n".join(steps),
        "formula_help": formula_help,
        "latex_f": _latex(f),
    }


def explain_expression_with_steps(raw: str) -> dict:
    """Подробный разбор: упрощение, фактор, корни, производная."""
    expr0 = _parse(raw)
    expr = expand(expr0)
    x = _get_main_symbol(expr, "x")
    steps = []
    steps.append(f"1) Ваше выражение: f(x) = {_symstr(expr)}")

    simp = sympy.simplify(expr)
    if simp != expr:
        steps.append(f"2) Упрощение: f(x) = {_symstr(simp)}")
    else:
        steps.append("2) Сильно упростить нельзя — оставляем исходный вид.")

    fact = sympy.factor(simp)
    if fact != simp:
        steps.append(f"3) Факторизация: f(x) = {_symstr(fact)}")

    if simp.has(x) and simp.is_polynomial(x) and sympy.degree(simp, x) >= 1:
        roots = _collect_real_solutions(simp, x)
        if roots:
            parts = [f"{_symstr(r)}" for r in roots]
            steps.append(
                f"4) Когда f(x) = 0, в вещественных x: {', '.join(parts)}"
            )
        else:
            steps.append("4) В вещественных x корней f(x)=0 нет (или f не обнуляется).")

    d = sympy.simplify(sympy.diff(simp, x))
    steps.append(f"5) Производная: f′(x) = {_symstr(d)} (правила суммы, степени, sin, …)")
    steps.append("6) Про f′: в каждой точке x это наклон касательной к графику y=f(x).")

    formula_help = (
        "Справка: f′(x) для полинома — по степенному правилу; для sin/cos — таблица производных; "
        "корни f(x)=0 — из разложения или формулы дискриминанта."
    )

    return {
        "expr": simp,
        "derivative": d,
        "steps_text": "\n".join(steps),
        "formula_help": formula_help,
    }
