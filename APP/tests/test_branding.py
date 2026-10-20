"""Regression checks for explicit native and shortcut branding."""
import ast
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]

class BrandingTests(unittest.TestCase):
    def test_multiresolution_icon(self):
        with Image.open(ROOT/'APP/desktop/branding/paddy.ico') as icon:
            self.assertEqual(icon.format,'ICO')
            sizes=icon.ico.sizes()
            for side in (16,32,48,256):
                self.assertIn((side,side),sizes)
                self.assertIsNotNone(icon.ico.getimage((side,side)).convert('RGBA').getbbox())

    def test_native_explicit_icon(self):
        source=(ROOT/'APP/desktop/main.py').read_text()
        tree=ast.parse(source)
        starts=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='start']
        self.assertEqual(len(starts),1)
        self.assertIn('icon',{k.arg for k in starts[0].keywords})
        self.assertLess(source.index("SetCurrentProcessExplicitAppUserModelID"),source.index('import webview'))

    def test_packaging_and_shortcuts(self):
        source=(ROOT/'APP/desktop/build.py').read_text()
        self.assertIn("shutil.copy2(icon,stage/'assets/paddy.ico')",source)
        installer=(ROOT/'APP/desktop/installer.iss').read_text()
        shortcuts=[line for line in installer.splitlines() if line.startswith('Name: "{auto')]
        self.assertEqual(len(shortcuts),2)
        for line in shortcuts:
            self.assertIn('IconFilename: "{app}\\_internal\\site\\assets\\paddy.ico"',line)
            self.assertIn('AppUserModelID: "Paddy.Desktop.1"',line)

if __name__=='__main__':unittest.main()
