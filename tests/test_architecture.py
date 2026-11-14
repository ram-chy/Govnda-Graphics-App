"""Import-boundary and financial-safety checks from ARCHITECTURE.md §4.1."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "app"

FORBIDDEN_DOMAIN_MODULES = {
    "PySide6",
    "shiboken6",
    "sqlalchemy",
    "alembic",
    "sqlite3",
    "app.ui",
    "app.infrastructure",
    "app.services",
    "app.repositories",
}
FORBIDDEN_CORE_MODULES = {"PySide6", "shiboken6", "sqlalchemy", "alembic", "sqlite3"}


def _python_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*.py") if "__pycache__" not in path.parts)


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module)
    return roots


def _matches_forbidden(imported: str, forbidden: set[str]) -> bool:
    return any(imported == item or imported.startswith(f"{item}.") for item in forbidden)


def test_domain_has_no_framework_or_io_imports() -> None:
    violations: list[str] = []
    for path in _python_files(APP_ROOT / "domain"):
        for imported in _imported_roots(path):
            if _matches_forbidden(imported, FORBIDDEN_DOMAIN_MODULES):
                violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")
    assert violations == []


def test_core_has_no_qt_or_database_imports() -> None:
    violations: list[str] = []
    for path in _python_files(APP_ROOT / "core"):
        for imported in _imported_roots(path):
            if _matches_forbidden(imported, FORBIDDEN_CORE_MODULES):
                violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")
    assert violations == []


def test_viewmodels_do_not_import_qtwidgets() -> None:
    violations: list[str] = []
    for path in _python_files(APP_ROOT / "ui" / "viewmodels"):
        for imported in _imported_roots(path):
            if imported.startswith("PySide6.QtWidgets"):
                violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")
    assert violations == []


def test_infrastructure_has_no_qt_or_ui_imports() -> None:
    forbidden = {"PySide6", "shiboken6", "app.ui"}
    violations: list[str] = []
    for path in _python_files(APP_ROOT / "infrastructure"):
        for imported in _imported_roots(path):
            if _matches_forbidden(imported, forbidden):
                violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")
    assert violations == []


def test_services_have_no_qt_or_ui_imports() -> None:
    forbidden = {"PySide6", "shiboken6", "app.ui"}
    violations: list[str] = []
    for path in _python_files(APP_ROOT / "services"):
        for imported in _imported_roots(path):
            if _matches_forbidden(imported, forbidden):
                violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")
    assert violations == []


def test_tools_have_no_qt_imports() -> None:
    forbidden = {"PySide6", "shiboken6"}
    violations: list[str] = []
    for path in _python_files(APP_ROOT / "tools"):
        for imported in _imported_roots(path):
            if _matches_forbidden(imported, forbidden):
                violations.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")
    assert violations == []


def test_production_code_never_creates_tables_implicitly() -> None:
    violations: list[str] = []
    for path in _python_files(APP_ROOT):
        source = path.read_text(encoding="utf-8")
        if ".create_all(" in source:
            violations.append(str(path.relative_to(PROJECT_ROOT)))
    assert violations == []


def test_financial_modules_do_not_call_float() -> None:
    financial_paths = [
        *(_python_files(APP_ROOT / "domain")),
        APP_ROOT / "core" / "formatting.py",
    ]
    violations: list[str] = []
    for path in financial_paths:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "float"
            ):
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{node.lineno}")
    assert violations == []


def test_all_application_modules_compile() -> None:
    for path in _python_files(APP_ROOT):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")


def test_application_package_exists() -> None:
    assert (APP_ROOT / "main.py").is_file()
    assert (APP_ROOT / "core" / "config.py").is_file()
    assert (APP_ROOT / "domain" / "value_objects" / "currency.py").is_file()
