"""
Data Processor テスト
"""
import pytest
import numpy as np
import pandas as pd
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../containers/data-processor/src'))

from processor_service import analyze_data, transform_data, aggregate_data

@pytest.mark.asyncio
async def test_analyze_data():
    """データ分析機能のテスト"""
    test_data = {
        "records": [
            {"name": "Alice", "age": 25, "score": 85},
            {"name": "Bob", "age": 30, "score": 92},
            {"name": "Carol", "age": 28, "score": 78}
        ]
    }
    
    result = await analyze_data(test_data, {})
    
    assert "shape" in result
    assert result["shape"] == [3, 3]
    assert "numeric_summary" in result
    assert "missing_values" in result
    assert result["rows_processed"] == 3

@pytest.mark.asyncio
async def test_transform_data():
    """データ変換機能のテスト"""
    test_data = {
        "records": [
            {"name": "Alice", "age": 25, "score": 85},
            {"name": "Bob", "age": 30, "score": 92},
            {"name": "Carol", "age": 28, "score": 78}
        ]
    }
    
    options = {"columns": ["name", "age"]}
    result = await transform_data(test_data, options)
    
    assert "transformed_data" in result
    assert result["rows_processed"] == 3
    # Should only have name and age columns
    for record in result["transformed_data"]:
        assert len(record) == 2
        assert "name" in record
        assert "age" in record

@pytest.mark.asyncio
async def test_aggregate_data():
    """データ集約機能のテスト"""
    test_data = {
        "records": [
            {"category": "A", "value": 10},
            {"category": "A", "value": 20},
            {"category": "B", "value": 15},
            {"category": "B", "value": 25}
        ]
    }
    
    options = {
        "group_by": ["category"],
        "agg_funcs": {"value": "mean"}
    }
    
    result = await aggregate_data(test_data, options)
    
    assert "aggregated_data" in result
    assert result["rows_processed"] == 4