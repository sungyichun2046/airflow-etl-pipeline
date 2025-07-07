"""
Test suite for ETL utility functions.

Covers:
- Column type detection
- Data cleaning and unification
- Data validation
- Deduplication logic
- Data type mismatch detection
"""

import numpy as np

import pandas as pd
from dags.etl_utils import (clean_and_standardize, clean_data, detect_columns,
                            flexible_validate)


def test_detect_columns() -> None:
    """
    Test the detect_columns function to ensure proper identification of string, date, and possible date columns.
    """
    df = pd.DataFrame({
        'string_col': ['a', 'b', 'c'],
        'date_col': pd.date_range('2024-01-01', periods=3),
        'possible_date': ['2023-01-01', '2024-01-01', '2021-01-04'],
        'num_col': [1, 2, 3]
    })

    result = detect_columns(df)

    # Ensure string_col is detected correctly
    assert 'string_col' in result['categorical_columns']
    # Ensure date_col is detected correctly
    assert 'date_col' in result['date_columns']
    # Ensure possible_date is correctly excluded from categorical and included in possible date columns
    assert 'possible_date' not in result['categorical_columns']
    assert 'possible_date' in result['possible_date_columns']


def test_clean_and_standardize() -> None:
    """
    Test that string columns are cleaned and possible date columns are correctly converted.
    """
    df = pd.DataFrame({
        'dirty_string': ['  a  ', 'city ', ' Paris', ' '],
        'date_string': ['2023-01-01', '2025-07-11', '2024-08-10', '2024-01-01']
    })

    cleaned_df, detected = clean_and_standardize(df)

    # Check string cleaning
    assert cleaned_df['dirty_string'].tolist() == ['a', 'city', 'Paris', '']

    # Check detected types
    assert 'dirty_string' in detected['categorical_columns']
    assert 'date_string' in detected['possible_date_columns']


def test_flexible_validate() -> None:
    """
    Test the flexible_validate function to ensure correct validation of expected data types.
    """
    df = pd.DataFrame({
        'num_col': [1, 2, 3],
        'date_col': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']),
        'str_col': ['a', 'b', 'c']
    })

    expected_types = {
        'num_col': 'numeric',
        'date_col': 'datetime',
        'str_col': 'string'
    }

    errors = flexible_validate(df, expected_types)
    assert errors == {}


def test_flexible_validate_with_errors() -> None:
    """
    Test flexible_validate to ensure it correctly identifies data type mismatches.
    """
    df = pd.DataFrame({
        'num_col': ['not_a_number', 'test', 'example'],  # Wrong type
        'date_col': ['not_a_date', 'another_string', 'random'],  # Wrong type
        'str_col': ['a', 'b', 'c']
    })

    expected_types = {
        'num_col': 'numeric',
        'date_col': 'datetime',
        'str_col': 'string'
    }

    errors = flexible_validate(df, expected_types)

    assert 'num_col' in errors
    assert 'date_col' in errors
    assert 'str_col' not in errors


def test_clean_data() -> None:
    """
    Test clean_data to verify deduplication based on address and removal of null-only rows.
    """
    df = pd.DataFrame({
        'street': ['Main', None, 'Main', None],
        'houseNumber': ['1', None, '1', None],
        'postalCode': ['1000', None, '1000', None],
        'city': ['City', None, 'City', None],
        'estateType': ['Flat', None, 'Flat', None],
        'floorNumber': [np.nan, None, np.nan, None],
        'num_col': [1, 2, 1, None]
    })

    cleaned_df = clean_data(df)

    # Should deduplicate by address and remove null-only rows
    assert cleaned_df.shape[1] == 6
    assert not cleaned_df.isnull().all().any()  # No all-null columns


def test_clean_data_with_all_null_address() -> None:
    """
    Test clean_data when all address columns are null.
    Deduplication based on address should be skipped.
    """
    df = pd.DataFrame({
        'street': [None, None],
        'houseNumber': [None, None],
        'postalCode': [None, None],
        'city': [None, None],
        'estateType': [None, None],
        'floorNumber': [None, None],
        'num_col': [1, 2]
    })

    cleaned_df = clean_data(df)

    # All-null address columns => no deduplication by address
    assert len(cleaned_df) == 2  # No rows should be dropped


def test_clean_data_type_errors_detection() -> None:
    """
    Test clean_data with intentional type mismatches to verify detection of data type errors.
    """
    df = pd.DataFrame({
        'order_date': ['2023-01-01', 'not_a_date', '2023-03-01'],  # should be datetime
        'price': ['100', '200', 'invalid'],  # should be numeric
        'customer_id': [1.0, 2.0, 3.0],  # should be int64
        'category': pd.Series(['A', 'B', 'C'], dtype="category"),  # category is acceptable
        'quantity': [10, 20, 30],  # correct type
        # 'notes' column is missing to trigger "Column not found"
    })

    cleaned_df = clean_data(df)

    # Run flexible_validate manually to check for expected errors
    expected_types = {
        'order_date': 'datetime',
        'price': 'numeric',
        'customer_id': 'int64',
        'category': 'string',
        'quantity': 'numeric',
        'notes': 'string'  # Missing on purpose
    }
    errors = flexible_validate(cleaned_df, expected_types)

    # Assertions to verify each expected error
    assert 'order_date' in errors
    assert 'price' in errors
    assert 'customer_id' in errors
    assert 'notes' in errors

    # Check the error messages
    assert "Expected datetime" in errors['order_date']
    assert "Expected numeric" in errors['price']
    assert "Expected int64" in errors['customer_id']
    assert errors['notes'] == "Column not found"

    # Ensure no errors for correct columns
    assert 'category' not in errors
    assert 'quantity' not in errors
