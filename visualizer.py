import matplotlib.pyplot as plt
import numpy as np
import io
import sympy
from config import PLOT_SIZE, DPI, DEFAULT_X_RANGE
from geometry import CircleShape, TriangleShape, RectangleShape, EllipseShape

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
            has_plotted = True
            
        except Exception as e:
            print(f"Error plotting {expr}: {e}")
            continue

    if has_plotted:
        ax.legend()
        ax.set_title("График функции")
        ax.set_ylim(-10, 10) 
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

def plot_3d(z_data):
    # 3D plot needs its own figure/axis setup
    fig = plt.figure(figsize=PLOT_SIZE, dpi=DPI)
    ax = fig.add_subplot(projection='3d')
    
    expr = z_data['data']
    # We expect x and y
    x, y = sympy.symbols('x y')
    
    try:
        f_z = sympy.lambdify((x, y), expr, modules=['numpy'])
        
        # Create meshgrid
        range_val = 5
        X = np.linspace(-range_val, range_val, 50)
        Y = np.linspace(-range_val, range_val, 50)
        X, Y = np.meshgrid(X, Y)
        
        Z = f_z(X, Y)
        
        # Handle scalar Z
        if np.isscalar(Z):
            Z = np.full_like(X, Z)
            
        surf = ax.plot_surface(X, Y, Z, cmap='viridis', edgecolor='none', alpha=0.8)
        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
        
        ax.set_title(f"z = ${sympy.latex(expr)}$")
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
            shape = CircleShape(shape_info['r'])
        elif shape_type == 'triangle':
            shape = TriangleShape(shape_info['a'], shape_info['b'], shape_info['c'])
        elif shape_type == 'rectangle':
            shape = RectangleShape(shape_info['width'], shape_info['height'])
        elif shape_type == 'ellipse':
             shape = EllipseShape(shape_info['width'], shape_info['height'])
            
        if shape:
            shape.plot(ax)
            details_text = shape.get_details()
            ax.set_title(details_text.split('\n')[0]) # Title is first line
            
            # Add text box with details
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.05, 0.95, details_text, transform=ax.transAxes, fontsize=10,
                    verticalalignment='top', bbox=props)
            
    except Exception as e:
        ax.text(0.5, 0.5, f"Ошибка построения фигуры: {e}", ha='center', va='center')

    return get_plot_buffer(fig)
