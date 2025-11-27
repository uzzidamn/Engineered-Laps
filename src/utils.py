"""
Utility functions for F1 telemetry streaming pipeline
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def calculate_frequency(timestamps: pd.Series) -> float:
    """
    Calculate data frequency (Hz) from timestamp series
    
    Args:
        timestamps: Pandas Series of timestamps (datetime or timedelta)
        
    Returns:
        Frequency in Hz (samples per second)
    """
    if len(timestamps) < 2:
        return 0.0
    
    # Handle timedelta (e.g., FastF1 SessionTime)
    if pd.api.types.is_timedelta64_dtype(timestamps):
        # Calculate time differences directly
        time_diffs = timestamps.diff().dropna()
        # Convert timedelta to seconds
        time_diffs_seconds = time_diffs.dt.total_seconds()
    # Handle datetime
    elif pd.api.types.is_datetime64_any_dtype(timestamps):
        # Calculate time differences
        time_diffs = timestamps.diff().dropna()
        # Convert to seconds
        time_diffs_seconds = time_diffs.dt.total_seconds()
    else:
        # Try to convert to timedelta (e.g., "0 days 01:02:02.950000" format)
        try:
            # Check if it looks like a timedelta string (contains "days" or timedelta format)
            if timestamps.dtype == 'object' and timestamps.astype(str).str.contains('days', na=False).any():
                # Parse timedelta strings
                timestamps = pd.to_timedelta(timestamps)
                time_diffs = timestamps.diff().dropna()
                time_diffs_seconds = time_diffs.dt.total_seconds()
            else:
                # Try to convert to datetime first
                try:
                    timestamps = pd.to_datetime(timestamps)
                    time_diffs = timestamps.diff().dropna()
                    time_diffs_seconds = time_diffs.dt.total_seconds()
                except (TypeError, ValueError):
                    # If datetime fails, try timedelta
                    timestamps = pd.to_timedelta(timestamps)
                    time_diffs = timestamps.diff().dropna()
                    time_diffs_seconds = time_diffs.dt.total_seconds()
        except (TypeError, ValueError) as e:
            logger.error(f"Cannot convert timestamps to datetime or timedelta: {e}")
            return 0.0
    
    # Filter out zeros and outliers (keep only reasonable intervals)
    valid_diffs = time_diffs_seconds[(time_diffs_seconds > 0) & (time_diffs_seconds < 10)]
    
    if len(valid_diffs) == 0:
        return 0.0
    
    # Calculate average interval
    avg_interval = valid_diffs.mean()
    
    # Frequency is 1 / interval
    frequency = 1.0 / avg_interval if avg_interval > 0 else 0.0
    
    logger.info(f"Calculated frequency: {frequency:.2f} Hz (avg interval: {avg_interval*1000:.2f} ms)")
    
    return frequency


def calculate_sleep_intervals(timestamps: pd.Series) -> List[float]:
    """
    Calculate sleep intervals between timestamps for accurate replay
    
    Args:
        timestamps: Pandas Series of timestamps (datetime or timedelta)
        
    Returns:
        List of sleep intervals in seconds
    """
    if len(timestamps) < 2:
        return [0.0]
    
    # Handle timedelta (e.g., FastF1 SessionTime)
    if pd.api.types.is_timedelta64_dtype(timestamps):
        # Calculate time differences directly
        time_diffs = timestamps.diff().dropna()
        # Convert timedelta to seconds
        intervals = time_diffs.dt.total_seconds().tolist()
    # Handle datetime
    elif pd.api.types.is_datetime64_any_dtype(timestamps):
        # Calculate time differences
        time_diffs = timestamps.diff().dropna()
        # Convert to seconds
        intervals = time_diffs.dt.total_seconds().tolist()
    else:
        # Try to convert to timedelta (e.g., "0 days 01:02:02.950000" format)
        try:
            # Check if it looks like a timedelta string (contains "days" or timedelta format)
            if timestamps.dtype == 'object' and timestamps.astype(str).str.contains('days', na=False).any():
                # Parse timedelta strings
                timestamps = pd.to_timedelta(timestamps)
                time_diffs = timestamps.diff().dropna()
                intervals = time_diffs.dt.total_seconds().tolist()
            else:
                # Try to convert to datetime first
                try:
                    timestamps = pd.to_datetime(timestamps)
                    time_diffs = timestamps.diff().dropna()
                    intervals = time_diffs.dt.total_seconds().tolist()
                except (TypeError, ValueError):
                    # If datetime fails, try timedelta
                    timestamps = pd.to_timedelta(timestamps)
                    time_diffs = timestamps.diff().dropna()
                    intervals = time_diffs.dt.total_seconds().tolist()
        except (TypeError, ValueError) as e:
            logger.error(f"Cannot convert timestamps to datetime or timedelta: {e}")
            return [0.0]
    
    # First interval is 0 (no sleep before first message)
    intervals = [0.0] + intervals
    
    return intervals


def validate_data(df: pd.DataFrame, required_columns: List[str]) -> Tuple[bool, str]:
    """
    Validate DataFrame has required columns and data
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if df is None or df.empty:
        return False, "DataFrame is None or empty"
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {missing_columns}"
    
    # Check for null values in required columns
    null_counts = df[required_columns].isnull().sum()
    if null_counts.any():
        return False, f"Null values found in required columns: {null_counts[null_counts > 0].to_dict()}"
    
    return True, "Data validation passed"


def format_timestamp(timestamp: Any) -> str:
    """
    Format timestamp to ISO string
    
    Args:
        timestamp: Timestamp (datetime, string, or pandas Timestamp)
        
    Returns:
        ISO formatted timestamp string
    """
    if isinstance(timestamp, str):
        return timestamp
    elif isinstance(timestamp, pd.Timestamp):
        return timestamp.isoformat()
    elif isinstance(timestamp, datetime):
        return timestamp.isoformat()
    else:
        return str(timestamp)


def log_metrics(metrics: Dict[str, Any], level: str = "INFO"):
    """
    Log performance metrics
    
    Args:
        metrics: Dictionary of metric names and values
        level: Logging level (INFO, DEBUG, WARNING, ERROR)
    """
    log_func = getattr(logger, level.lower(), logger.info)
    
    for metric_name, metric_value in metrics.items():
        if isinstance(metric_value, float):
            log_func(f"{metric_name}: {metric_value:.4f}")
        else:
            log_func(f"{metric_name}: {metric_value}")


def get_telemetry_fields() -> List[str]:
    """
    Get list of relevant telemetry fields to extract
    
    Returns:
        List of field names
    """
    return [
        'Time', 'SessionTime', 'Driver', 'Speed', 'RPM', 
        'Throttle', 'Brake', 'Gear', 'DRS', 'nGear',
        'BrakeTempFL', 'BrakeTempFR', 'BrakeTempRL', 'BrakeTempRR',
        'X', 'Y', 'Z', 'Source', 'Date', 'Status'
    ]


def extract_driver_id(driver_abbreviation: str) -> str:
    """
    Extract driver ID from driver abbreviation
    
    Args:
        driver_abbreviation: Driver abbreviation (e.g., 'VER')
        
    Returns:
        Driver ID
    """
    return driver_abbreviation


def calculate_lap_number(session_time: pd.Series, lap_times: List[float]) -> pd.Series:
    """
    Calculate lap number from session time
    
    Args:
        session_time: Series of session times
        lap_times: List of lap times in seconds
        
    Returns:
        Series of lap numbers
    """
    if not lap_times:
        return pd.Series([1] * len(session_time))
    
    lap_number = pd.Series([1] * len(session_time))
    cumulative_time = 0.0
    
    for lap_idx, lap_time in enumerate(lap_times, start=1):
        cumulative_time += lap_time
        lap_number[session_time <= cumulative_time] = lap_idx
    
    return lap_number

