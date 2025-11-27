"""
Kafka utility functions for topic management, partitioning, and consumer groups
"""

import os
import sys
import yaml
import logging
import uuid
from typing import Dict, Any, Optional, List
from kafka.admin import KafkaAdminClient, NewTopic, ConfigResource, ConfigResourceType
from kafka.errors import TopicAlreadyExistsError
from kafka import KafkaConsumer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def get_kafka_config(config: Optional[Dict[str, Any]] = None, 
                     config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Get Kafka configuration"""
    if config is None:
        config = load_config(config_path)
    return config.get('kafka', {})


def create_topic(topic_name: str, num_partitions: int, replication_factor: int = 1,
                 bootstrap_servers: str = "localhost:9092") -> bool:
    """
    Create a Kafka topic if it doesn't exist
    
    Args:
        topic_name: Name of the topic
        num_partitions: Number of partitions
        replication_factor: Replication factor
        bootstrap_servers: Kafka bootstrap servers
        
    Returns:
        True if topic was created or already exists, False on error
    """
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id='f1_topic_manager'
        )
        
        topic = NewTopic(
            name=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor
        )
        
        fs = admin_client.create_topics([topic], validate_only=False)
        for topic_name_check, f in fs.items():
            try:
                f.result()
                logger.info(f"✅ Topic '{topic_name_check}' created successfully")
                return True
            except TopicAlreadyExistsError:
                logger.info(f"ℹ️  Topic '{topic_name_check}' already exists")
                return True
            except Exception as e:
                error_str = str(e)
                if "already exists" in error_str.lower() or "TopicAlreadyExistsError" in error_str or "error_code=36" in error_str:
                    logger.info(f"ℹ️  Topic '{topic_name_check}' already exists")
                    return True
                else:
                    logger.error(f"❌ Failed to create topic '{topic_name_check}': {e}")
                    return False
    except Exception as e:
        error_str = str(e)
        # Check if the error is about topic already existing
        if "already exists" in error_str.lower() or "error_code=36" in error_str:
            logger.info(f"ℹ️  Topic '{topic_name}' already exists")
            return True
        else:
            logger.error(f"Error creating topic '{topic_name}': {e}")
            return False


def create_all_topics(config: Optional[Dict[str, Any]] = None, 
                      config_path: str = "config/config.yaml") -> Dict[str, bool]:
    """
    Create all required Kafka topics based on configuration
    
    Returns:
        Dictionary mapping topic names to creation success status
    """
    kafka_config = get_kafka_config(config, config_path)
    bootstrap_servers = kafka_config.get('bootstrap_servers', 'localhost:9092')
    topics_config = kafka_config.get('topics', {})
    partitions_config = kafka_config.get('partitions', {})
    replication_factor = kafka_config.get('replication_factor', 1)
    
    results = {}
    
    # Create telemetry topic
    telemetry_topic = topics_config.get('telemetry', 'f1-telemetry')
    telemetry_partitions = partitions_config.get('telemetry', 4)
    results[telemetry_topic] = create_topic(
        telemetry_topic, telemetry_partitions, replication_factor, bootstrap_servers
    )
    
    # Create alerts topic
    alerts_topic = topics_config.get('alerts', 'f1-alerts')
    alerts_partitions = partitions_config.get('alerts', 3)
    results[alerts_topic] = create_topic(
        alerts_topic, alerts_partitions, replication_factor, bootstrap_servers
    )
    
    # Create predictions topic (optional)
    predictions_topic = topics_config.get('predictions', 'f1-predictions')
    predictions_partitions = partitions_config.get('predictions', 3)
    results[predictions_topic] = create_topic(
        predictions_topic, predictions_partitions, replication_factor, bootstrap_servers
    )
    
    return results


def check_kafka_connection(bootstrap_servers: str = "localhost:9092", timeout_ms: int = 5000) -> bool:
    """
    Check if Kafka broker is reachable
    
    Args:
        bootstrap_servers: Kafka bootstrap servers
        timeout_ms: Connection timeout in milliseconds
        
    Returns:
        True if connection successful, False otherwise
    """
    try:
        from kafka import KafkaProducer
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=timeout_ms,
            max_block_ms=timeout_ms
        )
        producer.close()
        return True
    except Exception as e:
        logger.debug(f"Kafka connection failed: {e}")
        return False


def validate_topic_exists(topic_name: str, bootstrap_servers: str = "localhost:9092") -> bool:
    """Check if a topic exists"""
    try:
        consumer = KafkaConsumer(bootstrap_servers=bootstrap_servers)
        partitions = consumer.partitions_for_topic(topic_name)
        consumer.close()
        return partitions is not None and len(partitions) > 0
    except Exception as e:
        logger.error(f"Error validating topic '{topic_name}': {e}")
        return False


def get_topic_partitions(topic_name: str, bootstrap_servers: str = "localhost:9092") -> Optional[int]:
    """Get number of partitions for a topic"""
    try:
        consumer = KafkaConsumer(bootstrap_servers=bootstrap_servers)
        partitions = consumer.partitions_for_topic(topic_name)
        consumer.close()
        return len(partitions) if partitions else None
    except Exception as e:
        logger.error(f"Error getting partitions for topic '{topic_name}': {e}")
        return None


def generate_message_key(key_type: str, value: Any) -> str:
    """
    Generate message key based on type
    
    Args:
        key_type: Type of key ('driver_id', 'alert_id', 'model_type')
        value: Value to use as key (or None to generate)
        
    Returns:
        String key for Kafka message
    """
    if key_type == 'alert_id':
        # Generate UUID for alert_id if not provided
        return str(value) if value else str(uuid.uuid4())
    elif key_type == 'driver_id':
        return str(value) if value else 'UNKNOWN'
    elif key_type == 'model_type':
        return str(value) if value else 'unknown'
    else:
        return str(value) if value else 'default'


def get_partition_for_severity(severity: str, num_partitions: int = 3) -> int:
    """
    Map severity to partition number
    
    Args:
        severity: Severity level ('high', 'medium', 'low')
        num_partitions: Number of partitions available
        
    Returns:
        Partition number (0-based)
    """
    severity_map = {
        'high': 0,
        'medium': 1,
        'low': 2
    }
    
    partition = severity_map.get(severity.lower(), 1)  # Default to medium
    return min(partition, num_partitions - 1)  # Ensure within bounds


def get_partition_for_model_type(model_type: str, num_partitions: int = 3) -> int:
    """
    Map model type to partition number (hash-based)
    
    Args:
        model_type: Model type string
        num_partitions: Number of partitions available
        
    Returns:
        Partition number (0-based)
    """
    # Use hash of model_type to distribute across partitions
    return hash(model_type) % num_partitions


def get_consumer_group_config(consumer_group_name: str,
                              config: Optional[Dict[str, Any]] = None,
                              config_path: str = "config/config.yaml") -> Optional[str]:
    """
    Get consumer group name from config
    
    Args:
        consumer_group_name: Name of the consumer group config key
        config: Optional config dict
        config_path: Path to config file
        
    Returns:
        Consumer group name or None
    """
    kafka_config = get_kafka_config(config, config_path)
    consumer_groups = kafka_config.get('consumer_groups', {})
    return consumer_groups.get(consumer_group_name)


def get_topic_name(topic_type: str,
                   config: Optional[Dict[str, Any]] = None,
                   config_path: str = "config/config.yaml") -> str:
    """
    Get topic name from config
    
    Args:
        topic_type: Type of topic ('telemetry', 'alerts', 'predictions')
        config: Optional config dict
        config_path: Path to config file
        
    Returns:
        Topic name
    """
    kafka_config = get_kafka_config(config, config_path)
    topics = kafka_config.get('topics', {})
    
    # Fallback to legacy topic_name if topics not configured
    if not topics:
        if topic_type == 'telemetry':
            return kafka_config.get('topic_name', 'f1-speed-stream')
        else:
            return f"f1-{topic_type}"
    
    return topics.get(topic_type, f"f1-{topic_type}")

