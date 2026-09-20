"""Run every zero-argument ``test_*`` function in one project test module.

The project intentionally has no pytest runtime dependency in portable builds.
Historically each test file maintained a manual ``__main__`` list; functions
omitted from that list were counted by the PowerShell runner but never run.
This tiny discovery runner keeps the dependency-free workflow while ensuring
that the reported function count is the executed function count.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import runpy
import ast
import sys
import traceback


def discover(module_name: str):
    module = importlib.import_module(module_name)
    tests = [
        value
        for name, value in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and value.__module__ == module.__name__
    ]
    return sorted(tests, key=lambda function: function.__code__.co_firstlineno)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m tools.run_python_test_module tests.test_module", file=sys.stderr)
        return 2
    module_name = sys.argv[1]
    specification = importlib.util.find_spec(module_name)
    if specification and specification.origin:
        source = open(specification.origin, "r", encoding="utf-8-sig").read()
        declared = [
            node.name
            for node in ast.parse(source, filename=specification.origin).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ]
        if not declared:
            runpy.run_module(module_name, run_name="__main__")
            print(f"{module_name}: legacy module assertions passed")
            return 0
    tests = discover(module_name)
    for test in tests:
        signature = inspect.signature(test)
        required = [
            parameter.name
            for parameter in signature.parameters.values()
            if parameter.default is inspect.Parameter.empty
            and parameter.kind
            in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        if required:
            print(f"{module_name}.{test.__name__} requires unsupported fixtures: {required}", file=sys.stderr)
            return 2
        try:
            test()
        except Exception:  # noqa: BLE001 - test runner must report the original stack
            print(f"FAILED: {module_name}.{test.__name__}", file=sys.stderr)
            traceback.print_exc()
            return 1
    print(f"{module_name}: {len(tests)} test functions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
