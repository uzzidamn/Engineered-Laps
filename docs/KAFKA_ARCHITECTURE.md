# Kafka Architecture - F1 Streaming Pipeline

## Overview

This document describes the complete Kafka architecture for the F1 Real-Time Telemetry Streaming Pipeline. The architecture is designed to support multiple independent consumers monitoring the same data streams simultaneously.

## Infrastructure

### Broker Configuration
- **Bootstrap Server**: `localhost:9092`
- **Replication Factor**: `1` (single broker, development setup)
- **Topics**: 3 main topics for telemetry, alerts, and predictions

## Topics Structure

### 1. Telemetry Topic: `f1-telemetry`
- **Partitions**: 4
- **Purpose**: Real-time F1 telemetry data (speed, RPM, gear, etc.)
- **Partitioning Strategy**: Hash-based on `driver_id` message key
- **Message Key**: `driver_id` (e.g., "VER", "HAM", "LEC")
- **Message Format**: JSON with fields: `driver_id`, `speed`, `rpm`, `gear`, `timestamp`, `message_type`

**Partitioning Logic:**
```python
# Messages with same driver_id go to same partition
# Ensures per-driver ordering and load distribution
driver_key = generate_message_key('driver_id', message.get('driver_id'))
producer.send(topic_name, key=driver_key, value=message)
```

### 2. Alerts Topic: `f1-alerts`
- **Partitions**: 3
- **Purpose**: Anomaly alerts and notifications
- **Partitioning Strategy**: Severity-based mapping
- **Message Key**: `alert_id` (UUID)
- **Partition Mapping**:
  - `high` severity → Partition 0
  - `medium` severity → Partition 1
  - `low` severity → Partition 2

### 3. Predictions Topic: `f1-predictions`
- **Partitions**: 3
- **Purpose**: ML model predictions (crash risk, tire failure, pit stop probability)
- **Partitioning Strategy**: Hash-based on `model_type`
- **Message Key**: `model_type` (e.g., "crash_risk", "tire_failure")
- **Model Types**: `crash_risk`, `tire_failure`, `pit_stop_probability`

## Consumer Groups

The architecture uses **6 consumer groups** to enable parallel processing and independent monitoring:

| Consumer Group Config Key | Consumer Group Name | Purpose | Used By |
|---------------------------|---------------------|---------|---------|
| `streamlit_anomalies` | `streamlit-anomalies-group` | General telemetry and metrics | Streamlit Tab 3: Kafka Metrics Dashboard |
| `streamlit_wheel_spin` | `streamlit-wheel-spin-group` | Wheel spin anomaly detection | Streamlit Tab 4: Real-Time Wheel Spin |
| `streamlit_gear_anomalies` | `streamlit-gear-anomalies-group` | Gear selection anomaly detection | Streamlit Tab 5: Real-Time Gear Anomalies |
| `alert_processor` | `alert-processor-group` | Alert processing and monitoring | Streamlit Tab 6: Real-Time Alerts & Warnings |
| `ml_inference` | `ml-inference-group` | ML model inference | ML inference pipeline |
| `notebook_monitor` | `notebook-monitor-group` | Jupyter notebook monitoring | Notebook 04: Kafka Dashboard |

### Consumer Group Benefits

1. **Independent Processing**: Each consumer group receives ALL messages independently
2. **No Interference**: Multiple dashboards can run simultaneously without conflicts
3. **Independent Offsets**: Each group tracks its own read position
4. **Scalability**: Can add more consumers to a group for parallel processing

## Producer Architecture

### RealTimeProducer (`src/kafka_producer.py`)

**Configuration:**
```python
KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=json.dumps,      # JSON serialization
    key_serializer=str.encode,         # String key encoding
    acks='all',                        # Wait for all replicas
    retries=3,                         # Retry failed sends
    batch_size=16384,                  # 16KB batches
    linger_ms=10,                      # Wait 10ms for batching
    compression_type='gzip'            # Compress messages
)
```

**Streaming Behavior:**
- Streams at FastF1 frequency (10-20 Hz typically)
- Preserves original timestamp spacing for accurate replay
- When filtering by `driver_ids`, uses consistent frequency intervals (no heartbeat gaps)
- Speed factor control (1.0 = real-time, 2.0 = 2x speed)
- **Alert Generation**: Automatically generates and sends alerts during telemetry streaming:
  - High Speed Alert: When speed > 300 km/h (High severity → Partition 0)
  - DRS Status Change: When DRS transitions on/off (Medium severity → Partition 1)
  - Brake Temperature: When brake temp > 600°C (Medium) or > 800°C (High) → Partition 1 or 0

