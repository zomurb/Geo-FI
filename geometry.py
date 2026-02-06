import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle, Ellipse
import numpy as np

class GeometricShape:
    def plot(self, ax):
        raise NotImplementedError

    def get_details(self):
        return ""

class CircleShape(GeometricShape):
    def __init__(self, radius, center=(0, 0)):
        self.radius = radius
        self.center = center

    def plot(self, ax):
        circle = Circle(self.center, self.radius, fill=False, color='blue', linewidth=2)
        ax.add_patch(circle)
        ax.set_aspect('equal')
        
        # Adjust limits to show the circle
        ax.set_xlim(self.center[0] - self.radius * 1.5, self.center[0] + self.radius * 1.5)
        ax.set_ylim(self.center[1] - self.radius * 1.5, self.center[1] + self.radius * 1.5)

    def get_details(self):
        area = np.pi * self.radius ** 2
        circumference = 2 * np.pi * self.radius
        return f"Круг: R={self.radius}, Площадь={area:.2f}, Периметр={circumference:.2f}"

class TriangleShape(GeometricShape):
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

    def plot(self, ax):
        # Calculate coordinates (Heron's formula approach to place points)
        # Using Law of Cosines to find angle C
        # c^2 = a^2 + b^2 - 2ab cos(C) -> cos(C) = (a^2+b^2-c^2)/(2ab)
        
        # Let point A be at (0, 0)
        # Let point B be at (a, 0)
        # Point C is at (b * cos(C), b * sin(C))
        
        try:
            cos_C = (self.a**2 + self.b**2 - self.c**2) / (2 * self.a * self.b)
            angle_C = np.arccos(cos_C)
            cx = self.b * np.cos(angle_C)
            cy = self.b * np.sin(angle_C)
            
            points = np.array([[0, 0], [self.a, 0], [cx, cy]])
            triangle = Polygon(points, fill=False, color='green', linewidth=2)
            ax.add_patch(triangle)
            ax.set_aspect('equal')
            
            # Simple auto-scale
            ax.autoscale_view()
            
        except ValueError:
             # Invalid triangle
             pass


    def get_details(self):
        s = (self.a + self.b + self.c) / 2
        area = np.sqrt(s * (s - self.a) * (s - self.b) * (s - self.c))
        perimeter = self.a + self.b + self.c
        return f"Треугольник: a={self.a}, b={self.b}, c={self.c}\nПлощадь={area:.2f}, Периметр={perimeter:.2f}"

class RectangleShape(GeometricShape):
    def __init__(self, width, height, center=(0,0)):
        self.width = width
        self.height = height
        self.center = center

    def plot(self, ax):
        # Bottom left corner
        xy = (self.center[0] - self.width / 2, self.center[1] - self.height / 2)
        rect = Rectangle(xy, self.width, self.height, fill=False, color='red', linewidth=2)
        ax.add_patch(rect)
        ax.set_aspect('equal')
        
        ax.set_xlim(self.center[0] - self.width, self.center[0] + self.width)
        ax.set_ylim(self.center[1] - self.height, self.center[1] + self.height)

    def get_details(self):
        area = self.width * self.height
        perimeter = 2 * (self.width + self.height)
        return f"Прямоугольник: {self.width}x{self.height}, Площадь={area:.2f}, Периметр={perimeter:.2f}"

class EllipseShape(GeometricShape):
    def __init__(self, width, height, center=(0,0)):
        self.width = width
        self.height = height
        self.center = center

    def plot(self, ax):
        ellipse = Ellipse(self.center, self.width, self.height, fill=False, color='purple', linewidth=2)
        ax.add_patch(ellipse)
        ax.set_aspect('equal')
        
        ax.set_xlim(self.center[0] - self.width, self.center[0] + self.width)
        ax.set_ylim(self.center[1] - self.height, self.center[1] + self.height)

    def get_details(self):
        # Approximation of perimeter (Ramanujan)
        a = self.width / 2
        b = self.height / 2
        h = ((a - b)**2) / ((a + b)**2)
        perimeter = np.pi * (a + b) * (1 + (3*h) / (10 + np.sqrt(4 - 3*h)))
        area = np.pi * a * b
        return f"Эллипс: a={a}, b={b}, Площадь={area:.2f}, Периметр≈{perimeter:.2f}"
