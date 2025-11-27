# F1 Telemetry Pipeline - Scaling Guide

## Table of Contents
1. [Current Architecture Overview](#current-architecture-overview)
2. [Current Process Flow](#current-process-flow)
3. [Scaling Strategies](#scaling-strategies)
4. [Scaling Metrics](#scaling-metrics)
5. [Implementation Roadmap](#implementation-roadmap)

---

## Current Architecture Overview

### System Components

The F1 Telemetry Streaming Pipeline consists of the following key components:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CURRENT ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   FastF1     │     │    Cache     │     │   Producer   │
│    API       │────▶│   Manager    │────▶│  (Single)     │
│              │     │  (In-Memory) │     │              │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
                                    ┌──────────────────────┐
                                    │   Kafka Cluster       │
                                    │   (Single Broker)     │
                                    │                       │
                                    │  ┌─────────────────┐ │
                                    │  │ f1-telemetry    │ │
                                    │  │ (4 partitions)  │ │
                                    │  └─────────────────┘ │
                                    │  ┌─────────────────┐ │
                                    │  │ f1-alerts       │ │
                                    │  │ (3 partitions)  │ │
                                    │  └─────────────────┘ │
                                    │  ┌─────────────────┐ │
                                    │  │ f1-predictions  │ │
                                    │  │ (3 partitions)  │ │
                                    │  └─────────────────┘ │
                                    └──────────┬────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
            │  Consumer    │          │  Consumer    │          │  Consumer    │
            │  Group 1     │          │  Group 2     │          │  Group 3     │
            │  (Streamlit) │          │  (Grafana)   │          │  (Notebook)  │
            └──────────────┘          └──────────────┘          └──────────────┘
```

### Current Configuration

| Component | Current State | Limitation |
|-----------|--------------|------------|
| **Kafka Broker** | Single broker (localhost:9092) | Single point of failure, no replication |
| **Replication Factor** | 1 | No fault tolerance |
| **Producer** | Single instance | Limited throughput (~2,200 msg/s) |
| **Consumers** | 6 consumer groups, 1 consumer each | No parallel processing within groups |
| **Partitions** | 4 (telemetry), 3 (alerts), 3 (predictions) | Limits parallelism |
| **Data Source** | Single CSV/Parquet file | Sequential processing |
| **Cache** | In-memory DataFrame | Memory-bound, single process |

### Current Performance Characteristics

| Metric | Current Value | Bottleneck |
|--------|--------------|------------|
| **Producer Throughput** | ~2,200 msg/s (3 drivers) | Single producer, single thread |
| **Consumer Latency** | < 10 ms | Single consumer per group |
| **End-to-End Latency** | < 100 ms | Acceptable for current scale |
| **Memory Usage** | ~200 MB (bridge) | In-memory buffers |
| **CPU Usage** | ~15% (single core) | Underutilized |
| **Max Drivers Supported** | ~20 (full grid) | Limited by producer throughput |

---

## Current Process Flow

### Stage 1: Data Extraction & Caching

```
FastF1 API → Session Load → DataFrame → CSV/Parquet Export
                                    ↓
                            CacheManager (In-Memory)
```

**Current Process:**
- Single-threaded data extraction from FastF1 API
- Sequential loading into in-memory DataFrame
- No parallel processing or distributed caching

**Bottlenecks:**
- Network I/O for FastF1 API calls
- Memory constraints for large datasets
- Single-threaded execution

### Stage 2: Kafka Production

```
CacheManager → RealTimeProducer → Kafka Topics
```

**Current Process:**
1. Producer reads from in-memory cache sequentially
2. Messages created at FastF1 frequency (10-20 Hz)
3. Messages partitioned by `driver_id` (hash-based)
4. Alert generation happens inline during streaming
5. Single producer instance handles all drivers

**Message Flow:**
- **Telemetry**: `driver_id` → hash → partition (0-3)
- **Alerts**: `severity` → partition mapping (high=0, medium=1, low=2)
- **Predictions**: `model_type` → hash → partition (0-2)

**Bottlenecks:**
- Single producer thread
- Sequential message creation
- Inline alert generation (blocks streaming)
- No batching optimization beyond Kafka defaults

### Stage 3: Kafka Consumption

```
Kafka Topics → Consumer Groups → Processing → Visualization
```

**Current Process:**
1. **6 Consumer Groups** independently consume topics:
   - `streamlit-anomalies-group`: General telemetry
   - `streamlit-wheel-spin-group`: Wheel spin detection
   - `streamlit-gear-anomalies-group`: Gear anomaly detection
   - `alert-processor-group`: Alert processing
   - `ml-inference-group`: ML predictions
   - `notebook-monitor-group`: Jupyter monitoring

2. Each group has **1 consumer** processing all partitions
3. Consumers poll messages, process, and buffer for visualization
4. Grafana bridge aggregates data from Kafka

**Bottlenecks:**
- Single consumer per group (no parallelism)
- Sequential message processing
- No load balancing across consumers
- Limited by partition count (max 4 parallel consumers for telemetry)

### Stage 4: Visualization

```
Consumer → Grafana Bridge → Grafana Dashboard
```

**Current Process:**
- Flask bridge service consumes from Kafka
- Maintains rolling window buffers (60,000 points/driver)
- Calculates derived metrics (wheel spin, gear anomalies)
- Exposes JSON API endpoints for Grafana
- Single Flask instance

**Bottlenecks:**
- Single Flask process
- In-memory buffers (memory-bound)
- Synchronous API requests
- No caching layer

---

## Scaling Strategies

### 1. Horizontal Scaling (Recommended)

Horizontal scaling involves adding more instances of components to distribute load.

#### 1.1 Producer Scaling

**Current State:**
- Single producer instance
- Sequential message creation
- ~2,200 msg/s throughput

**Scaling Approach:**
- **Multi-Producer Architecture**: Deploy multiple producer instances
- **Driver-Based Partitioning**: Each producer handles a subset of drivers
- **Parallel Processing**: Use threading/multiprocessing for message creation

**Implementation:**
```python
# Producer Pool Architecture
Producers = {
    'producer-1': ['VER', 'HAM', 'LEC'],      # Drivers 0-2
    'producer-2': ['NOR', 'SAI', 'ALO'],      # Drivers 3-5
    'producer-3': ['GAS', 'OCO', 'STR'],      # Drivers 6-8
    'producer-4': ['RUS', 'BOT', 'PER']       # Drivers 9-11
}
```

**Expected Improvement:**
- **Throughput**: 2,200 → 8,800 msg/s (4x with 4 producers)
- **Latency**: Remains < 10 ms (no change)
- **Scalability**: Linear scaling with producer count

**Configuration Changes:**
```yaml
producers:
  count: 4
  drivers_per_producer: 3
  parallel_processing: true
  batch_size: 32768  # Increase batch size
  linger_ms: 5       # Reduce linger for lower latency
```

#### 1.2 Consumer Scaling

**Current State:**
- 1 consumer per consumer group
- Sequential partition processing
- Limited by partition count

**Scaling Approach:**
- **Consumer Instances**: Add multiple consumers per group
- **Partition Assignment**: Kafka automatically distributes partitions
- **Parallel Processing**: Each consumer processes assigned partitions independently

**Implementation:**
```python
# Consumer Scaling Example
Consumer Group: streamlit-anomalies-group
├── Consumer-1: Partitions [0, 1]
├── Consumer-2: Partitions [2, 3]
└── Throughput: 2x (if partitions are balanced)
```

**Expected Improvement:**
- **Processing Rate**: 2,200 → 4,400 msg/s (2x with 2 consumers, 4 partitions)
- **Latency**: Remains < 10 ms per message
- **Scalability**: Limited by partition count (need more partitions for more consumers)

**Configuration Changes:**
```yaml
consumers:
  streamlit_anomalies:
    instances: 2  # Scale to 2 consumers
  streamlit_wheel_spin:
    instances: 2
  # ... other groups
```

#### 1.3 Partition Scaling

**Current State:**
- 4 partitions for telemetry topic
- 3 partitions for alerts topic
- 3 partitions for predictions topic

**Scaling Approach:**
- **Increase Partitions**: Add more partitions to topics
- **Re-partitioning**: Use Kafka's partition reassignment tool
- **Key Distribution**: Ensure even distribution with hash partitioning

**Implementation:**
```bash
# Increase telemetry partitions from 4 to 16
kafka-topics.sh --alter \
  --topic f1-telemetry \
  --partitions 16 \
  --bootstrap-server localhost:9092
```

**Expected Improvement:**
- **Max Parallelism**: 4 → 16 consumers (4x increase)
- **Throughput**: Scales linearly with partition count
- **Load Distribution**: Better distribution across consumers

**Configuration Changes:**
```yaml
kafka:
  partitions:
    telemetry: 16  # Increase from 4
    alerts: 8      # Increase from 3
    predictions: 8 # Increase from 3
```

#### 1.4 Kafka Cluster Scaling

**Current State:**
- Single broker (localhost:9092)
- Replication factor: 1
- No fault tolerance

**Scaling Approach:**
- **Multi-Broker Cluster**: Deploy 3-5 Kafka brokers
- **Replication Factor**: Set to 3 for fault tolerance
- **Leader Election**: Automatic failover
- **Load Distribution**: Brokers share partition leadership

**Implementation:**
```
Kafka Cluster (3 brokers):
├── Broker-1: localhost:9092 (Leader for partitions 0, 3, 6, 9)
├── Broker-2: localhost:9093 (Leader for partitions 1, 4, 7, 10)
└── Broker-3: localhost:9094 (Leader for partitions 2, 5, 8, 11)
```

**Expected Improvement:**
- **Fault Tolerance**: Survives 1 broker failure (with RF=3)
- **Throughput**: Distributed across brokers
- **Availability**: 99.9% uptime (vs 99% single broker)

**Configuration Changes:**
```yaml
kafka:
  bootstrap_servers: "broker1:9092,broker2:9092,broker3:9092"
  replication_factor: 3
  min_insync_replicas: 2
```

### 2. Vertical Scaling

Vertical scaling involves increasing resources (CPU, memory, I/O) for existing components.

#### 2.1 Producer Vertical Scaling

**Current State:**
- Single-threaded producer
- ~15% CPU usage
- Limited by sequential processing

**Scaling Approach:**
- **Multi-threading**: Use ThreadPoolExecutor for parallel message creation
- **Batch Optimization**: Increase batch size and optimize compression
- **Memory Allocation**: Increase buffer sizes

**Implementation:**
```python
# Multi-threaded Producer
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = []
    for driver_batch in driver_batches:
        future = executor.submit(produce_messages, driver_batch)
        futures.append(future)
```

**Expected Improvement:**
- **Throughput**: 2,200 → 4,400 msg/s (2x with 2 threads)
- **CPU Usage**: 15% → 60% (better utilization)
- **Scalability**: Limited by GIL (Python) or CPU cores

#### 2.2 Consumer Vertical Scaling

**Current State:**
- Single-threaded consumers
- Low CPU usage
- Sequential processing

**Scaling Approach:**
- **Multi-threading**: Process messages in parallel threads
- **Batch Processing**: Process message batches concurrently
- **Memory Optimization**: Increase buffer sizes

**Expected Improvement:**
- **Processing Rate**: 2x-4x improvement
- **Latency**: Slight increase due to thread overhead
- **Scalability**: Limited by CPU cores

### 3. Hybrid Scaling (Recommended for Production)

Combine horizontal and vertical scaling for optimal performance.

**Recommended Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│              SCALED ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   FastF1     │     │  Distributed │     │  Producer    │
│    API       │────▶│    Cache     │────▶│   Pool (4)   │
│              │     │  (Redis/DB)  │     │              │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
                                    ┌──────────────────────┐
                                    │   Kafka Cluster       │
                                    │   (3 Brokers)         │
                                    │   RF=3                │
                                    │                       │
                                    │  ┌─────────────────┐ │
                                    │  │ f1-telemetry    │ │
                                    │  │ (16 partitions) │ │
                                    │  └─────────────────┘ │
                                    │  ┌─────────────────┐ │
                                    │  │ f1-alerts       │ │
                                    │  │ (8 partitions)  │ │
                                    │  └─────────────────┘ │
                                    └──────────┬────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
            ┌──────────────┐          ┌──────────────┐          ┌──────────────┐
            │  Consumer    │          │  Consumer    │          │  Consumer    │
            │  Pool (8)    │          │  Pool (4)    │          │  Pool (2)    │
            │  (Streamlit) │          │  (Grafana)   │          │  (Notebook)  │
            └──────────────┘          └──────────────┘          └──────────────┘
```

**Key Improvements:**
- **4 Producers** (horizontal scaling)
- **3-Broker Kafka Cluster** (horizontal + fault tolerance)
- **16 Partitions** (horizontal scaling)
- **8 Consumers per Group** (horizontal scaling)
- **Distributed Cache** (Redis/Database instead of in-memory)
- **Load Balancer** for Grafana bridge

---

## Scaling Metrics

### 1. Throughput Metrics

#### Producer Throughput
- **Current**: ~2,200 msg/s (3 drivers)
- **Target (Scaled)**: ~35,200 msg/s (20 drivers, 4 producers, 4x speed factor)
- **Formula**: `Throughput = Drivers × Messages_per_driver_per_sec × Producer_count × Speed_factor`

| Scenario | Drivers | Producers | Partitions | Expected Throughput |
|----------|---------|-----------|------------|---------------------|
| **Current** | 3 | 1 | 4 | 2,200 msg/s |
| **Small Scale** | 10 | 2 | 8 | 7,500 msg/s |
| **Medium Scale** | 20 | 4 | 16 | 15,000 msg/s |
| **Large Scale** | 20 | 8 | 32 | 30,000 msg/s |

#### Consumer Throughput
- **Current**: ~2,200 msg/s (1 consumer per group)
- **Target (Scaled)**: ~15,000 msg/s (8 consumers, 16 partitions)
- **Formula**: `Consumer_Throughput = Min(Partitions, Consumers) × Messages_per_partition_per_sec`

| Consumers | Partitions | Expected Throughput | Utilization |
|-----------|------------|---------------------|-------------|
| 1 | 4 | 2,200 msg/s | 25% (1/4 partitions) |
| 2 | 4 | 4,400 msg/s | 50% (2/4 partitions) |
| 4 | 4 | 8,800 msg/s | 100% (4/4 partitions) |
| 8 | 16 | 15,000 msg/s | 50% (8/16 partitions) |
| 16 | 16 | 30,000 msg/s | 100% (16/16 partitions) |

### 2. Latency Metrics

#### End-to-End Latency
- **Current**: < 100 ms
- **Target (Scaled)**: < 150 ms (acceptable increase due to network overhead)
- **Components**:
  - Producer: 1-2 ms
  - Kafka: 5-10 ms (single broker) → 10-20 ms (cluster)
  - Consumer: 2-5 ms
  - Processing: 1-2 ms
  - Visualization: 50-100 ms

#### Consumer Lag
- **Current**: 0 ms (real-time processing)
- **Target (Scaled)**: < 500 ms (acceptable lag)
- **Formula**: `Lag = Latest_Offset - Consumer_Offset`
- **Monitoring**: Track per partition, per consumer group

### 3. Resource Utilization Metrics

#### CPU Utilization
- **Current**: ~15% (single core)
- **Target (Scaled)**: 60-80% (multi-core utilization)
- **Per Component**:
  - Producer: 20-30% (4 producers)
  - Consumers: 40-50% (8 consumers)
  - Kafka Brokers: 30-40% (3 brokers)

#### Memory Utilization
- **Current**: ~200 MB (bridge)
- **Target (Scaled)**: ~2 GB (distributed across components)
- **Per Component**:
  - Producer: 500 MB (buffers, cache)
  - Consumers: 300 MB each (8 consumers = 2.4 GB)
  - Kafka Brokers: 1 GB each (3 brokers = 3 GB)
  - Grafana Bridge: 500 MB

#### Network Bandwidth
- **Current**: ~10 MB/s (2,200 msg/s × ~4.5 KB/msg)
- **Target (Scaled)**: ~135 MB/s (30,000 msg/s × ~4.5 KB/msg)
- **Formula**: `Bandwidth = Throughput × Avg_Message_Size`

### 4. Scalability Metrics

#### Weak Scaling Efficiency
- **Definition**: Performance remains constant as problem size and resources increase proportionally
- **Current**: Maintained (latency stable, throughput scales)
- **Target**: > 90% efficiency (minimal overhead from scaling)

#### Strong Scaling Efficiency
- **Definition**: Problem size fixed, resources increase
- **Current**: Limited by partition count
- **Target**: Linear scaling up to partition limit

#### Partition Utilization
- **Current**: 100% (4 partitions, 4 consumers max)
- **Target**: 100% (16 partitions, 16 consumers)
- **Formula**: `Utilization = Active_Consumers / Partitions`

### 5. Fault Tolerance Metrics

#### Availability
- **Current**: ~99% (single broker, no replication)
- **Target**: 99.9% (3 brokers, RF=3)
- **Formula**: `Availability = Uptime / Total_Time`

#### Recovery Time
- **Current**: N/A (no replication)
- **Target**: < 30 seconds (automatic failover)
- **Components**:
  - Broker failure detection: 5-10 seconds
  - Leader election: 10-15 seconds
  - Consumer rebalancing: 5-10 seconds

#### Data Durability
- **Current**: Low (RF=1, single broker)
- **Target**: High (RF=3, min.insync.replicas=2)
- **Formula**: `Durability = 1 - (Failure_Rate ^ Replication_Factor)`

### 6. Cost Metrics

#### Infrastructure Cost
- **Current**: 1 server (development)
- **Target**: 5-7 servers (production)
  - 3 Kafka brokers
  - 1-2 Producer servers
  - 1-2 Consumer/Processing servers

#### Cost per Message
- **Current**: ~$0.00001 per message (estimated)
- **Target**: ~$0.000005 per message (economies of scale)

### 7. Monitoring Dashboard Metrics

**Key Metrics to Track:**

1. **Producer Metrics**
   - Messages sent per second
   - Message size distribution
   - Error rate
   - Producer lag (if using timestamps)

2. **Kafka Metrics**
   - Topic throughput (messages/second)
   - Partition distribution
   - Broker CPU/Memory/Disk
   - Replication lag
   - Under-replicated partitions

3. **Consumer Metrics**
   - Messages consumed per second
   - Consumer lag (per partition, per group)
   - Processing latency
   - Error rate
   - Rebalancing events

4. **System Metrics**
   - End-to-end latency (P50, P95, P99)
   - Throughput trends
   - Resource utilization (CPU, Memory, Network)
   - Error rates and exceptions

**Grafana Dashboard Panels:**
```
┌─────────────────────────────────────────────────────────┐
│  Scaling Metrics Dashboard                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Producer Throughput]  [Consumer Throughput]           │
│  [Partition Distribution]  [Consumer Lag]               │
│  [End-to-End Latency]  [Error Rate]                     │
│  [CPU Utilization]  [Memory Utilization]               │
│  [Network Bandwidth]  [Replication Status]              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase 1: Producer Scaling (Week 1-2)
- [ ] Implement multi-producer architecture
- [ ] Add driver-based producer assignment
- [ ] Optimize batch sizes and compression
- [ ] Add producer metrics collection
- [ ] Test with 4 producers, 10 drivers

**Expected Outcome**: 4x throughput increase

### Phase 2: Partition Scaling (Week 2-3)
- [ ] Increase telemetry partitions to 16
- [ ] Increase alerts partitions to 8
- [ ] Increase predictions partitions to 8
- [ ] Re-partition existing data (if needed)
- [ ] Update partitioning logic

**Expected Outcome**: Support for 16 parallel consumers

### Phase 3: Consumer Scaling (Week 3-4)
- [ ] Deploy multiple consumers per group
- [ ] Implement consumer pool management
- [ ] Add consumer metrics and monitoring
- [ ] Test with 8 consumers per group
- [ ] Optimize consumer processing

**Expected Outcome**: 4x processing capacity

### Phase 4: Kafka Cluster (Week 4-5)
- [ ] Deploy 3-broker Kafka cluster
- [ ] Set replication factor to 3
- [ ] Configure min.insync.replicas=2
- [ ] Test failover scenarios
- [ ] Monitor replication lag

**Expected Outcome**: 99.9% availability, fault tolerance

### Phase 5: Distributed Cache (Week 5-6)
- [ ] Replace in-memory cache with Redis
- [ ] Implement distributed caching
- [ ] Add cache replication
- [ ] Optimize cache access patterns
- [ ] Monitor cache hit rates

**Expected Outcome**: Shared cache across producers

### Phase 6: Load Balancing (Week 6-7)
- [ ] Deploy load balancer for Grafana bridge
- [ ] Implement session affinity
- [ ] Add health checks
- [ ] Monitor load distribution
- [ ] Test failover

**Expected Outcome**: High availability for visualization

### Phase 7: Monitoring & Optimization (Week 7-8)
- [ ] Deploy comprehensive monitoring (Prometheus + Grafana)
- [ ] Create scaling metrics dashboard
- [ ] Set up alerts for key metrics
- [ ] Performance tuning
- [ ] Load testing and optimization

**Expected Outcome**: Production-ready, monitored system

---

## Scaling Recommendations

### For Development/Testing
- **Current setup is sufficient**
- Single broker, single producer, single consumer per group
- Focus on functionality over scale

### For Small Production (10-20 drivers)
- **2 Producers** (handle 5-10 drivers each)
- **8 Partitions** (telemetry topic)
- **2 Consumers** per consumer group
- **Single Broker** (with RF=1, acceptable for small scale)
- **Expected Throughput**: ~7,500 msg/s

### For Medium Production (20-50 drivers)
- **4 Producers** (handle 5-12 drivers each)
- **16 Partitions** (telemetry topic)
- **4 Consumers** per consumer group
- **3-Broker Cluster** (RF=3)
- **Distributed Cache** (Redis)
- **Expected Throughput**: ~15,000 msg/s

### For Large Production (50+ drivers, multiple races)
- **8+ Producers** (handle 6-8 drivers each)
- **32 Partitions** (telemetry topic)
- **8-16 Consumers** per consumer group
- **5-Broker Cluster** (RF=3)
- **Distributed Cache** (Redis Cluster)
- **Load Balancer** for bridge services
- **Expected Throughput**: ~30,000+ msg/s

---

## Conclusion

The current F1 Telemetry Pipeline architecture is well-designed for development and small-scale production. With the scaling strategies outlined in this document, the system can scale from handling 3 drivers at 2,200 msg/s to 20+ drivers at 30,000+ msg/s while maintaining low latency and high availability.

**Key Takeaways:**
1. **Horizontal scaling** (more instances) is preferred over vertical scaling (bigger instances)
2. **Partition count** determines maximum parallelism
3. **Kafka cluster** provides fault tolerance and better performance
4. **Monitoring** is critical for scaling decisions
5. **Incremental scaling** allows testing and optimization at each stage

The metrics provided in this document serve as a baseline for measuring scaling effectiveness and identifying bottlenecks as the system grows.

