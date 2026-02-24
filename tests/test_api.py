"""
tests/test_api.py — Basic API tests
"""
import pytest
from fastapi.testclient import TestClient
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.api import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_invalid_file_type():
    response = client.post(
        "/extract/pdf",
        files={"file": ("test.txt", b"hello", "text/plain")}
    )
    assert response.status_code == 200
    assert "error" in response.json()


def test_invalid_image_type():
    response = client.post(
        "/extract/image",
        files={"file": ("test.pdf", b"fake", "application/pdf")}
    )
    assert response.status_code == 200
    assert "error" in response.json()