**Message Creation:**
```python
message = {
    'timestamp': datetime.now().isoformat(),
    'driver_id': record.get('DriverID'),
    'speed': record.get('Speed'),
    'rpm': record.get('RPM'),
    'gear': record.get('Gear'),
    'message_type': 'telemetry',
    # ... other telemetry fields
}
```

## Consumer Architecture

### RealTimeConsumer (`src/kafka_consumer.py`)

**Configuration:**
```python
KafkaConsumer(
    *topics,                           # Subscribe to topics
    bootstrap_servers='localhost:9092',
    value_deserializer=json.loads,     # JSON deserialization
    key_deserializer=str.decode,       # String key decoding
    group_id=consumer_group,           # Consumer group name
    auto_offset_reset='earliest',      # Start from beginning if no offset
    enable_auto_commit=True,            # Auto-commit offsets
    consumer_timeout_ms=2000           # Poll timeout
)
```

**Features:**
- Driver filtering (optional)
- Message buffering (deque with maxlen=10000)
- Latency tracking (last 1000 messages)
- ML inference integration (optional)
- Poll-based consumption with timeout handling

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA SOURCE                              │
│  (FastF1 API or Cache File)                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              RealTimeProducer                                │
│  • Loads data from cache/FastF1                             │
│  • Filters by driver_ids (optional)                         │
│  • Streams at FastF1 frequency                              │
│  • Partitions by driver_id (hash)                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              KAFKA BROKER (localhost:9092)                   │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Topic: f1-telemetry (4 partitions)                │    │
│  │  Partition 0: [VER messages]                       │    │
│  │  Partition 1: [HAM messages]                       │    │
│  │  Partition 2: [LEC messages]                      │    │
│  │  Partition 3: [Other drivers]                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Topic: f1-alerts (3 partitions)                   │    │
│  │  Partition 0: [High severity]                      │    │
│  │  Partition 1: [Medium severity]                     │    │
│  │  Partition 2: [Low severity]                        │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Topic: f1-predictions (3 partitions)              │    │
│  │  [ML predictions distributed by hash]              │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Consumer    │ │ Consumer    │ │ Consumer    │
│ Group 1:    │ │ Group 2:     │ │ Group 3:    │
│ streamlit-  │ │ streamlit-   │ │ notebook_   │
│ anomalies   │ │ wheel_spin   │ │ monitor     │
│             │ │              │ │             │
│ Tab 3: Live │ │ Tab 4: Wheel │ │ Jupyter     │
│ Streaming   │ │ Spin Monitor │ │ Notebook    │
└─────────────┘ └─────────────┘ └─────────────┘
         │           │           │
         └───────────┼───────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Consumer    │ │ Consumer    │ │             │
│ Group 4:    │ │ Group 5:     │ │             │
│ alert_      │ │ ml_inference │ │             │
│ processor   │ │              │ │             │
│             │ │              │ │             │
│ Tab 5:      │ │ ML Pipeline  │ │             │
│ Alerts      │ │              │ │             │
│ Monitor     │ │              │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

## Streamlit Dashboard Integration

### New Tab Structure (6 Tabs)

The dashboard is organized into **Offline Analysis** (Tabs 1-2) and **Real-Time Kafka Streaming** (Tabs 3-6):

#### Offline Analysis Section

**Tab 1: Offline Wheel Spin Analysis**
- Uses pre-loaded data from sidebar
- No Kafka dependency
- Historical analysis and playback controls

**Tab 2: Offline Gear Anomalies Analysis**
- Uses pre-loaded data from sidebar
- No Kafka dependency
- Historical anomaly detection and visualization

#### Real-Time Kafka Streaming Section

**Tab 3: Kafka Metrics Dashboard**
- **Consumer Group**: `streamlit-anomalies-group`
- **Topic**: `f1-telemetry`
- **Purpose**: Infrastructure monitoring and metrics
- **Features**: 
  - Producer metrics (message count, rate, uptime)
  - Consumer metrics for all groups
  - Topic information and partition details
  - Live message preview

**Tab 4: Real-Time Wheel Spin Analysis**
- **Consumer Group**: `streamlit-wheel-spin-group`
- **Topic**: `f1-telemetry`
- **Purpose**: Real-time wheel spin anomaly detection
- **Features**: 
  - Live wheel spin percentage calculation
  - Actual vs Expected speed comparison
  - Spin event detection and real-time charts
  - Multi-driver support with color coding

