from dataclasses import dataclass
import numpy as np
from matplotlib.patches import Circle, Polygon, Rectangle, Ellipse


@dataclass
class Point:
    x: float
    y: float

    def as_tuple(self):
        return (self.x, self.y)


def _to_np(points):
    return np.array([[p.x, p.y] for p in points], dtype=float)


def _to_points(arr):
    return [Point(float(row[0]), float(row[1])) for row in arr]


def apply_transformations(points, transforms):
    arr = _to_np(points)
    if not transforms:
        return points

    for transform in transforms:
        op = transform.get("op")
        if op == "translate":
            arr[:, 0] += transform.get("dx", 0.0)
            arr[:, 1] += transform.get("dy", 0.0)
        elif op == "rotate":
            angle = np.deg2rad(transform.get("angle", 0.0))
            origin = transform.get("origin", (0.0, 0.0))
            ox, oy = origin
            shifted = arr - np.array([ox, oy])
            rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
            arr = shifted @ rot.T + np.array([ox, oy])
        elif op == "scale":
            k = transform.get("k", 1.0)
            origin = transform.get("origin", (0.0, 0.0))
            ox, oy = origin
            arr = (arr - np.array([ox, oy])) * k + np.array([ox, oy])
        elif op == "reflect":
            axis = transform.get("axis", "x")
            if axis == "x":
                arr[:, 1] = -arr[:, 1]
            elif axis == "y":
                arr[:, 0] = -arr[:, 0]
            elif axis == "origin":
                arr *= -1

    return _to_points(arr)


class GeometricShape:
    def plot(self, ax, color="tab:blue", alpha=1.0):
        raise NotImplementedError

    def get_details(self):
        return ""

    def transformed(self, transforms):
        return self


class CircleShape(GeometricShape):
    def __init__(self, radius, center=(0, 0)):
        self.radius = radius
        self.center = Point(center[0], center[1])

    def plot(self, ax, color="tab:blue", alpha=1.0):
        circle = Circle(self.center.as_tuple(), self.radius, fill=False, color=color, linewidth=2, alpha=alpha)
        ax.add_patch(circle)
        ax.set_aspect('equal')
        ax.set_xlim(self.center.x - self.radius * 1.6, self.center.x + self.radius * 1.6)
        ax.set_ylim(self.center.y - self.radius * 1.6, self.center.y + self.radius * 1.6)

    def get_details(self):
        area = np.pi * self.radius ** 2
        circumference = 2 * np.pi * self.radius
        return f"Круг: R={self.radius}, Площадь={area:.2f}, Периметр={circumference:.2f}"

    def transformed(self, transforms):
        center = apply_transformations([self.center], transforms)[0]
        scaled = self.radius
        for t in transforms or []:
            if t.get("op") == "scale":
                scaled *= abs(t.get("k", 1.0))
        return CircleShape(scaled, center.as_tuple())


class TriangleShape(GeometricShape):
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c
        self.points = self._build_points_from_sides()

    def _build_points_from_sides(self):
        if min(self.a, self.b, self.c) <= 0:
            return []
        if self.a + self.b <= self.c or self.a + self.c <= self.b or self.b + self.c <= self.a:
            return []
        cos_c = np.clip((self.a**2 + self.b**2 - self.c**2) / (2 * self.a * self.b), -1.0, 1.0)
        angle_c = np.arccos(cos_c)
        return [Point(0, 0), Point(self.a, 0), Point(self.b * np.cos(angle_c), self.b * np.sin(angle_c))]

    def triangle_centers(self):
        if len(self.points) != 3:
            return {}
        a, b, c = self.points
        arr = _to_np(self.points)
        centroid = Point(float(arr[:, 0].mean()), float(arr[:, 1].mean()))

        side_a = np.linalg.norm(arr[1] - arr[2])
        side_b = np.linalg.norm(arr[0] - arr[2])
        side_c = np.linalg.norm(arr[0] - arr[1])
        perimeter = side_a + side_b + side_c
        incenter = Point(
            float((side_a * a.x + side_b * b.x + side_c * c.x) / perimeter),
            float((side_a * a.y + side_b * b.y + side_c * c.y) / perimeter),
        )

        d = 2 * (a.x * (b.y - c.y) + b.x * (c.y - a.y) + c.x * (a.y - b.y))
        if abs(d) < 1e-9:
            circumcenter = centroid
        else:
            ux = (
                (a.x**2 + a.y**2) * (b.y - c.y)
                + (b.x**2 + b.y**2) * (c.y - a.y)
                + (c.x**2 + c.y**2) * (a.y - b.y)
            ) / d
            uy = (
                (a.x**2 + a.y**2) * (c.x - b.x)
                + (b.x**2 + b.y**2) * (a.x - c.x)
                + (c.x**2 + c.y**2) * (b.x - a.x)
            ) / d
            circumcenter = Point(float(ux), float(uy))

        return {"centroid": centroid, "incenter": incenter, "circumcenter": circumcenter}

    def plot(self, ax, color="tab:green", alpha=1.0):
        if len(self.points) != 3:
            ax.text(0.5, 0.5, "Некорректный треугольник", ha='center', va='center')
            return
        arr = _to_np(self.points)
        triangle = Polygon(arr, fill=False, color=color, linewidth=2, alpha=alpha)
        ax.add_patch(triangle)
        ax.set_aspect('equal')
        ax.autoscale_view()

    def get_details(self):
        if len(self.points) != 3:
            return f"Треугольник: a={self.a}, b={self.b}, c={self.c}\nНекорректные стороны"
        s = (self.a + self.b + self.c) / 2
        area = np.sqrt(s * (s - self.a) * (s - self.b) * (s - self.c))
        perimeter = self.a + self.b + self.c
        return f"Треугольник: a={self.a}, b={self.b}, c={self.c}\nПлощадь={area:.2f}, Периметр={perimeter:.2f}"


