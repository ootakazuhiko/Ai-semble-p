"""
pytest設定ファイル
"""
import pytest
import os
import sys

# テスト実行時のPython path設定
def pytest_configure():
    """pytest設定"""
    # プロジェクトルートをPython pathに追加
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

@pytest.fixture(scope="session")
def project_root():
    """プロジェクトルートディレクトリ"""
    return os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def test_data():
    """テスト用サンプルデータ"""
    return {
        "sample_records": [
            {"id": 1, "name": "Alice", "score": 85},
            {"id": 2, "name": "Bob", "score": 92},
            {"id": 3, "name": "Carol", "score": 78}
        ],
        "sample_text": "This is a sample text for testing NLP functionality.",
        "sample_image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    }