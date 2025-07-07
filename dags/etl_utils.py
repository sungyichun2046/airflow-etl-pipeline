"""
ETL Utility Functions: (can be reused across different ETL pipelines)

- Detects categorical, date, and possible date columns stored as strings by sampling.
- Unification of dates and cleans string columns (fills missing strings with empty values, and strips spaces.)
- Replaces NaN or empty strings with None, drops full empty columns.
- Deduplicates by address columns and exact duplicates.
- Data types are validated with warnings logged for mismatches.
"""
import logging
from typing import Dict, List, Tuple

import numpy as np

import pandas as pd
import pandas.api.types as ptypes

INPUT_PATH = '../data/listing_raw_technical_test.parquet'
KEY_COLS = ['street', 'houseNumber', 'postalCode', 'city', 'estateType', 'floorNumber']  # Address columns

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def detect_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Detects categorical, date, and possible date columns in the dataframe.

    :param df: Input dataframe.
    :return: Dictionary with lists of detected columns by type.
    """
    category_columns = []
    date_columns = []
    possible_date_columns = []

    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_categorical_dtype(df[col]):
            category_columns.append(col)
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            date_columns.append(col)

    # Check if any string column is actually a date, detect with sample for performance consideration
    for col in category_columns:
        non_null = df[col].dropna()
        if len(non_null) > 0:
            sample = non_null.sample(min(100, len(non_null)), random_state=42)
            try:
                pd.to_datetime(sample, errors='raise')
                possible_date_columns.append(col)
            except ValueError:
                pass

    # Remove possible date columns from category list
    category_columns = [col for col in category_columns if col not in possible_date_columns]

    return {
        'categorical_columns': category_columns,
        'date_columns': date_columns,
        'possible_date_columns': possible_date_columns
    }


def clean_and_standardize(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
    """
    Cleans and standardizes date and string columns.

    :param df: Input dataframe.
    :return: Cleaned dataframe and detected columns.
    """
    df_clean = df.copy()
    detected = detect_columns(df_clean)

    # Step 1: Detect columns
    cat_cols = detected['categorical_columns']
    date_cols = detected['date_columns']
    possible_date_cols = detected['possible_date_columns']

    # Step 2: Standardize date columns
    for col in date_cols + possible_date_cols:
        # Convert to datetime format; invalid parsing results in NaT (missing)
        df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')

    # Step 3: Standardize categorical/string columns
    for col in cat_cols:
        df_clean[col] = fillna_and_strip(df_clean[col])

    return df_clean, detected


def fillna_and_strip(series: pd.Series) -> pd.Series:
    """
    Fills NA values and strips whitespace from string or categorical series.

    :param series: Input pandas series.
    :return: Cleaned series.
    """
    if isinstance(series.dtype, pd.CategoricalDtype):
        if '' not in series.cat.categories:
            series = series.cat.add_categories([''])
        return series.fillna('').str.strip()
    else:
        return series.fillna('').str.strip()


def flexible_validate(df: pd.DataFrame, expected_types_family: Dict[str, str]) -> Dict[str, str]:
    """
    Validates that columns match expected data types.

    :param df: Dataframe to validate.
    :param expected_types_family: Expected type family per column.
    :return: Dictionary of errors.
    """
    errors = {}
    for col, expected_family in expected_types_family.items():
        if col not in df.columns:
            errors[col] = "Column not found"
            continue

        actual_dtype = df[col].dtype

        if expected_family == 'numeric':
            if not ptypes.is_numeric_dtype(actual_dtype):
                errors[col] = "Expected numeric dtype, found %s" % actual_dtype
        elif expected_family == 'datetime':
            if not ptypes.is_datetime64_any_dtype(actual_dtype):
                errors[col] = "Expected datetime dtype, found %s" % actual_dtype
        elif expected_family == 'string':
            if not (ptypes.is_string_dtype(actual_dtype) or ptypes.is_categorical_dtype(actual_dtype)):
                errors[col] = "Expected string or categorical dtype, found %s" % actual_dtype
        else:
            if actual_dtype.name != expected_family:
                errors[col] = "Expected %s, found %s" % (expected_family, actual_dtype)

    return errors


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and deduplicates the dataset, applies standardization, and validates data types.

    :param df: Input dataframe.
    :return: Cleaned dataframe.
    """
    df = df.replace({np.nan: None, '': None})
    # Drop columns that are completely null (all values are NaN)
    df = df.dropna(axis=1, how='all')

    if set(KEY_COLS).issubset(df.columns):
        # If any of the KEY_COLS is fully null, skip address-based deduplication
        if any(df[col].isnull().all() for col in KEY_COLS):
            logging.warning("Skipping address-based deduplication because at least one key column is fully null.")

        else:
            # Remove rows where all address fields are null
            mask_not_all_null = ~df[KEY_COLS].isnull().all(axis=1)
            df = df[mask_not_all_null]
            # Deduplicate based on address
            df = df.drop_duplicates(subset=KEY_COLS, keep='last')
            logging.info("Performed address-based deduplication.")
    # Remove exact duplicate rows
    df = df.drop_duplicates()

    logging.info("Shape after dropping all-null columns and deduplication: %s", df.shape)

    # Unify formats & categories (Standardize dates, strings, categories
    df_clean, detected = clean_and_standardize(df)

    expected_types = {}
    # Save original dtypes as expected types
    for col, dtype in df.dtypes.items():
        if col in detected['possible_date_columns'] or col in detected['date_columns']:
            expected_types[col] = 'datetime'
        elif ptypes.is_numeric_dtype(dtype):
            expected_types[col] = 'numeric'
        elif ptypes.is_string_dtype(dtype) or isinstance(dtype, pd.CategoricalDtype):
            expected_types[col] = 'string'
        else:
            expected_types[col] = dtype.name

    errors = flexible_validate(df_clean, expected_types)
    if errors:
        logging.warning("Data type validation errors found: %s", errors)
    else:
        logging.info("All column types are as expected.")

    return df_clean
