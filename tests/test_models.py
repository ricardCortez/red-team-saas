import pytest

def test_imports():
    from app.models import User, Task, Result
    assert User is not None

def test_env_exists():
    import os
    assert os.path.exists(".env")