**Tab 5: Real-Time Gear Anomalies**
- **Consumer Group**: `streamlit-gear-anomalies-group`
- **Topic**: `f1-telemetry`
- **Purpose**: Real-time gear selection anomaly detection
- **Features**:
  - Lugging detection (gear too high for speed)
  - Over-revving detection (gear too low for speed)
  - Rapid shifting detection
  - Gear vs Speed scatter plots
  - Multi-driver anomaly comparison

**Tab 6: Real-Time Alerts & Warnings**
- **Consumer Group**: `alert-processor-group`
- **Topic**: `f1-alerts`
- **Purpose**: Real-time alert monitoring and visualization
- **Features**:
  - High speed alerts (Partition 0 - High severity)
  - DRS status change alerts (Partition 1 - Medium severity)
  - Brake temperature alerts (Partition 0/1 - High/Medium severity)
  - Alerts organized by partition and severity
  - Real-time timeline and distribution charts

### Master Streaming Control

All real-time tabs (3-6) are controlled by a **Master Streaming Control** in the sidebar:

- **Single Start/Stop**: One button starts producer and all 4 consumers simultaneously
- **Driver Selection**: Select multiple drivers to stream (e.g., VER, HAM, LEC)
- **Data Source**: Choose between Cache File or FastF1 API
- **Status Indicator**: Shows streaming status and uptime
- **Automatic Initialization**: All consumers auto-start when master streaming begins

**Benefits:**
- Consistent streaming state across all tabs
- No manual consumer activation needed
- Synchronized data flow
- Better resource management
- Simplified UX

## Jupyter Notebook Integration

### Notebook 04: Kafka Dashboard
- **Consumer Group**: `notebook-monitor-group`
- **Topic**: `f1-telemetry`
- **Purpose**: Interactive monitoring and analysis
- **Features**: Live matplotlib/plotly visualizations, data export

## Message Format

### Telemetry Message
```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "driver_id": "VER",
  "speed": 285.5,
  "rpm": 12500,
  "gear": 7,
  "message_type": "telemetry",
  "session_time": "0 days 01:23:45.123456",
  "lap_number": 12,
  "throttle": 0.95,
  "brake": 0.0,
  "drs": true
}
```

### Alert Message
```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "alert_id": "uuid-here",
  "alert_type": "high_speed",
  "severity": "high",
  "driver_id": "VER",
  "message_type": "alert",
  "description": "High speed detected: 305.5 km/h (threshold: 300 km/h)",
  "value": 305.5,
  "threshold": 300.0
}
```

**Alert Types:**
- `high_speed`: Speed exceeds 300 km/h (High severity → Partition 0)
- `drs_status_change`: DRS on/off transition (Medium severity → Partition 1)
- `brake_temperature`: Brake temp > 600°C (Medium) or > 800°C (High) → Partition 1 or 0

### Prediction Message
```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "model_type": "crash_risk",
  "prediction": {"risk_level": "medium", "probability": 0.15},
  "confidence": 0.87,
  "driver_id": "VER",
  "message_type": "prediction"
}
```

## Partitioning Strategies

### 1. Telemetry Topic (Hash-based)
- **Key**: `driver_id`
- **Method**: Kafka's default hash partitioning
- **Result**: Same driver always goes to same partition
- **Benefits**: 
  - Per-driver ordering guaranteed
  - Load distribution across partitions
  - Parallel processing capability

### 2. Alerts Topic (Severity-based)
- **Key**: `alert_id` (UUID)
- **Method**: Custom partition mapping by severity
- **Result**: 
  - High severity → Partition 0 (priority processing)
  - Medium severity → Partition 1
  - Low severity → Partition 2
- **Benefits**: Priority-based processing

### 3. Predictions Topic (Hash-based)
- **Key**: `model_type`
- **Method**: Hash of model_type string
- **Result**: Even distribution across partitions
- **Benefits**: Load balancing for ML inference

## Topic Creation

Topics are automatically created when the producer starts:
```python
create_all_topics(config=config)
```

This ensures all required topics exist before streaming begins.

## Offset Management

- **Auto-commit**: Enabled by default (`enable_auto_commit=True`)
- **Offset Reset**: `earliest` (starts from beginning if no offset exists)
- **Offset Storage**: Kafka's internal `__consumer_offsets` topic
- **Per Consumer Group**: Each group maintains independent offsets

