"""
Kafka producer for real-time F1 telemetry streaming at FastF1 frequency
"""

import os
import sys
import json
import time
import yaml
import logging
import pandas as pd
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from kafka import KafkaProducer
except ImportError:
    print("kafka-python not installed. Install with: pip install kafka-python")
    sys.exit(1)

from src.cache_manager import CacheManager
from src.utils import calculate_sleep_intervals
from src.kafka_utils import (
    get_topic_name, generate_message_key, get_partition_for_severity,
    get_partition_for_model_type, create_all_topics
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealTimeProducer:
    """
    Kafka producer that streams F1 telemetry at exact FastF1 frequency
    Preserves original timestamp spacing for accurate replay
    """
    
    def __init__(self, config_path: str = "config/config.yaml", driver_ids: Optional[List[str]] = None):
        """
        Initialize real-time producer
        
        Args:
            config_path: Path to configuration file
            driver_ids: List of driver IDs to stream (None for all drivers)
        """
        self.config = self._load_config(config_path)
        self.producer = None
        self.cache_manager = CacheManager()
        self.message_count = 0
        self.start_time = None
        self.driver_ids = driver_ids  # Filter by driver IDs if specified
        self.cache_loading = False
        self.cache_loaded = False
        self.cache_lock = threading.Lock()
        # Alert generation state
        self.previous_drs_state = {}  # Track DRS state per driver for change detection
        self.enable_alerts = True  # Flag to enable/disable alert generation
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            raise
    
    def _setup_kafka_producer(self):
        """Setup Kafka producer connection"""
        try:
            kafka_config = self.config.get('kafka', {})
            bootstrap_servers = kafka_config.get('bootstrap_servers', 'localhost:9092')
            
            # Create topics if they don't exist
            try:
                create_all_topics(config=self.config)
            except Exception as e:
                logger.warning(f"Could not create topics (they may already exist): {e}")
            
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                batch_size=16384,
                linger_ms=10,
                compression_type='gzip'
            )
            
            logger.info(f"Connected to Kafka at {bootstrap_servers}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def load_cache(self, file_path: str, format: str = "auto") -> bool:
        """
        Load data cache from file
        
        Args:
            file_path: Path to CSV or Parquet file
            format: File format ('csv', 'parquet', or 'auto')
            
        Returns:
            True if successful
        """
        result = self.cache_manager.load_data(file_path, format)
        if result:
            with self.cache_lock:
                self.cache_loaded = True
        return result
    
    def load_cache_background(self, file_path: str, format: str = "auto"):
        """
        Load cache in background thread
        
        Args:
            file_path: Path to CSV or Parquet file
            format: File format ('csv', 'parquet', or 'auto')
        """
        def _load():
            with self.cache_lock:
                self.cache_loading = True
            try:
                logger.info(f"Background loading cache from {file_path}...")
                result = self.load_cache(file_path, format)
                if result:
                    logger.info("✅ Background cache loading completed")
                else:
                    logger.error("❌ Background cache loading failed")
            except Exception as e:
                logger.error(f"Error in background cache loading: {e}")
            finally:
                with self.cache_lock:
                    self.cache_loading = False
        
        thread = threading.Thread(target=_load, daemon=True)
        thread.start()
        return thread
    
    def _create_message(self, record: Dict[str, Any], message_type: str = 'telemetry') -> Dict[str, Any]:
        """
        Create Kafka message from record
        
        Args:
            record: Data record dictionary
            message_type: Type of message ('telemetry', 'alert', 'prediction')
            
        Returns:
            Formatted message dictionary
        """
        driver_id = record.get('DriverID') or record.get('Driver', 'UNKNOWN')
        
        # Filter by driver_ids if specified
        if self.driver_ids and driver_id not in self.driver_ids:
            return None
        
        message = {
            'timestamp': datetime.utcnow().isoformat(),
            'original_timestamp': record.get('SessionTime', '').isoformat() if hasattr(record.get('SessionTime', ''), 'isoformat') else str(record.get('SessionTime', '')),
            'driver': driver_id,
            'driver_id': driver_id,  # Explicit driver_id field for partitioning
            'session_time': float(record.get('SessionTime', 0)) if isinstance(record.get('SessionTime'), (int, float)) else 0.0,
            'speed': float(record.get('Speed', 0)) if pd.notna(record.get('Speed')) else 0.0,
            'rpm': float(record.get('RPM', 0)) if pd.notna(record.get('RPM')) else 0.0,
            'throttle': float(record.get('Throttle', 0)) if pd.notna(record.get('Throttle')) else 0.0,
            'brake': float(record.get('Brake', 0)) if pd.notna(record.get('Brake')) else 0.0,
            'gear': int(record.get('Gear', 0)) if pd.notna(record.get('Gear')) else 0,
            'drs': int(record.get('DRS', 0)) if pd.notna(record.get('DRS')) else 0,
            'n_gear': int(record.get('nGear', 0)) if pd.notna(record.get('nGear')) else 0,
            'message_type': message_type
        }
        
        # Add brake temperatures if available
        for brake_pos in ['FL', 'FR', 'RL', 'RR']:
            col_name = f'BrakeTemp{brake_pos}'
            if col_name in record:
                message[f'brake_temp_{brake_pos.lower()}'] = float(record[col_name]) if pd.notna(record[col_name]) else 0.0
        
        # Add position if available
        if 'X' in record and 'Y' in record:
            message['x'] = float(record['X']) if pd.notna(record['X']) else 0.0
            message['y'] = float(record['Y']) if pd.notna(record['Y']) else 0.0
            if 'Z' in record:
                message['z'] = float(record['Z']) if pd.notna(record['Z']) else 0.0
        
        # Add lap number if available
        if 'LapNumber' in record:
            message['lap_number'] = int(record['LapNumber']) if pd.notna(record['LapNumber']) else 0
        
        # Add compound if available
        if 'Compound' in record:
            message['compound'] = str(record['Compound']) if pd.notna(record['Compound']) else 'UNKNOWN'
        
        # Add alert-specific fields
        if message_type == 'alert':
            message['alert_id'] = generate_message_key('alert_id', record.get('alert_id'))
            message['severity'] = record.get('severity', 'medium')
            message['alert_type'] = record.get('alert_type', 'unknown')
            message['description'] = record.get('description', '')
        
        # Add prediction-specific fields
        if message_type == 'prediction':
            message['model_type'] = record.get('model_type', 'unknown')
            message['prediction'] = record.get('prediction', {})
            message['confidence'] = record.get('confidence', 0.0)
        
        return message
    
    def send_alert(self, alert_data: Dict[str, Any]):
        """
        Send alert message to alerts topic
        
        Args:
            alert_data: Alert data dictionary with severity, alert_type, description, etc.
        """
        if self.producer is None:
            self._setup_kafka_producer()
        
        # Create alert message
        message = {
            'timestamp': datetime.utcnow().isoformat(),
            'alert_id': generate_message_key('alert_id', alert_data.get('alert_id')),
            'severity': alert_data.get('severity', 'medium'),
            'alert_type': alert_data.get('alert_type', 'unknown'),
            'description': alert_data.get('description', ''),
            'driver_id': alert_data.get('driver_id', 'UNKNOWN'),
            'message_type': 'alert',
            **alert_data
        }
        
        topic_name = get_topic_name('alerts', config=self.config)
        alert_key = message['alert_id']
        
        # Get partition based on severity
        kafka_config = self.config.get('kafka', {})
        num_partitions = kafka_config.get('partitions', {}).get('alerts', 3)
        partition = get_partition_for_severity(message['severity'], num_partitions)
        
        self.producer.send(
            topic_name,
            key=alert_key,
            value=message,
            partition=partition
        )
        logger.debug(f"Sent alert to {topic_name} partition {partition}: {alert_data.get('alert_type')}")
    
    def _generate_and_send_alerts(self, message: Dict[str, Any], record: Dict[str, Any]):
        """Generate alerts from telemetry message and send to alerts topic"""
        try:
            driver_id = message.get('driver_id', 'UNKNOWN')
            speed = message.get('speed', 0)
            drs = message.get('drs', 0) or message.get('DRS', 0)
            drs_bool = bool(int(drs)) if drs else False
            
            # 1. High Speed Alert (>300 km/h)
            if speed > 300.0:
                self.send_alert({
                    'alert_type': 'high_speed',
                    'severity': 'high',
                    'description': f'High speed detected: {speed:.1f} km/h (threshold: 300 km/h)',
                    'driver_id': driver_id,
                    'value': speed,
                    'threshold': 300.0
                })
            
            # 2. DRS Status Change Alert
            if driver_id not in self.previous_drs_state:
                self.previous_drs_state[driver_id] = drs_bool
            else:
                previous_drs = self.previous_drs_state[driver_id]
                if previous_drs != drs_bool:
                    self.previous_drs_state[driver_id] = drs_bool
                    drs_status = 'ON' if drs_bool else 'OFF'
                    self.send_alert({
                        'alert_type': 'drs_status_change',
                        'severity': 'medium',
                        'description': f'DRS {drs_status} - Driver {driver_id}',
                        'driver_id': driver_id,
                        'drs_status': drs_status,
                        'previous_status': 'ON' if previous_drs else 'OFF'
                    })
            
            # 3. Brake Temperature Alert
            brake_temps = {}
            max_temp = 0.0
            max_position = None
            
            # Check all brake positions
            for pos in ['FL', 'FR', 'RL', 'RR']:
                temp_key = f'brake_temp_{pos.lower()}'
                if temp_key in message:
                    temp = message[temp_key]
                    brake_temps[pos] = temp
                    if temp > max_temp:
                        max_temp = temp
                        max_position = pos
                else:
                    # Try alternative naming from record
                    alt_key = f'BrakeTemp{pos}'
                    if alt_key in record:
                        temp = float(record[alt_key]) if pd.notna(record[alt_key]) else 0.0
                        brake_temps[pos] = temp
                        if temp > max_temp:
                            max_temp = temp
                            max_position = pos
            
            if max_temp > 800.0:  # High threshold
                self.send_alert({
                    'alert_type': 'brake_temperature',
                    'severity': 'high',
                    'description': f'High brake temperature: {max_temp:.1f}°C at {max_position} (threshold: 800°C)',
                    'driver_id': driver_id,
                    'temperature': max_temp,
                    'position': max_position,
                    'threshold': 800.0,
                    'all_temps': brake_temps
                })
            elif max_temp > 600.0:  # Medium threshold
                self.send_alert({
                    'alert_type': 'brake_temperature',
                    'severity': 'medium',
                    'description': f'Elevated brake temperature: {max_temp:.1f}°C at {max_position} (threshold: 600°C)',
                    'driver_id': driver_id,
                    'temperature': max_temp,
                    'position': max_position,
                    'threshold': 600.0,
                    'all_temps': brake_temps
                })
        except Exception as e:
            logger.warning(f"Error generating alerts: {e}")
            # Don't fail the entire streaming if alert generation fails
    
    def send_prediction(self, prediction_data: Dict[str, Any]):
        """
        Send ML prediction message to predictions topic
        
        Args:
            prediction_data: Prediction data dictionary with model_type, prediction, confidence, etc.
        """
        if self.producer is None:
            self._setup_kafka_producer()
        
        # Create prediction message
        message = {
            'timestamp': datetime.utcnow().isoformat(),
            'model_type': prediction_data.get('model_type', 'unknown'),
            'prediction': prediction_data.get('prediction', {}),
            'confidence': prediction_data.get('confidence', 0.0),
            'driver_id': prediction_data.get('driver_id', 'UNKNOWN'),
            'message_type': 'prediction',
            **prediction_data
        }
        
        topic_name = get_topic_name('predictions', config=self.config)
        model_key = generate_message_key('model_type', message['model_type'])
        
        # Get partition based on model_type
        kafka_config = self.config.get('kafka', {})
        num_partitions = kafka_config.get('partitions', {}).get('predictions', 3)
        partition = get_partition_for_model_type(message['model_type'], num_partitions)
        
        self.producer.send(
            topic_name,
            key=model_key,
            value=message,
            partition=partition
        )
        logger.debug(f"Sent prediction to {topic_name} partition {partition}: {message['model_type']}")
    
    def stream_at_frequency(self, duration_seconds: Optional[int] = None, 
                           speed_factor: float = 1.0, 
                           start_immediately: bool = True) -> Dict[str, Any]:
        """
        Stream data at exact FastF1 frequency
        
        Args:
            duration_seconds: Maximum duration to stream (None for all data)
            speed_factor: Speed multiplier (1.0 = real-time, 2.0 = 2x speed)
            start_immediately: If True, start streaming even if cache is still loading
            
        Returns:
            Dictionary with streaming statistics
        """
        if self.producer is None:
            self._setup_kafka_producer()
        
        # Use new topic name structure
        topic_name = get_topic_name('telemetry', config=self.config)
        frequency = self.cache_manager.get_frequency()
        
        logger.info(f"Starting stream to topic '{topic_name}' at {frequency:.2f} Hz (speed: {speed_factor}x)")
        if self.driver_ids:
            logger.info(f"Filtering for drivers: {self.driver_ids}")
        
        self.start_time = time.time()
        self.message_count = 0
        index = 0
        skipped_count = 0
        
        try:
            # Wait for cache to be ready if not starting immediately
            if not start_immediately:
                while not self.cache_loaded and self.cache_loading:
                    time.sleep(0.1)
                    if not self.cache_loading:
                        break
            
            while True:
                # Check if cache has more records
                if not self.cache_manager.has_more_records():
                    # If cache is still loading, wait a bit
                    if self.cache_loading:
                        time.sleep(0.1)
                        continue
                    else:
                        # Cache loaded and no more records
                        break
                
                # Check duration limit
                if duration_seconds and (time.time() - self.start_time) >= duration_seconds:
                    logger.info(f"Duration limit reached: {duration_seconds}s")
                    break
                
                # Get next record
                record = self.cache_manager.get_next_record()
                if record is None:
                    # If cache is still loading, wait a bit
                    if self.cache_loading:
                        time.sleep(0.1)
                        continue
                    else:
                        break
                
                # Create message (filters by driver_ids if specified)
                message = self._create_message(record, message_type='telemetry')
                
                # Skip if message is None (filtered out by driver_ids)
                if message is None:
                    skipped_count += 1
                    index += 1
                    # When filtering, don't sleep for skipped messages - continue immediately
                    continue
                
                # Calculate sleep interval based on actual data or consistent frequency
                if self.driver_ids:
                    # When filtering by driver, use consistent frequency-based interval
                    # to avoid heartbeat pattern from gaps in filtered data
                    sleep_interval = (1.0 / frequency) / speed_factor if frequency > 0 else 0
                else:
                    # When not filtering, use original sleep intervals for accurate replay
                    sleep_interval = self.cache_manager.get_sleep_interval(index) / speed_factor
                
                # Send to Kafka with driver_id as key for partitioning
                driver_key = generate_message_key('driver_id', message.get('driver_id', 'UNKNOWN'))
                self.producer.send(
                    topic_name,
                    key=driver_key,
                    value=message
                )
                
                # Generate and send alerts if enabled
                if self.enable_alerts:
                    self._generate_and_send_alerts(message, record)
                
                self.message_count += 1
                index += 1
                
                # Log progress every 100 messages
                if self.message_count % 100 == 0:
                    elapsed = time.time() - self.start_time
                    rate = self.message_count / elapsed if elapsed > 0 else 0
                    logger.info(f"Streamed {self.message_count} messages (skipped {skipped_count}) in {elapsed:.1f}s ({rate:.1f} msg/s)")
                
                # Sleep to maintain frequency (if interval > 0)
                if sleep_interval > 0:
                    time.sleep(max(0, sleep_interval))
            
            # Flush remaining messages
            self.producer.flush()
            
            # Calculate statistics
            elapsed_time = time.time() - self.start_time
            avg_rate = self.message_count / elapsed_time if elapsed_time > 0 else 0
            
            stats = {
                'messages_sent': self.message_count,
                'messages_skipped': skipped_count,
                'duration_seconds': elapsed_time,
                'avg_rate_messages_per_sec': avg_rate,
                'frequency_hz': frequency,
                'success': True
            }
            
            logger.info(f"Streaming completed: {self.message_count} messages (skipped {skipped_count}) in {elapsed_time:.1f}s ({avg_rate:.1f} msg/s)")
            
            return stats
            
        except KeyboardInterrupt:
            logger.info("Streaming interrupted by user")
            self.producer.flush()
            return {
                'messages_sent': self.message_count,
                'messages_skipped': skipped_count,
                'duration_seconds': time.time() - self.start_time if self.start_time else 0,
                'interrupted': True,
                'success': False
            }
        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            return {
                'messages_sent': self.message_count,
                'messages_skipped': skipped_count,
                'error': str(e),
                'success': False
            }
    
    def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.close()
            logger.info("Kafka producer closed")

