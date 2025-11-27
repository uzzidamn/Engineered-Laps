"""
Cache manager for streaming F1 telemetry data
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import calculate_frequency, validate_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheManager:
    """
    In-memory cache for streaming F1 telemetry data
    Maintains data in memory for efficient row-by-row iteration
    """
    
    def __init__(self):
        """Initialize cache manager"""
        self.data: Optional[pd.DataFrame] = None
        self.frequency: float = 0.0
        self.current_index: int = 0
        self.sleep_intervals: List[float] = []
        
    def load_data(self, file_path: str, format: str = "auto") -> bool:
        """
        Load data from file into cache
        
        Args:
            file_path: Path to CSV or Parquet file
            format: File format ('csv', 'parquet', or 'auto' to detect)
            
        Returns:
            True if successful
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
            
            # Auto-detect format if needed
            if format == "auto":
                if file_path.endswith('.csv'):
                    format = 'csv'
                elif file_path.endswith('.parquet'):
                    format = 'parquet'
                else:
                    logger.error(f"Unknown file format: {file_path}")
                    return False
            
            # Load data
            logger.info(f"Loading data from {file_path} ({format} format)...")
            
            if format == 'csv':
                self.data = pd.read_csv(file_path)
            elif format == 'parquet':
                self.data = pd.read_parquet(file_path, engine='pyarrow')
            else:
                logger.error(f"Unsupported format: {format}")
                return False
            
            logger.info(f"Loaded {len(self.data)} records")
            
            # Reset index
            self.current_index = 0
            
            # Calculate frequency if SessionTime column exists
            if 'SessionTime' in self.data.columns:
                # Convert SessionTime to timedelta if it's a string
                if self.data['SessionTime'].dtype == 'object':
                    try:
                        # Try to parse as timedelta (handles "0 days 01:02:02.950000" format)
                        self.data['SessionTime'] = pd.to_timedelta(self.data['SessionTime'])
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Could not convert SessionTime to timedelta: {e}")
                
                self.frequency = calculate_frequency(self.data['SessionTime'])
                
                # Calculate sleep intervals for accurate replay
                self.sleep_intervals = self._calculate_sleep_intervals()
            else:
                logger.warning("SessionTime column not found, cannot calculate frequency")
                self.frequency = 0.0
                self.sleep_intervals = []
            
            # Validate data
            required_fields = ['SessionTime', 'DriverID', 'Speed']
            is_valid, error_msg = validate_data(self.data, required_fields)
            
            if not is_valid:
                logger.warning(f"Data validation warning: {error_msg}")
            
            logger.info(f"Cache loaded successfully. Frequency: {self.frequency:.2f} Hz")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False
    
    def load_cache(self, file_path: str, format: str = "auto") -> bool:
        """
        Alias for load_data method (for consistency with other components)
        
        Args:
            file_path: Path to CSV or Parquet file
            format: File format ('csv', 'parquet', or 'auto' to detect)
            
        Returns:
            True if successful
        """
        return self.load_data(file_path, format)
    
    def load_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Load data directly from a DataFrame into cache
        
        Args:
            df: DataFrame with telemetry data
            
        Returns:
            True if successful
        """
        try:
            if df is None or df.empty:
                logger.error("DataFrame is None or empty")
                return False
            
            logger.info(f"Loading data from DataFrame ({len(df)} records)...")
            
            # Make a copy to avoid modifying original
            self.data = df.copy()
            
            # Reset index
            self.current_index = 0
            
            # Calculate frequency if SessionTime column exists
            if 'SessionTime' in self.data.columns:
                # Ensure SessionTime is timedelta
                if not pd.api.types.is_timedelta64_dtype(self.data['SessionTime']):
                    try:
                        self.data['SessionTime'] = pd.to_timedelta(self.data['SessionTime'])
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Could not convert SessionTime to timedelta: {e}")
                
                self.frequency = calculate_frequency(self.data['SessionTime'])
                
                # Calculate sleep intervals for accurate replay
                self.sleep_intervals = self._calculate_sleep_intervals()
            else:
                logger.warning("SessionTime column not found, cannot calculate frequency")
                self.frequency = 0.0
                self.sleep_intervals = []
            
            # Validate data
            required_fields = ['SessionTime', 'DriverID', 'Speed']
            is_valid, error_msg = validate_data(self.data, required_fields)
            
            if not is_valid:
                logger.warning(f"Data validation warning: {error_msg}")
            
            logger.info(f"DataFrame loaded successfully. Frequency: {self.frequency:.2f} Hz")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load DataFrame: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _calculate_sleep_intervals(self) -> List[float]:
        """Calculate sleep intervals between timestamps"""
        if self.data is None or 'SessionTime' not in self.data.columns:
            return []
        
        timestamps = self.data['SessionTime']
        
        # Handle timedelta
        if pd.api.types.is_timedelta64_dtype(timestamps):
            # Calculate differences directly
            time_diffs = timestamps.diff().dropna()
            intervals = time_diffs.dt.total_seconds().tolist()
        # Handle datetime
        elif pd.api.types.is_datetime64_any_dtype(timestamps):
            # Calculate differences
            time_diffs = timestamps.diff().dropna()
            intervals = time_diffs.dt.total_seconds().tolist()
        else:
            # Try to convert to timedelta (handles string formats)
            try:
                if timestamps.dtype == 'object' and timestamps.astype(str).str.contains('days', na=False).any():
                    # Parse timedelta strings
                    timestamps = pd.to_timedelta(timestamps)
                else:
                    # Try datetime first, then timedelta
                    try:
                        timestamps = pd.to_datetime(timestamps)
                    except (TypeError, ValueError):
                        timestamps = pd.to_timedelta(timestamps)
                
                time_diffs = timestamps.diff().dropna()
                intervals = time_diffs.dt.total_seconds().tolist()
            except (TypeError, ValueError) as e:
                logger.error(f"Cannot calculate sleep intervals: {e}")
                return [0.0]
        
        # First interval is 0 (no sleep before first message)
        intervals = [0.0] + intervals
        
        return intervals
    
    def get_next_record(self) -> Optional[Dict[str, Any]]:
        """
        Get next record from cache
        
        Returns:
            Dictionary with record data, or None if end of cache
        """
        if self.data is None or self.current_index >= len(self.data):
            return None
        
        record = self.data.iloc[self.current_index].to_dict()
        self.current_index += 1
        
        return record
    
    def get_sleep_interval(self, index: int) -> float:
        """
        Get sleep interval for given index
        
        Args:
            index: Record index
            
        Returns:
            Sleep interval in seconds
        """
        if index < len(self.sleep_intervals):
            return self.sleep_intervals[index]
        return 0.0
    
    def reset(self):
        """Reset cache to beginning"""
        self.current_index = 0
        logger.info("Cache reset to beginning")
    
    def get_frequency(self) -> float:
        """Get data frequency in Hz"""
        return self.frequency
    
    def get_num_records(self) -> int:
        """Get total number of records"""
        return len(self.data) if self.data is not None else 0
    
    def get_current_index(self) -> int:
        """Get current index"""
        return self.current_index
    
    def has_more_records(self) -> bool:
        """Check if more records are available"""
        return self.data is not None and self.current_index < len(self.data)
    
    def get_all_records(self) -> pd.DataFrame:
        """Get all cached records as DataFrame"""
        return self.data.copy() if self.data is not None else pd.DataFrame()
    
    def get_records_by_driver(self, driver_id: str) -> pd.DataFrame:
        """
        Get all records for a specific driver
        
        Args:
            driver_id: Driver abbreviation
            
        Returns:
            DataFrame with driver's records
        """
        if self.data is None:
            return pd.DataFrame()
        
        if 'DriverID' in self.data.columns:
            return self.data[self.data['DriverID'] == driver_id].copy()
        elif 'Driver' in self.data.columns:
            return self.data[self.data['Driver'] == driver_id].copy()
        else:
            logger.warning("DriverID or Driver column not found")
            return pd.DataFrame()
    
    def iterator(self) -> Iterator[Dict[str, Any]]:
        """
        Get iterator over all records
        
        Returns:
            Iterator yielding dictionaries
        """
        if self.data is None:
            return iter([])
        
        for idx, row in self.data.iterrows():
            yield row.to_dict()

