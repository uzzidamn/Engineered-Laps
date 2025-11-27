"""
Kafka consumer for real-time F1 telemetry analysis with ML inference
"""

import os
import sys
import json
import time
import yaml
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections import deque

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from kafka import KafkaConsumer
except ImportError:
    print("kafka-python not installed. Install with: pip install kafka-python")
    sys.exit(1)

from src.ml_inference import MLInference
from src.kafka_utils import (
    get_topic_name, get_consumer_group_config, get_kafka_config
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RealTimeConsumer:
    """
    Kafka consumer that processes F1 telemetry in real-time
    Performs analysis and ML inference on each message
    """
    
    def __init__(self, config_path: str = "config/config.yaml",
                 consumer_group: Optional[str] = None,
                 topics: Optional[List[str]] = None,
                 driver_ids: Optional[List[str]] = None):
        """
        Initialize real-time consumer
        
        Args:
            config_path: Path to configuration file
            consumer_group: Consumer group name (None to use default from config)
            topics: List of topic names to subscribe to (None to use default from config)
            driver_ids: List of driver IDs to filter (None for all drivers)
        """
        self.config = self._load_config(config_path)
        self.consumer = None
        self.ml_inference = None
        self.message_count = 0
        self.latencies = deque(maxlen=1000)  # Store last 1000 latencies
        self.analysis_results = []
        self.consumer_group = consumer_group
        self.topics = topics
        self.driver_ids = driver_ids  # Filter by driver IDs if specified
        self.message_buffer = deque(maxlen=10000)  # Buffer for Streamlit
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            raise
    
    def _setup_kafka_consumer(self, consumer_timeout_ms: int = 2000):
        """Setup Kafka consumer connection
        
        Args:
            consumer_timeout_ms: Consumer timeout in milliseconds (for polling)
        """
        try:
            kafka_config = get_kafka_config(config=self.config)
            bootstrap_servers = kafka_config.get('bootstrap_servers', 'localhost:9092')
            
            # Determine topics to subscribe to
            if self.topics:
                topics_to_subscribe = self.topics
            else:
                # Default: subscribe to telemetry topic
                telemetry_topic = get_topic_name('telemetry', config=self.config)
                topics_to_subscribe = [telemetry_topic]
            
            # Determine consumer group
            if self.consumer_group:
                group_id = self.consumer_group
            else:
                # Use default from config (streamlit-anomalies-group)
                group_id = get_consumer_group_config('streamlit_anomalies', config=self.config)
                if not group_id:
                    # Fallback to a default group
                    group_id = 'f1-consumer-group'
            
            self.consumer = KafkaConsumer(
                *topics_to_subscribe,
                bootstrap_servers=bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                group_id=group_id,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                consumer_timeout_ms=consumer_timeout_ms
            )
            
            logger.info(f"Connected to Kafka at {bootstrap_servers}")
            logger.info(f"Consumer group: {group_id}")
            logger.info(f"Subscribed to topics: {topics_to_subscribe}")
            if self.driver_ids:
                logger.info(f"Filtering for drivers: {self.driver_ids}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    def _load_ml_models(self):
        """Load ML models for inference"""
        try:
            ml_config = self.config.get('ml', {})
            models_dir = ml_config.get('models_dir', 'models/')
            
            self.ml_inference = MLInference(models_dir)
            self.ml_inference.load_models()
            
            logger.info("ML models loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load ML models: {e}")
            self.ml_inference = None
    
    def _run_analysis(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run real-time analysis on message
        
        Args:
            message: Message dictionary
            
        Returns:
            Analysis results dictionary
        """
        analysis = {
            'timestamp': message.get('timestamp', ''),
            'driver': message.get('driver', 'UNKNOWN'),
            'anomalies': [],
            'predictions': {}
        }
        
        # Simple anomaly detection
        speed = message.get('speed', 0)
        rpm = message.get('rpm', 0)
        brake = message.get('brake', 0)
        throttle = message.get('throttle', 0)
        
        # High speed with high brake (unusual)
        if speed > 200 and brake > 0.8:
            analysis['anomalies'].append({
                'type': 'high_speed_braking',
                'severity': 'medium',
                'description': f"High speed ({speed:.1f} km/h) with heavy braking"
            })
        
        # High RPM with low speed (wheel spin)
        if rpm > 12000 and speed < 50:
            analysis['anomalies'].append({
                'type': 'wheel_spin',
                'severity': 'high',
                'description': f"High RPM ({rpm:.0f}) with low speed ({speed:.1f} km/h)"
            })
        
        # High throttle and brake simultaneously
        if throttle > 0.5 and brake > 0.5:
            analysis['anomalies'].append({
                'type': 'throttle_brake_overlap',
                'severity': 'low',
                'description': "Throttle and brake applied simultaneously"
            })
        
        # ML predictions
        if self.ml_inference:
            try:
                predictions = self.ml_inference.predict(message)
                analysis['predictions'] = predictions
            except Exception as e:
                logger.warning(f"ML inference failed: {e}")
        
        return analysis
    
    def _record_latency(self, message_time: str, processing_time: float):
        """
        Record processing latency
        
        Args:
            message_time: Message timestamp
            processing_time: Processing time in seconds
        """
        latency_ms = processing_time * 1000
        self.latencies.append({
            'timestamp': message_time,
            'latency_ms': latency_ms,
            'processing_time_s': processing_time
        })
    
    def consume_messages(self, timeout_seconds: Optional[int] = None, 
                        max_messages: Optional[int] = None) -> Dict[str, Any]:
        """
        Consume and process messages from Kafka
        
        Args:
            timeout_seconds: Maximum time to consume (None for unlimited)
            max_messages: Maximum number of messages to process (None for unlimited)
            
        Returns:
            Dictionary with consumption statistics
        """
        if self.consumer is None:
            self._setup_kafka_consumer()
        
        # Load ML models if available
        if self.ml_inference is None:
            self._load_ml_models()
        
        logger.info(f"Starting message consumption... (timeout: {timeout_seconds}s, max_messages: {max_messages})")
        
        start_time = time.time()
        self.message_count = 0
        
        # Safety: Set consumer timeout to allow periodic checks (max 2 seconds)
        # This ensures we can check overall timeout frequently
        poll_timeout_ms = 2000  # 2 seconds - allows frequent timeout checks
        if timeout_seconds:
            # Adjust poll timeout to be much smaller than overall timeout
            # Use 1-2 seconds max to allow frequent timeout checks
            poll_timeout_ms = min(2000, max(500, int(min(timeout_seconds, 10) * 100)))  # milliseconds
        
        # Setup consumer with proper timeout if not already set up
        if self.consumer is None:
            self._setup_kafka_consumer(consumer_timeout_ms=poll_timeout_ms)
        # Note: KafkaConsumer doesn't allow changing timeout after creation,
        # but 2 seconds is fine for our use case with periodic checks
        
        logger.info(f"Using poll timeout: {poll_timeout_ms}ms")
        
        try:
            while True:
                # Check timeout BEFORE trying to get next message
                elapsed = time.time() - start_time
                if timeout_seconds and elapsed >= timeout_seconds:
                    logger.info(f"Timeout reached: {timeout_seconds}s (elapsed: {elapsed:.1f}s)")
                    break
                
                # Check message limit BEFORE getting next message
                if max_messages and self.message_count >= max_messages:
                    logger.info(f"Message limit reached: {max_messages}")
                    break
                
                # Use poll() instead of iterator to allow timeout checks
                # Poll with short timeout to check conditions frequently
                try:
                    message_batch = self.consumer.poll(timeout_ms=poll_timeout_ms)
                    
                    # If no messages, check timeout and continue
                    if not message_batch:
                        elapsed = time.time() - start_time
                        if timeout_seconds and elapsed >= timeout_seconds:
                            logger.info(f"Timeout reached during poll wait: {timeout_seconds}s")
                            break
                        # Continue polling if within timeout
                        continue
                    
                    # Process all messages in the batch
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            # Check timeout before processing each message
                            elapsed = time.time() - start_time
                            if timeout_seconds and elapsed >= timeout_seconds:
                                logger.info(f"Timeout reached during message processing: {timeout_seconds}s")
                                break
                            
                            # Check message limit
                            if max_messages and self.message_count >= max_messages:
                                logger.info(f"Message limit reached: {max_messages}")
                                break
                            
                            # Process message
                            process_start = time.time()
                            
                            # Get message data
                            message_data = message.value
                            message_key = message.key
                            
                            # Filter by driver_ids if specified
                            if self.driver_ids:
                                driver_id = message_data.get('driver_id') or message_data.get('driver', 'UNKNOWN')
                                if driver_id not in self.driver_ids:
                                    continue  # Skip this message
                            
                            # Run analysis
                            analysis = self._run_analysis(message_data)
                            
                            # Record latency
                            processing_time = time.time() - process_start
                            self._record_latency(message_data.get('timestamp', ''), processing_time)
                            
                            # Store analysis result
                            result = {
                                'message': message_data,
                                'analysis': analysis,
                                'processing_time': processing_time,
                                'topic': topic_partition.topic,
                                'partition': topic_partition.partition,
                                'offset': message.offset
                            }
                            self.analysis_results.append(result)
                            
                            # Add to buffer for Streamlit
                            self.message_buffer.append(result)
                            
                            self.message_count += 1
                            
                            # Log progress every 100 messages
                            if self.message_count % 100 == 0:
                                elapsed = time.time() - start_time
                                rate = self.message_count / elapsed if elapsed > 0 else 0
                                avg_latency = sum(l['latency_ms'] for l in self.latencies) / len(self.latencies) if self.latencies else 0
                                logger.info(f"Processed {self.message_count} messages in {elapsed:.1f}s ({rate:.1f} msg/s, avg latency: {avg_latency:.2f} ms)")
                            
                            # Log anomalies
                            if analysis['anomalies']:
                                for anomaly in analysis['anomalies']:
                                    logger.warning(f"ANOMALY [{message_key}]: {anomaly['type']} - {anomaly['description']}")
                        
                        # Break outer loop if we've hit limits (after processing all messages from partition)
                        elapsed = time.time() - start_time
                        if timeout_seconds and elapsed >= timeout_seconds:
                            break
                        if max_messages and self.message_count >= max_messages:
                            break
                    
                    # Check limits after processing batch
                    elapsed = time.time() - start_time
                    if timeout_seconds and elapsed >= timeout_seconds:
                        break
                    if max_messages and self.message_count >= max_messages:
                        break
                    
                except StopIteration:
                    # No more messages from consumer
                    logger.info("No more messages available")
                    break
                except Exception as e:
                    logger.error(f"Error polling for messages: {e}")
                    # Continue polling if there's an error, unless timeout reached
                    elapsed = time.time() - start_time
                    if timeout_seconds and elapsed >= timeout_seconds:
                        break
                    continue
            
            # Calculate statistics
            elapsed_time = time.time() - start_time
            avg_rate = self.message_count / elapsed_time if elapsed_time > 0 else 0
            avg_latency = sum(l['latency_ms'] for l in self.latencies) / len(self.latencies) if self.latencies else 0
            max_latency = max(l['latency_ms'] for l in self.latencies) if self.latencies else 0
            min_latency = min(l['latency_ms'] for l in self.latencies) if self.latencies else 0
            
            stats = {
                'messages_processed': self.message_count,
                'duration_seconds': elapsed_time,
                'avg_rate_messages_per_sec': avg_rate,
                'avg_latency_ms': avg_latency,
                'max_latency_ms': max_latency,
                'min_latency_ms': min_latency,
                'total_anomalies': sum(len(a['analysis']['anomalies']) for a in self.analysis_results),
                'success': True
            }
            
            logger.info(f"Consumption completed: {self.message_count} messages in {elapsed_time:.1f}s")
            logger.info(f"Average rate: {avg_rate:.1f} msg/s, Average latency: {avg_latency:.2f} ms")
            
            return stats
            
        except KeyboardInterrupt:
            logger.info("Consumption interrupted by user")
            return {
                'messages_processed': self.message_count,
                'duration_seconds': time.time() - start_time if 'start_time' in locals() else 0,
                'interrupted': True,
                'success': False
            }
        except Exception as e:
            logger.error(f"Error during consumption: {e}")
            return {
                'messages_processed': self.message_count,
                'error': str(e),
                'success': False
            }
    
    def get_latency_stats(self) -> Dict[str, float]:
        """Get latency statistics"""
        if not self.latencies:
            return {}
        
        latencies_ms = [l['latency_ms'] for l in self.latencies]
        
        return {
            'avg': sum(latencies_ms) / len(latencies_ms),
            'min': min(latencies_ms),
            'max': max(latencies_ms),
            'count': len(latencies_ms)
        }
    
    def get_analysis_results(self) -> List[Dict[str, Any]]:
        """Get all analysis results"""
        return self.analysis_results.copy()
    
    def poll_messages(self, timeout_ms: int = 100, max_messages: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Poll for new messages and return them as a list
        Useful for Streamlit real-time updates
        
        Args:
            timeout_ms: Polling timeout in milliseconds
            max_messages: Maximum number of messages to return (None for all available)
            
        Returns:
            List of message dictionaries
        """
        if self.consumer is None:
            self._setup_kafka_consumer(consumer_timeout_ms=timeout_ms)
        
        messages = []
        try:
            message_batch = self.consumer.poll(timeout_ms=timeout_ms)
            
            for topic_partition, msgs in message_batch.items():
                for msg in msgs:
                    message_data = msg.value
                    message_key = msg.key
                    
                    # Filter by driver_ids if specified
                    if self.driver_ids:
                        driver_id = message_data.get('driver_id') or message_data.get('driver', 'UNKNOWN')
                        if driver_id not in self.driver_ids:
                            continue
                    
                    messages.append({
                        'message': message_data,
                        'key': message_key,
                        'topic': topic_partition.topic,
                        'partition': topic_partition.partition,
                        'offset': msg.offset,
                        'timestamp': time.time()
                    })
                    
                    if max_messages and len(messages) >= max_messages:
                        return messages
            
        except Exception as e:
            logger.error(f"Error polling messages: {e}")
        
        return messages
    
    def get_buffered_messages(self, clear_buffer: bool = False) -> List[Dict[str, Any]]:
        """
        Get messages from buffer (for Streamlit)
        
        Args:
            clear_buffer: If True, clear buffer after returning messages
            
        Returns:
            List of buffered messages
        """
        messages = list(self.message_buffer)
        if clear_buffer:
            self.message_buffer.clear()
        return messages
    
    def get_consumer_metrics(self) -> Dict[str, Any]:
        """
        Get consumer metrics for monitoring
        
        Returns:
            Dictionary with consumer metrics
        """
        metrics = {
            'messages_processed': self.message_count,
            'buffer_size': len(self.message_buffer),
            'latency_stats': self.get_latency_stats()
        }
        
        if self.consumer:
            try:
                # Get partition assignments
                assignments = self.consumer.assignment()
                metrics['partitions_assigned'] = [
                    {'topic': tp.topic, 'partition': tp.partition} 
                    for tp in assignments
                ]
                
                # Get consumer group info
                metrics['consumer_group'] = self.consumer.config.get('group_id', 'unknown')
                
            except Exception as e:
                logger.warning(f"Could not get consumer metrics: {e}")
        
        return metrics
    
    def close(self):
        """Close Kafka consumer"""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")

