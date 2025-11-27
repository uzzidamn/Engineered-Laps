"""
Data preparation module for F1 telemetry extraction and export
"""

import os
import sys
import pandas as pd
import numpy as np
import yaml
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import fastf1
except ImportError:
    print("FastF1 not installed. Install with: pip install fastf1")
    sys.exit(1)

from src.utils import (
    calculate_frequency, 
    validate_data, 
    get_telemetry_fields,
    extract_driver_id
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise


def load_fastf1_session(year: int, grand_prix: str, session: str, cache_dir: str = None) -> Any:
    """
    Load F1 session data from FastF1
    
    Args:
        year: F1 season year
        grand_prix: Grand Prix name
        session: Session type (Practice1, Practice2, Practice3, Qualifying, Race)
        cache_dir: Directory for FastF1 cache (optional)
        
    Returns:
        FastF1 session object
    """
    try:
        # Enable cache if directory provided
        if cache_dir:
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
            fastf1.Cache.enable_cache(cache_dir)
        
        logger.info(f"Loading {year} {grand_prix} {session}...")
        session_obj = fastf1.get_session(year, grand_prix, session)
        session_obj.load()
        
        logger.info(f"Session loaded successfully")
        return session_obj
        
    except Exception as e:
        logger.error(f"Failed to load session: {e}")
        raise


def _merge_lap_data_to_telemetry(telemetry: pd.DataFrame, driver_laps: pd.DataFrame) -> pd.DataFrame:
    """
    Merge lap-level data into telemetry DataFrame
    
    Args:
        telemetry: Telemetry DataFrame
        driver_laps: Laps DataFrame for driver
        
    Returns:
        Telemetry DataFrame with merged lap fields
    """
    if telemetry.empty or driver_laps.empty:
        return telemetry
    
    # Lap fields to merge
    lap_fields = [
        'LapNumber', 'LapTime', 'Sector1Time', 'Sector2Time', 'Sector3Time',
        'Sector1SessionTime', 'Sector2SessionTime', 'Sector3SessionTime',
        'LapStartTime', 'LapStartDate', 'Time',
        'PitOutTime', 'PitInTime', 'IsPersonalBest',
        'Compound', 'TyreLife', 'FreshTyre', 'Stint',
        'TrackStatus', 'Position', 'Deleted', 'DeletedReason'
    ]
    
    # Initialize columns with NaN
    for field in lap_fields:
        if field not in telemetry.columns:
            telemetry[field] = np.nan
    
    # Merge lap data for each lap
    for _, lap in driver_laps.iterrows():
        lap_start = lap.get('LapStartTime')
        lap_end = lap.get('Time')
        
        if pd.isna(lap_start) or pd.isna(lap_end):
            continue
        
        # Find telemetry points within this lap
        lap_mask = (
            (telemetry['SessionTime'] >= lap_start) & 
            (telemetry['SessionTime'] <= lap_end)
        )
        
        if not lap_mask.any():
            continue
        
        # Fill lap fields for this lap's telemetry
        for field in lap_fields:
            if field in lap.index:
                value = lap[field]
                if pd.notna(value):
                    # Handle timedelta columns - store both original and seconds version
                    try:
                        if pd.api.types.is_timedelta64_dtype(type(value)) or isinstance(value, pd.Timedelta):
                            # Store as seconds for CSV compatibility
                            telemetry.loc[lap_mask, f'{field}_seconds'] = pd.Timedelta(value).total_seconds()
                            # Also keep original if possible
                            telemetry.loc[lap_mask, field] = value
                        else:
                            telemetry.loc[lap_mask, field] = value
                    except (TypeError, ValueError):
                        # If conversion fails, just store the value as-is
                        telemetry.loc[lap_mask, field] = value
    
    return telemetry


def _merge_weather_data(telemetry: pd.DataFrame, session_obj: Any) -> pd.DataFrame:
    """
    Merge weather data with telemetry based on SessionTime
    
    Args:
        telemetry: Telemetry DataFrame
        session_obj: FastF1 session object
        
    Returns:
        Telemetry DataFrame with merged weather fields
    """
    try:
        weather_data = session_obj.weather_data
        
        if weather_data is None or weather_data.empty:
            logger.warning("No weather data available")
            return telemetry
        
        # Prepare weather DataFrame for merging
        weather_df = pd.DataFrame(weather_data)
        
        # Convert timedelta to seconds for easier merging
        if 'SessionTime' in weather_df.columns:
            weather_df['SessionTime_seconds'] = pd.to_timedelta(weather_df['SessionTime']).dt.total_seconds()
        
        if 'SessionTime' in telemetry.columns:
            telemetry['SessionTime_seconds'] = pd.to_timedelta(telemetry['SessionTime']).dt.total_seconds()
        
        # Weather fields to merge
        weather_fields = ['AirTemp', 'Humidity', 'Pressure', 'TrackTemp', 
                         'WindSpeed', 'WindDirection']
        
        # Merge using nearest time match (asof merge)
        telemetry = telemetry.sort_values('SessionTime_seconds')
        weather_df = weather_df.sort_values('SessionTime_seconds')
        
        # Merge weather data
        weather_cols = ['SessionTime_seconds'] + [f for f in weather_fields if f in weather_df.columns]
        telemetry = pd.merge_asof(
            telemetry,
            weather_df[weather_cols],
            on='SessionTime_seconds',
            direction='nearest',
            tolerance=1.0  # 1 second tolerance (in seconds)
        )
        
        # Clean up temporary column
        if 'SessionTime_seconds' in telemetry.columns:
            telemetry = telemetry.drop(columns=['SessionTime_seconds'])
        
        logger.info(f"Merged weather data: {len([f for f in weather_fields if f in telemetry.columns])} fields")
        
    except Exception as e:
        logger.warning(f"Error merging weather data: {e}")
    
    return telemetry


def _merge_driver_and_session_info(telemetry: pd.DataFrame, session_obj: Any) -> pd.DataFrame:
    """
    Merge driver info and session results with telemetry
    
    Args:
        telemetry: Telemetry DataFrame
        session_obj: FastF1 session object
        
    Returns:
        Telemetry DataFrame with merged driver/session fields
    """
    try:
        # Get driver info and session results
        results = session_obj.results
        
        if results is None or results.empty:
            logger.warning("No session results available")
            return telemetry
        
        # Create driver mapping DataFrame with available fields
        driver_map_data = {}
        
        # Check each field and add if available
        result_fields = [
            ('DriverNumber', 'DriverNumber'),
            ('FullName', 'FullName'),
            ('FirstName', 'FirstName'),
            ('LastName', 'LastName'),
            ('TeamName', 'TeamName'),
            ('GridPosition', 'GridPosition'),
            ('Position', 'Position'),
            ('Points', 'Points'),
            ('Status', 'Status'),
            ('Q1', 'Q1'),
            ('Q2', 'Q2'),
            ('Q3', 'Q3'),
            ('FastestLapTime', 'FastestLapTime'),
            ('FastestLapSpeed', 'FastestLapSpeed'),
        ]
        
        for source_field, target_field in result_fields:
            if source_field in results.columns:
                driver_map_data[target_field] = results[source_field].values
        
        if not driver_map_data:
            logger.warning("No driver/session fields available for merging")
            return telemetry
        
        # Use Abbreviation as DriverID for merging (matches telemetry DriverID)
        if 'Abbreviation' in results.columns:
            driver_map_data['DriverID'] = results['Abbreviation'].values
        elif 'DriverNumber' in results.columns:
            driver_map_data['DriverID'] = results['DriverNumber'].astype(str).values
        else:
            logger.warning("No driver identifier found for merging")
            return telemetry
        
        # Create driver mapping DataFrame
        driver_map = pd.DataFrame(driver_map_data)
        
        if 'DriverID' in telemetry.columns and not driver_map.empty and 'DriverID' in driver_map.columns:
            # Merge driver info
            telemetry = telemetry.merge(driver_map, on='DriverID', how='left')
            merged_fields = len([c for c in driver_map.columns if c != 'DriverID'])
            logger.info(f"Merged driver/session info: {merged_fields} fields")
        
    except Exception as e:
        logger.warning(f"Error merging driver/session info: {e}")
    
    return telemetry


def extract_telemetry_fields(session_obj: Any, driver: str = None) -> pd.DataFrame:
    """
    Extract relevant telemetry fields from FastF1 session
    
    Args:
        session_obj: FastF1 session object
        driver: Driver abbreviation (optional, if None extracts all drivers)
        
    Returns:
        DataFrame with telemetry data
    """
    try:
        all_data = []
        
        # Get all drivers if not specified
        if driver:
            drivers = [driver]
        else:
            drivers = session_obj.results['Abbreviation'].tolist()
        
        logger.info(f"Extracting telemetry for {len(drivers)} drivers")
        
        for drv in drivers:
            try:
                # Get driver laps
                driver_laps = session_obj.laps.pick_driver(drv)
                
                if driver_laps.empty:
                    logger.warning(f"No laps found for driver {drv}")
                    continue
                
                # Get telemetry (includes all car_data fields)
                telemetry = driver_laps.get_telemetry()
                
                if telemetry.empty:
                    logger.warning(f"No telemetry found for driver {drv}")
                    continue
                
                # Add driver abbreviation
                telemetry['DriverID'] = drv
                telemetry['Driver'] = drv
                
                # Merge all lap-level data (tire fields, lap times, etc.)
                telemetry = _merge_lap_data_to_telemetry(telemetry, driver_laps)
                
                all_data.append(telemetry)
                logger.info(f"Extracted {len(telemetry)} data points for driver {drv}")
                
            except Exception as e:
                logger.warning(f"Error extracting telemetry for driver {drv}: {e}")
                continue
        
        if not all_data:
            logger.error("No telemetry data extracted")
            return pd.DataFrame()
        
        # Combine all drivers
        combined_data = pd.concat(all_data, ignore_index=True)
        
        # Sort by SessionTime
        combined_data = combined_data.sort_values('SessionTime').reset_index(drop=True)
        
        # Merge weather data (applies to all drivers)
        combined_data = _merge_weather_data(combined_data, session_obj)
        
        # Merge driver and session info
        combined_data = _merge_driver_and_session_info(combined_data, session_obj)
        
        logger.info(f"Total telemetry data points: {len(combined_data)}")
        logger.info(f"Total columns: {len(combined_data.columns)}")
        logger.info(f"Columns: {list(combined_data.columns)}")
        
        return combined_data
        
    except Exception as e:
        logger.error(f"Error extracting telemetry fields: {e}")
        raise


def export_to_csv(df: pd.DataFrame, output_path: str) -> bool:
    """
    Export DataFrame to CSV file
    
    Args:
        df: DataFrame to export
        output_path: Output file path
        
    Returns:
        True if successful
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create a copy to avoid modifying original dataframe
        df_export = df.copy()
        
        # Convert timedelta columns to total_seconds for CSV compatibility
        for col in df_export.columns:
            if pd.api.types.is_timedelta64_dtype(df_export[col]):
                # Convert timedelta to float (seconds)
                df_export[col] = df_export[col].dt.total_seconds()
                logger.debug(f"Converted timedelta column {col} to seconds for CSV export")
            elif pd.api.types.is_datetime64_any_dtype(df_export[col]):
                # Convert datetime to ISO string format
                df_export[col] = df_export[col].dt.strftime('%Y-%m-%d %H:%M:%S.%f')
                logger.debug(f"Converted datetime column {col} to string for CSV export")
        
        # Handle any remaining complex types
        for col in df_export.columns:
            if df_export[col].dtype == 'object':
                # Try to convert any remaining timedelta-like objects
                try:
                    sample_val = df_export[col].dropna().iloc[0] if not df_export[col].dropna().empty else None
                    if isinstance(sample_val, pd.Timedelta):
                        df_export[col] = pd.to_timedelta(df_export[col]).dt.total_seconds()
                except:
                    pass  # Not a timedelta, keep as is
        
        # Export to CSV
        df_export.to_csv(output_path, index=False)
        
        logger.info(f"Exported {len(df)} rows, {len(df.columns)} columns to CSV: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def export_to_parquet(df: pd.DataFrame, output_path: str) -> bool:
    """
    Export DataFrame to Parquet file
    
    Args:
        df: DataFrame to export
        output_path: Output file path
        
    Returns:
        True if successful
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create a copy to avoid modifying original dataframe
        df_export = df.copy()
        
        # Convert timedelta columns to total_seconds for better parquet compatibility
        for col in df_export.columns:
            if pd.api.types.is_timedelta64_dtype(df_export[col]):
                # Convert timedelta to float (seconds) for parquet compatibility
                df_export[col] = df_export[col].dt.total_seconds()
                logger.debug(f"Converted timedelta column {col} to seconds for parquet export")
        
        # Export to Parquet with explicit engine
        df_export.to_parquet(output_path, index=False, engine='pyarrow')
        
        logger.info(f"Exported {len(df)} rows to Parquet: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export Parquet: {e}")
        return False


def prepare_data(year: int = None, grand_prix: str = None, session: str = None, 
                 config_path: str = "config/config.yaml", output_format: str = "both") -> Dict[str, Any]:
    """
    Complete data preparation pipeline
    
    Args:
        year: F1 season year (optional, uses config if None)
        grand_prix: Grand Prix name (optional, uses config if None)
        session: Session type (optional, uses config if None)
        config_path: Path to config file
        output_format: Output format ('csv', 'parquet', or 'both')
        
    Returns:
        Dictionary with results and metadata
    """
    try:
        # Load config
        config = load_config(config_path)
        race_config = config.get('race', {})
        data_config = config.get('data', {})
        
        # Use config values if not provided
        year = year or race_config.get('year', 2023)
        grand_prix = grand_prix or race_config.get('grand_prix', 'Monaco')
        session = session or race_config.get('session', 'Race')
        data_dir = data_config.get('data_dir', 'data/')
        
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{year}_{grand_prix}_{session}_{timestamp}"
        
        # Load session
        session_obj = load_fastf1_session(year, grand_prix, session)
        
        # Extract telemetry
        df = extract_telemetry_fields(session_obj)
        
        if df.empty:
            return {
                'success': False,
                'error': 'No telemetry data extracted'
            }
        
        # Calculate frequency
        if 'SessionTime' in df.columns:
            frequency = calculate_frequency(df['SessionTime'])
        else:
            frequency = 0.0
            logger.warning("Cannot calculate frequency: SessionTime column not found")
        
        # Validate data
        required_fields = ['SessionTime', 'DriverID', 'Speed']
        is_valid, error_msg = validate_data(df, required_fields)
        
        if not is_valid:
            return {
                'success': False,
                'error': error_msg
            }
        
        # Export data
        results = {
            'success': True,
            'dataframe': df,
            'frequency_hz': frequency,
            'num_records': len(df),
            'drivers': df['DriverID'].unique().tolist() if 'DriverID' in df.columns else [],
            'files': []
        }
        
        if output_format in ['csv', 'both']:
            csv_path = os.path.join(data_dir, f"{base_filename}.csv")
            if export_to_csv(df, csv_path):
                results['files'].append(csv_path)
        
        if output_format in ['parquet', 'both']:
            parquet_path = os.path.join(data_dir, f"{base_filename}.parquet")
            if export_to_parquet(df, parquet_path):
                results['files'].append(parquet_path)
        
        return results
        
    except Exception as e:
        logger.error(f"Data preparation failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }

