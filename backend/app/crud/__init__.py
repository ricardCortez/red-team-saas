"""CRUD operations package"""
from app.crud.project import crud_project
from app.crud.scan import crud_scan
from app.crud.result import crud_result
from app.crud.report import crud_report

__all__ = ["crud_project", "crud_scan", "crud_result", "crud_report"]
