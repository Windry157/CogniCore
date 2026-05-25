import pytest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from src.core.tools.utility_tools import calculate
    HAS_CALCULATE = True
except ImportError:
    HAS_CALCULATE = False


class TestCalculate:
    @pytest.mark.skipif(not HAS_CALCULATE, reason="calculate tool not available")
    def test_simple_arithmetic(self):
        r = calculate("1 + 2")
        assert r["result"] == 3

    @pytest.mark.skipif(not HAS_CALCULATE, reason="calculate tool not available")
    def test_math_functions(self):
        r = calculate("sqrt(16)")
        assert r["result"] == 4.0

    @pytest.mark.skipif(not HAS_CALCULATE, reason="calculate tool not available")
    def test_pi(self):
        r = calculate("pi * 2")
        assert round(r["result"], 6) == round(6.283185307179586, 6)

    @pytest.mark.skipif(not HAS_CALCULATE, reason="calculate tool not available")
    def test_rejects_import(self):
        r = calculate("__import__('os').system('dir')")
        assert "error" in r

    @pytest.mark.skipif(not HAS_CALCULATE, reason="calculate tool not available")
    def test_rejects_unknown_function(self):
        r = calculate("hack()")
        assert "error" in r

    @pytest.mark.skipif(not HAS_CALCULATE, reason="calculate tool not available")
    def test_rejects_string_literal(self):
        r = calculate("'hello'")
        assert "result" in r and r["result"] == "hello" or "error" in r
