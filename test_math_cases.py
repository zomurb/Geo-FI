
import unittest
import os
import shutil
from parser import parse_input
from visualizer import plot_function, plot_geometry, plot_parametric, plot_polar, plot_3d

class TestMathBot(unittest.TestCase):
    OUTPUT_DIR = "test_output"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.OUTPUT_DIR):
            shutil.rmtree(cls.OUTPUT_DIR)
        os.makedirs(cls.OUTPUT_DIR)

    def run_case(self, input_text, case_id):
        print(f"Running case {case_id}: {input_text}")
        try:
            result = parse_input(input_text)
            self.assertNotEqual(result['type'], 'error', f"Parse error: {result.get('message')}")
            
            img_buffer = None
            if result['type'] == 'function':
                img_buffer = plot_function(result['data'])
            elif result['type'] == 'parametric':
                img_buffer = plot_parametric(result['data'])
            elif result['type'] == 'polar':
                img_buffer = plot_polar(result)
            elif result['type'] == '3d':
                img_buffer = plot_3d(result)
            elif result['type'] == 'geometry':
                img_buffer = plot_geometry(result)
            
            self.assertIsNotNone(img_buffer)
            
            # Save file
            filename = f"{self.OUTPUT_DIR}/case_{case_id}.png"
            with open(filename, "wb") as f:
                f.write(img_buffer.getvalue())
                
        except Exception as e:
            self.fail(f"Exception in case {case_id} ({input_text}): {e}")

    def test_cases(self):
        cases = [
            ("y = x", 1),
            ("y = x^2", 2),
            ("y = x^3 - 3*x", 3),
            ("y = sqrt(x)", 4),
            ("y = |x|", 5),
            ("y = sin(x)", 6),
            ("y = cos(2*x)", 7),
            ("y = tan(x)", 8),
            ("y = sin(x)/x", 9),
            ("y = sin(x) + cos(x)", 10),
            ("y = e^x", 11),
            ("y = ln(x)", 12),
            ("y = ln(x^2 + 1)", 13),
            ("y = 2^x", 14),
            ("y = e^(-x^2)", 15),
            ("y = 1/x", 16),
            ("y = 1/(x-2)", 17),
            ("y = (x^2 - 1)/(x - 1)", 18),
            ("y = (x+1)/(x^2 - 4)", 19),
            ("y = 1/(x^2 + 1)", 20),
            ("{ x, x >= 0; -x, x < 0 }", 21),
            ("{ x^2, |x| < 1; 1, |x| >= 1 }", 22),
            ("x = cos(t), y = sin(t)", 23),
            ("x = t, y = t^2", 24),
            ("y = x*sin(1/x)", 25),
            ("y = sqrt(-x)", 26),
            ("y = ln(-1)", 27), # Should produce empty graph or not crash
            ("y = 1/0", 28),    # Should not crash
            ("y = sin()", 29),  # Parse error expected? Or should handle graceful?
            ("y = x^^2", 30),
            
            # Polar
            ("r = t", 31),
            ("r = 1 - sin(t)", 32),
            ("r = sin(3*t)", 33),
            
            # 3D
            ("z = x^2 + y^2", 34),
            ("z = sin(sqrt(x^2 + y^2))", 35),
            ("z = x * y", 36)
        ]
        
        for text, idx in cases:
            with self.subTest(msg=f"Case {idx}: {text}"):
                print(f"Running case {idx}: {text}")
                # For intentional errors (29), we expect 'type': 'error' or parsing to fail
                if idx == 29:
                    res = parse_input(text)
                    if res['type'] != 'error':
                       # If it parses (empty arg?), let's see if it plots
                       pass
                    continue 

                self.run_case(text, idx)

if __name__ == '__main__':
    unittest.main()
