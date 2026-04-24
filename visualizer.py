import matplotlib.pyplot as plt
import numpy as np
import io
import sympy
from config import (
    PLOT_SIZE,
    DPI,
    DEFAULT_X_RANGE,
    DEFAULT_3D_ELEV,
    DEFAULT_3D_AZIM,
    DEFAULT_3D_RANGE,
    DEFAULT_3D_GRID,
    DEFAULT_3D_MODE,
)
from geometry import (
    CircleShape,
    TriangleShape,
    RectangleShape,
    EllipseShape,
    Point,
    TrianglePointsShape,
    PolygonShape,
    LineShape,
)

def get_plot_buffer(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def create_base_plot():
    fig, ax = plt.subplots(figsize=PLOT_SIZE, dpi=DPI)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    ax.axhline(y=0, color='k', linewidth=1)
    ax.axvline(x=0, color='k', linewidth=1)
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    return fig, ax

def clean_data_for_plot(x, y, threshold=10.0):
    """
    detects discontinuities (vertical asymptotes) and inserts NaN
    removes complex values
    """
    # 1. Handle complex numbers (if any slipped through numpy)
    if np.iscomplexobj(y):
        # Set complex entries to NaN
        y = np.where(np.iscomplex(y), np.nan, np.real(y))
    
    # 2. Handle simple discontinuities (jumps)
    dy = np.diff(y)
    dx = np.diff(x)
    
    with np.errstate(divide='ignore', invalid='ignore'):
         slope = np.abs(dy / dx)
    
    # Threshold for "too steep" -> likely asymptote
    mask = slope > threshold
    
    points_x = []
    points_y = []
    
    for i in range(len(x) - 1):
        points_x.append(x[i])
        points_y.append(y[i])
        
        if mask[i]:
            points_x.append(np.nan)
            points_y.append(np.nan)
            
    points_x.append(x[-1])
    points_y.append(y[-1])
    
    return np.array(points_x), np.array(points_y)

def plot_function(functions_data, x_range=DEFAULT_X_RANGE):
    fig, ax = create_base_plot()
    
    # Increase resolution for better curves
    x_vals_orig = np.linspace(x_range[0], x_range[1], 1000)
    x_sym = sympy.symbols('x')
    
    has_plotted = False
    plotted_y_values = []
    
    for expr in functions_data:
        try:
            # Prepare lambdified function
            f_lambdified = sympy.lambdify(x_sym, expr, modules=['numpy'])
            
            # Evaluate
            with np.errstate(invalid='ignore', divide='ignore'):
                 y_vals_orig = f_lambdified(x_vals_orig)
            
            # Broadcast scalar if constant function
            if np.isscalar(y_vals_orig):
                y_vals_orig = np.full_like(x_vals_orig, y_vals_orig)
            
            # Post-process for complex/invalid values
            if np.iscomplexobj(y_vals_orig):
                 y_vals_orig = np.where(np.iscomplex(y_vals_orig), np.nan, np.real(y_vals_orig))

            # Detect discontinuities
            x_plot, y_plot = clean_data_for_plot(x_vals_orig, y_vals_orig, threshold=100) 
            
            label = f"${sympy.latex(expr)}$"
            ax.plot(x_plot, y_plot, label=label, linewidth=2)
            finite_y = y_plot[np.isfinite(y_plot)]
            if finite_y.size:
                plotted_y_values.append(finite_y)
            has_plotted = True
            
        except Exception as e:
            print(f"Error plotting {expr}: {e}")
            continue

    if has_plotted:
        ax.legend()
        ax.set_title("График функции")
        if plotted_y_values:
            all_y = np.concatenate(plotted_y_values)
            lower = np.percentile(all_y, 2)
            upper = np.percentile(all_y, 98)
            if np.isfinite(lower) and np.isfinite(upper) and lower < upper:
                pad = max((upper - lower) * 0.15, 1.0)
                ax.set_ylim(lower - pad, upper + pad)
    else:
        ax.text(0.5, 0.5, "Ошибка построения", ha='center', va='center')

    return get_plot_buffer(fig)

def plot_parametric(parametric_data, t_range=(-10, 10)):
    fig, ax = create_base_plot()
    
    t_vals = np.linspace(t_range[0], t_range[1], 1000)
    t_sym = sympy.symbols('t')
    
    try:
        x_expr = parametric_data['x']
        y_expr = parametric_data['y']
        
        fx = sympy.lambdify(t_sym, x_expr, modules=['numpy'])
        fy = sympy.lambdify(t_sym, y_expr, modules=['numpy'])
        
        x_vals = fx(t_vals)
        y_vals = fy(t_vals)
        
        if np.isscalar(x_vals): x_vals = np.full_like(t_vals, x_vals)
        if np.isscalar(y_vals): y_vals = np.full_like(t_vals, y_vals)
        
        ax.plot(x_vals, y_vals, label='Parametric', linewidth=2)
        ax.set_title("Параметрический график")
        # ax.legend()
        ax.axis('equal') 
        
    except Exception as e:
        ax.text(0.5, 0.5, f"Ошибка: {e}", ha='center', va='center')
        
    return get_plot_buffer(fig)

def plot_polar(polar_data):
    fig, ax = create_base_plot()
    
    # Heuristic for variable: t, theta, phi
    r_expr = polar_data['data']
    free_symbols = r_expr.free_symbols
    var_sym = None
    
    # Default to 't' if no symbols
    if not free_symbols:
        var_sym = sympy.Symbol('t')
    else:
        # Pick the first one that looks like an angle
        for s in free_symbols:
            if str(s) in ['t', 'theta', 'phi', 'x']: # allow x as parameter too
                var_sym = s
                break
        if not var_sym:
             var_sym = list(free_symbols)[0]
             
    # Range: 0 to 4pi usually safe for polar
    t_vals = np.linspace(0, 4 * np.pi, 1000)
    
    try:
        f_r = sympy.lambdify(var_sym, r_expr, modules=['numpy'])
        r_vals = f_r(t_vals)
        
        if np.isscalar(r_vals): r_vals = np.full_like(t_vals, r_vals)
        
        # Convert to cartesian for standard plot
        x_vals = r_vals * np.cos(t_vals)
        y_vals = r_vals * np.sin(t_vals)
        
        ax.plot(x_vals, y_vals, label=f"r={sympy.latex(r_expr)}", linewidth=2)
        ax.set_title("Полярный график")
        ax.axis('equal')
        
    except Exception as e:
        ax.text(0.5, 0.5, f"Ошибка Polar: {e}", ha='center', va='center')

    return get_plot_buffer(fig)

def plot_3d(
    z_data,
    elev=None,
    azim=None,
    range_val=None,
    grid_n=None,
    mode=None,
    contour_base=False,
):
    """
    z_data: dict с ключом 'data' (SymPy выражение z=f(x,y)).
    elev/azim — углы камеры (view_init).
    range_val — полуинтервал по x и y: [-R, R].
    mode: surface | wireframe | both
    contour_base — заливка контуров на «полу» (z = min).
    """
    elev = DEFAULT_3D_ELEV if elev is None else float(elev)
    azim = DEFAULT_3D_AZIM if azim is None else float(azim)
    range_val = float(DEFAULT_3D_RANGE if range_val is None else range_val)
    grid_n = int(DEFAULT_3D_GRID if grid_n is None else grid_n)
    mode = (mode or DEFAULT_3D_MODE).lower()
    if mode not in ("surface", "wireframe", "both"):
        mode = "surface"

    range_val = max(0.35, min(22.0, range_val))
    grid_n = max(18, min(110, grid_n))
    elev = max(-89.0, min(89.0, elev))
    azim = float(azim % 360.0)

    fig = plt.figure(figsize=PLOT_SIZE, dpi=DPI)
    ax = fig.add_subplot(projection='3d')
    ax.view_init(elev=elev, azim=azim)

    expr = z_data['data']
    x_sym = next((s for s in expr.free_symbols if getattr(s, "name", "") == "x"), sympy.Symbol("x"))
    y_sym = next((s for s in expr.free_symbols if getattr(s, "name", "") == "y"), sympy.Symbol("y"))

    try:
        f_z = sympy.lambdify((x_sym, y_sym), expr, modules=['numpy'])

        X = np.linspace(-range_val, range_val, grid_n)
        Y = np.linspace(-range_val, range_val, grid_n)
        X, Y = np.meshgrid(X, Y)

        with np.errstate(invalid='ignore', divide='ignore'):
            Z = f_z(X, Y)

        if np.isscalar(Z):
            Z = np.full_like(X, Z, dtype=float)
        Z = np.asarray(Z, dtype=float)

        stride = max(1, grid_n // 22)

        drew_surface = False
        if mode in ("surface", "both"):
            surf = ax.plot_surface(
                X, Y, Z,
                cmap='viridis',
                edgecolor='none',
                alpha=0.78 if mode == "both" else 0.88,
                linewidth=0,
            )
            fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
            drew_surface = True
        if mode in ("wireframe", "both"):
            ax.plot_wireframe(
                X, Y, Z,
                rstride=stride,
                cstride=stride,
                color='0.15',
                linewidth=0.35 if mode == "both" else 0.45,
                alpha=0.55 if mode == "both" else 0.85,
            )

        zmin = float(np.nanmin(Z))
        zmax = float(np.nanmax(Z))
        zpad = max((zmax - zmin) * 0.06, 1e-6)
        ax.set_zlim(zmin - zpad, zmax + zpad)

        if contour_base:
            floor = zmin - zpad * 1.1
            ax.contourf(X, Y, Z, zdir='z', offset=floor, levels=14, cmap='viridis', alpha=0.5)

        title = f"z = ${sympy.latex(expr)}$"
        title += f"\nкамера elev={elev:.0f}°, azim={azim:.0f}° | окно ±{range_val:g} | сетка {grid_n} | {mode}"
        if contour_base:
            title += " | контур у основания"
        ax.set_title(title, fontsize=10)
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_zlabel('z')

    except Exception as e:
        ax.text2D(0.5, 0.5, f"Ошибка 3D: {e}", transform=ax.transAxes, ha='center', va='center')

    return get_plot_buffer(fig)

def plot_geometry(shape_info):
    fig, ax = create_base_plot()
    
    shape_type = shape_info.get('shape')
    details_text = ""
    
    try:
        shape = None
        if shape_type == 'circle':
            shape = CircleShape(shape_info['r'], center=shape_info.get('center', (0.0, 0.0)))
        elif shape_type == 'triangle':
            shape = TriangleShape(shape_info['a'], shape_info['b'], shape_info['c'])
        elif shape_type == 'triangle_points':
            pts = [Point(x, y) for x, y in shape_info['points']]
            shape = TrianglePointsShape(pts, labels=shape_info.get("labels"))
        elif shape_type == 'line_points':
            p1 = Point(shape_info['points'][0][0], shape_info['points'][0][1])
            p2 = Point(shape_info['points'][1][0], shape_info['points'][1][1])
            shape = LineShape(p1, p2)
        elif shape_type == 'polygon_points':
            pts = [Point(x, y) for x, y in shape_info['points']]
            shape = PolygonShape(pts)
        elif shape_type == 'rectangle':
            shape = RectangleShape(shape_info['width'], shape_info['height'])
        elif shape_type == 'ellipse':
             shape = EllipseShape(shape_info['width'], shape_info['height'])
            
        if shape:
            transformed_shape = shape.transformed(shape_info.get("transformations", []))
            if shape_info.get("transformations"):
                shape.plot(ax, color="gray", alpha=0.45)
                transformed_shape.plot(ax, color="tab:blue", alpha=1.0)
            else:
                transformed_shape.plot(ax)
            details_text = shape.get_details()
            ax.set_title(details_text.split('\n')[0]) # Title is first line
            
            # Add text box with details
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.05, 0.95, details_text, transform=ax.transAxes, fontsize=10,
                    verticalalignment='top', bbox=props)

            if isinstance(transformed_shape, TrianglePointsShape):
                for label, point in zip(transformed_shape.labels, transformed_shape.points):
                    ax.plot(point.x, point.y, "o", color="tab:blue")
                    ax.text(point.x, point.y, f" {label}", fontsize=10)
                centers = transformed_shape.triangle_centers()
                markers = {"centroid": "G", "incenter": "I", "circumcenter": "O"}
                for key, center in centers.items():
                    ax.plot(center.x, center.y, "x", color="tab:red")
                    ax.text(center.x, center.y, f" {markers.get(key, key)}", fontsize=9)
            elif isinstance(transformed_shape, PolygonShape):
                for idx, point in enumerate(transformed_shape.points, start=1):
                    ax.plot(point.x, point.y, "o", color="tab:blue")
                    ax.text(point.x, point.y, f" P{idx}", fontsize=9)
            elif isinstance(transformed_shape, LineShape):
                ax.plot(transformed_shape.p1.x, transformed_shape.p1.y, "o", color="tab:blue")
                ax.plot(transformed_shape.p2.x, transformed_shape.p2.y, "o", color="tab:blue")
                ax.text(transformed_shape.p1.x, transformed_shape.p1.y, " A", fontsize=9)
                ax.text(transformed_shape.p2.x, transformed_shape.p2.y, " B", fontsize=9)
            
    except Exception as e:
        ax.text(0.5, 0.5, f"Ошибка построения фигуры: {e}", ha='center', va='center')

    return get_plot_buffer(fig)