class TrianglePointsShape(GeometricShape):
    def __init__(self, points, labels=None):
        self.points = points
        self.labels = labels or ["A", "B", "C"]

    def plot(self, ax, color="tab:green", alpha=1.0):
        arr = _to_np(self.points)
        triangle = Polygon(arr, fill=False, color=color, linewidth=2, alpha=alpha)
        ax.add_patch(triangle)
        ax.set_aspect("equal")
        ax.autoscale_view()

    def get_details(self):
        arr = _to_np(self.points)
        a = np.linalg.norm(arr[1] - arr[2])
        b = np.linalg.norm(arr[0] - arr[2])
        c = np.linalg.norm(arr[0] - arr[1])
        perimeter = a + b + c
        s = perimeter / 2
        area = np.sqrt(max(s * (s - a) * (s - b) * (s - c), 0.0))
        return f"Треугольник по точкам: Площадь={area:.2f}, Периметр={perimeter:.2f}"

    def triangle_centers(self):
        base = TriangleShape(1, 1, 1)
        base.points = self.points
        return base.triangle_centers()

    def transformed(self, transforms):
        return TrianglePointsShape(apply_transformations(self.points, transforms), labels=self.labels)


class LineShape(GeometricShape):
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2

    def plot(self, ax, color="tab:orange", alpha=1.0):
        ax.plot([self.p1.x, self.p2.x], [self.p1.y, self.p2.y], color=color, linewidth=2, alpha=alpha)
        ax.set_aspect("equal")
        ax.autoscale_view()

    def get_details(self):
        length = np.hypot(self.p2.x - self.p1.x, self.p2.y - self.p1.y)
        return f"Прямая через 2 точки, длина отрезка={length:.2f}"

    def transformed(self, transforms):
        p1, p2 = apply_transformations([self.p1, self.p2], transforms)
        return LineShape(p1, p2)


class PolygonShape(GeometricShape):
    def __init__(self, points):
        self.points = points

    def plot(self, ax, color="tab:red", alpha=1.0):
        arr = _to_np(self.points)
        poly = Polygon(arr, fill=False, color=color, linewidth=2, alpha=alpha)
        ax.add_patch(poly)
        ax.set_aspect("equal")
        ax.autoscale_view()

    def get_details(self):
        arr = _to_np(self.points)
        shifted = np.roll(arr, -1, axis=0)
        perimeter = np.linalg.norm(shifted - arr, axis=1).sum()
        area = 0.5 * abs(np.dot(arr[:, 0], shifted[:, 1]) - np.dot(arr[:, 1], shifted[:, 0]))
        return f"Многоугольник: n={len(self.points)}, Площадь={area:.2f}, Периметр={perimeter:.2f}"

    def transformed(self, transforms):
        return PolygonShape(apply_transformations(self.points, transforms))


class RectangleShape(GeometricShape):
    def __init__(self, width, height, center=(0, 0)):
        self.width = width
        self.height = height
        self.center = center

    def plot(self, ax, color="tab:red", alpha=1.0):
        xy = (self.center[0] - self.width / 2, self.center[1] - self.height / 2)
        rect = Rectangle(xy, self.width, self.height, fill=False, color=color, linewidth=2, alpha=alpha)
        ax.add_patch(rect)
        ax.set_aspect('equal')
        ax.set_xlim(self.center[0] - self.width, self.center[0] + self.width)
        ax.set_ylim(self.center[1] - self.height, self.center[1] + self.height)

    def get_details(self):
        area = self.width * self.height
        perimeter = 2 * (self.width + self.height)
        return f"Прямоугольник: {self.width}x{self.height}, Площадь={area:.2f}, Периметр={perimeter:.2f}"


class EllipseShape(GeometricShape):
    def __init__(self, width, height, center=(0, 0)):
        self.width = width
        self.height = height
        self.center = center

    def plot(self, ax, color="tab:purple", alpha=1.0):
        ellipse = Ellipse(self.center, self.width, self.height, fill=False, color=color, linewidth=2, alpha=alpha)
        ax.add_patch(ellipse)
        ax.set_aspect('equal')
        ax.set_xlim(self.center[0] - self.width, self.center[0] + self.width)
        ax.set_ylim(self.center[1] - self.height, self.center[1] + self.height)

    def get_details(self):
        a = self.width / 2
        b = self.height / 2
        h = ((a - b) ** 2) / ((a + b) ** 2) if (a + b) else 0
        perimeter = np.pi * (a + b) * (1 + (3 * h) / (10 + np.sqrt(max(4 - 3 * h, 1e-9))))
        area = np.pi * a * b
        return f"Эллипс: a={a}, b={b}, Площадь={area:.2f}, Периметр≈{perimeter:.2f}"