## Scalability Considerations

### Current Setup (Development)
- Single broker (replication_factor=1)
- 4 partitions for telemetry
- Suitable for development/testing

### Production-Ready Scaling
1. **Increase Replication Factor**: Set to 3 for fault tolerance
2. **Add More Partitions**: Increase to 8-16 for higher throughput
3. **Multiple Brokers**: Deploy Kafka cluster with 3+ brokers
4. **Consumer Scaling**: Add multiple consumers per group for parallel processing

### Scaling Example
```python
# Current: 4 partitions, 1 consumer per group
# Scaled: 8 partitions, 2 consumers per group
# Each consumer handles 4 partitions
```

## Performance Characteristics

### Producer
- **Throughput**: ~10-20 messages/second (matches FastF1 frequency)
- **Latency**: <10ms per message (with batching)
- **Compression**: GZIP reduces network bandwidth by ~70%

### Consumer
- **Poll Timeout**: 100-2000ms (configurable)
- **Batch Processing**: Up to 100 messages per poll
- **Buffer Size**: 10,000 messages (for Streamlit)

## Error Handling

### Producer
- **Retries**: 3 attempts for failed sends
- **Acks**: `all` ensures message durability
- **Error Logging**: All errors logged with context

### Consumer
- **Timeout Handling**: Graceful timeout with no message loss
- **Connection Recovery**: Automatic reconnection on broker failure
- **Offset Management**: Safe offset commits prevent duplicate processing

## Configuration File Structure

```yaml
kafka:
  bootstrap_servers: "localhost:9092"
  topics:
    telemetry: "f1-telemetry"
    alerts: "f1-alerts"
    predictions: "f1-predictions"
  partitions:
    telemetry: 4
    alerts: 3
    predictions: 3
  replication_factor: 1
  consumer_groups:
    streamlit_anomalies: "streamlit-anomalies-group"
    streamlit_wheel_spin: "streamlit-wheel-spin-group"
    alert_processor: "alert-processor-group"
    ml_inference: "ml-inference-group"
    notebook_monitor: "notebook-monitor-group"
  partitioning:
    telemetry_key: "driver_id"
    alert_key: "alert_id"
    prediction_key: "model_type"
```

## Best Practices

1. **Consumer Groups**: Use separate groups for different use cases
2. **Partitioning**: Choose partitioning strategy based on ordering requirements
3. **Offset Management**: Monitor consumer lag to ensure timely processing
4. **Error Handling**: Implement retry logic and dead-letter queues
5. **Monitoring**: Track message rates, latency, and consumer lag
6. **Resource Management**: Close consumers properly to release resources

## Troubleshooting

### Common Issues

1. **Consumer Not Receiving Messages**
   - Check consumer group offset (may be at end of topic)
   - Verify topic exists and has messages
   - Check consumer group name matches config

2. **High Latency**
   - Increase batch size
   - Reduce poll timeout
   - Check network latency to broker

3. **Message Loss**
   - Verify `acks='all'` in producer
   - Check replication factor
   - Monitor consumer lag

4. **Partition Imbalance**
   - Verify message keys are well-distributed
   - Consider increasing partitions
   - Check hash distribution

## Monitoring

### Key Metrics
- **Message Rate**: Messages per second per topic
- **Consumer Lag**: Messages behind latest offset
- **Latency**: End-to-end message processing time
- **Partition Distribution**: Messages per partition
- **Error Rate**: Failed sends/consumes

### Tools
- Kafka Manager / Kafka UI
- Consumer group status commands
- Topic inspection tools
- Custom metrics dashboard (Streamlit)

## Future Enhancements

1. **Schema Registry**: Add Avro schema support
2. **Dead Letter Queue**: Handle failed messages
3. **Exactly-Once Semantics**: Idempotent producers
4. **Multi-Region**: Cross-datacenter replication
5. **Stream Processing**: Kafka Streams integration
6. **Monitoring Dashboard**: Real-time metrics visualization

---

## Summary

The Kafka architecture is designed for:
- **Real-time streaming** at FastF1 frequency
- **Multiple independent consumers** monitoring the same data
- **Scalable partitioning** for load distribution
- **Fault tolerance** through replication (production)
- **Flexible consumption** through consumer groups

All components are synchronized through `config/config.yaml`, ensuring consistent configuration across the entire pipeline.

