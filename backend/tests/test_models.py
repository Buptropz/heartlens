import pytest

def test_can_import_report_model():
    from models.report import Report
    assert Report.__tablename__ == "reports"
