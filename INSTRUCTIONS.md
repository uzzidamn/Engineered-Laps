# Step-by-Step Execution Instructions

This document provides detailed instructions for executing each step of the F1 Real-Time Telemetry Streaming Pipeline, following the project document structure.

## Prerequisites

Before starting, ensure:
1. ✅ Python 3.8+ installed
2. ✅ Java JDK 11+ installed
3. ✅ Kafka installed and `KAFKA_HOME` environment variable set
4. ✅ Virtual environment created and dependencies installed
5. ✅ Kafka services started (`bash scripts/start_kafka.sh`)

---

## Step 1: Data Preparation

**Objective:**  
Export historic race session data from FastF1 API for use as the streaming source.

### Instructions:

1. **Open notebook:**
   ```bash
   jupyter notebook notebooks/01_data_preparation.ipynb
   ```

2. **Run all cells:**
   - The notebook will:
     - Load FastF1 session data (2023 Monaco Race by default)
     - Extract telemetry fields (Speed, LapNumber, Timestamp, DriverID, Compound, etc.)
     - Calculate data frequency from timestamps
     - Export to CSV and Parquet formats

3. **Validation:**
   - ✅ File loads without errors
   - ✅ Data columns are as expected (check `df.head()` output)
   - ✅ Frequency calculated (typically 10-20 Hz)
   - ✅ Both CSV and Parquet files created in `data/` directory

### Expected Output:
```
✅ Data extraction complete
Total records: [number]
Columns: [list of columns]
✅ Data frequency calculated: 15.23 Hz (avg interval: 65.67 ms)
✅ CSV exported: data/2023_Monaco_Race_[timestamp].csv
✅ Parquet exported: data/2023_Monaco_Race_[timestamp].parquet
```

### Troubleshooting:
- **No data available**: Check internet connection, FastF1 cache may need time to download
- **Missing columns**: Verify FastF1 session loaded successfully
- **Export failed**: Check `data/` directory permissions

---

## Step 2: Temporary Cache Setup

**Objective:**  
Create a script to hold session data and serve rows for streaming.

### Instructions:

1. **Open notebook:**
   ```bash
   jupyter notebook notebooks/02_cache_setup.ipynb
   ```

2. **Run all cells:**
   - The notebook will:
     - Load CSV/Parquet file into memory
     - Create iterable cache structure
     - Calculate streaming frequency
     - Validate row-by-row iteration

3. **Validation:**
   - ✅ Can iterate/stream rows one-by-one
   - ✅ Data freshness (row reflects realistic event order)
   - ✅ Timestamps are in chronological order
   - ✅ Frequency matches Step 1 calculation

### Expected Output:
```
✅ Cache loaded: [number] records
✅ Frequency: 15.23 Hz
✅ Cache iteration successful: 5 records retrieved
✅ Data is ordered chronologically (realistic event order)
```

### Troubleshooting:
- **No data files**: Run Step 1 first to create data files
- **Cache iteration fails**: Check file format (CSV or Parquet)
- **Timestamps out of order**: Verify data integrity from Step 1

---

## Step 3: Kafka Producer Implementation

**Objective:**  
Stream telemetry data from cache at the real telemetry frequency.

### Instructions:

1. **Ensure Kafka is running:**
   ```bash
   bash scripts/start_kafka.sh
   ```

2. **Open notebook:**
   ```bash
   jupyter notebook notebooks/03_kafka_producer.ipynb
   ```

3. **Run all cells:**
   - The notebook will:
     - Load data into cache
     - Initialize Kafka producer
     - Stream messages at FastF1 frequency (using timestamp-based intervals)
     - Send JSON payloads to topic "f1-speed-stream"

4. **Validation:**
   - ✅ Messages arrive in topic (use Kafka console consumer to verify)
   - ✅ Order preserved (compare order between cache and messages)
   - ✅ Frequency correct (measure interval between produced messages)

### Verify Messages:
```bash
# In another terminal
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
    --topic f1-speed-stream --from-beginning
```

### Expected Output:
```
✅ Producer initialized
✅ Cache loaded: [number] records
✅ Frequency: 15.23 Hz
Starting Kafka producer stream...
Streamed 100 messages in 6.5s (15.4 msg/s)
✅ Streaming completed: [number] messages in [time]s
```

### Troubleshooting:
- **Kafka connection failed**: Ensure Kafka is running (`bash scripts/start_kafka.sh`)
- **No messages sent**: Check topic exists (run Step 4 first)
- **Frequency incorrect**: Verify cache frequency matches data frequency
- **Order not preserved**: Check cache iteration order

---

## Step 4: Kafka Broker/Topic Configuration

**Objective:**  
Set up the Kafka broker with required topic(s) and partitions.

### Instructions:

1. **Open notebook:**
   ```bash
   jupyter notebook notebooks/04_kafka_topic_setup.ipynb
   ```

2. **Run all cells:**
   - The notebook will:
     - Connect to Kafka admin client
     - Create topic "f1-speed-stream" with N partitions (default: 4)
     - Validate topic creation and partitioning

3. **Validation:**
   - ✅ Topic exists
   - ✅ Correct partitioning (`kafka-topics.sh --list`)
   - ✅ Can inspect message count with `kafka-console-consumer`

### Verify Topic:
```bash
kafka-topics.sh --list --bootstrap-server localhost:9092
kafka-topics.sh --describe --topic f1-speed-stream --bootstrap-server localhost:9092
```

### Expected Output:
```
✅ Connected to Kafka
Creating topic 'f1-speed-stream' with 4 partitions...
✅ Topic 'f1-speed-stream' created successfully
✅ Topic exists
✅ Partition count: 4 (expected: 4)
✅ Partitioning correct
```

### Troubleshooting:
- **Topic already exists**: This is fine, the script handles existing topics
- **Partition mismatch**: Delete and recreate topic if needed
- **Kafka connection failed**: Ensure Kafka is running

---

## Step 5: Kafka Consumer & Real-Time Analysis App

**Objective:**  
Consume streamed telemetry, run analytics or ML on each incoming message.

### Instructions:

1. **Ensure producer is running** (Step 3) or messages exist in topic

2. **Open notebook:**
   ```bash
   jupyter notebook notebooks/05_kafka_consumer.ipynb
   ```

3. **Run all cells:**
   - The notebook will:
     - Subscribe to "f1-speed-stream" topic
     - Parse JSON messages
     - Run real-time analysis (anomaly detection)
     - Integrate ML inference (if models available)
     - Record per-message latency

4. **Validation:**
   - ✅ Consumer receives each message as sent
   - ✅ Analysis completes with expected output for every message
   - ✅ Latency logged; aggregate stats available

### Expected Output:
```
✅ Consumer initialized
Starting message consumption...
Processed 100 messages in 6.5s (15.4 msg/s, avg latency: 5.23 ms)
✅ Consumption completed: [number] messages in [time]s
Average rate: 15.4 msg/s, Average latency: 5.23 ms
```

### Troubleshooting:
- **No messages received**: Start producer first (Step 3) or check topic has data
- **High latency**: Check ML models loading (run Step 6 first)
- **Analysis errors**: Verify message format matches expected schema

---

## Step 6: ML Model Training and Deployment

**Objective:**  
Train model on separate race data, deploy for instant inference in consumer.

### Instructions:

1. **Open notebook:**
   ```bash
   jupyter notebook notebooks/06_ml_model_training.ipynb
   ```

2. **Run all cells:**
   - The notebook will:
     - Load training data (different session than streaming)
     - Prepare features and labels
     - Train models (crash_risk, tire_failure, pit_stop_probability)
     - Validate with cross-validation (accuracy, F1, ROC-AUC, confusion matrix)
     - Save trained models (joblib `.pkl` files)
     - Test inference latency

3. **Validation:**
   - ✅ Model loads without error
   - ✅ Responds in <10ms per inference
   - ✅ Predictions are sensible given event history

### Expected Output:
```
✅ Training data loaded: [number] records
Training crash_risk model...
  Accuracy: 0.9234
  F1 Score: 0.8156
  ROC-AUC: 0.9123
  CV Accuracy: 0.9156 (+/- 0.0234)
✅ All models trained successfully
✅ Saved model: models/crash_risk_model.pkl
✅ Inference Latency: Avg 3.45 ms (✅ <10ms requirement met)
```

### Troubleshooting:
- **Low accuracy**: Training data may be imbalanced, adjust labels or use different session
- **High latency**: Reduce model complexity or optimize feature extraction
- **Models not saving**: Check `models/` directory permissions

---

## Step 7: Weak Scaling Demonstration

**Objective:**  
Show effect of increased resources on analysis throughput/latency.

### Instructions:

1. **Ensure producer is streaming** (run Step 3 in background or separate terminal)

2. **Open notebook:**
   ```bash
   jupyter notebook notebooks/07_weak_scaling_demo.ipynb
   ```

3. **Run all cells:**
   - The notebook will:
     - Launch multiple consumers (threads), each reading separate partition
     - Replay multiple streams in parallel
     - Log per-event and aggregate latency, throughput
     - Visualize: Number of consumers vs. latency & events/sec

4. **Validation:**
   - ✅ Latency remains flat or near-constant as number of consumers/streams grow
   - ✅ Throughput rises appropriately

### Expected Output:
```
Running scenario: 2 consumers
Results:
  Total messages: [number]
  Throughput: [number] msg/s
  Avg latency: [number] ms

Running scenario: 4 consumers
...
📊 Scaling Results Summary:
[Table showing scaling metrics]
```

### Visualization:
- Throughput vs. Consumers (should increase)
- Latency vs. Consumers (should remain stable)
- Messages vs. Consumers (should increase)

### Troubleshooting:
- **Latency increases with consumers**: May need more Kafka partitions or better resource allocation
- **Throughput not scaling**: Check partition distribution and consumer group configuration
- **No data processed**: Ensure producer is running and streaming data

---

## Step 8: Dashboard Creation

**Objective:**  
Visualize real-time analysis, ML predictions, and scaling metrics.

### Instructions:

1. **Ensure producer is streaming** (Step 3)

2. **Open notebook:**
   ```bash
   jupyter notebook notebooks/08_live_dashboard.ipynb
   ```

3. **Launch Streamlit dashboard:**
   ```bash
   streamlit run src/dashboard.py
   ```

   Or run notebook cells to test dashboard functionality.

4. **Dashboard Features:**
   - Real-time telemetry (current speed, lap number, driver ID, compound)
   - ML predictions (pit stop likelihood, anomaly flags)
   - Processing latency/throughput charts
   - Scaling trend graphs (if Step 7 completed)

5. **Validation:**
   - ✅ Dashboard auto-refreshes (at FastF1 frequency: 50-100ms)
   - ✅ All metrics update in real-time
   - ✅ Historical/past event logs viewable
   - ✅ Timestamps move in real-time

### Dashboard URL:
```
http://localhost:8501
```

### Expected Behavior:
- Auto-refresh every 50-100ms
- Real-time graph updates
- Live telemetry metrics
- ML prediction probabilities
- Anomaly alerts
- Latency metrics

### Troubleshooting:
- **Dashboard not updating**: 
  - Check producer is running
  - Verify Kafka topic has messages
  - Check refresh interval in config
- **No data displayed**: 
  - Start consumer to populate dashboard
  - Check Kafka connection
- **High refresh lag**: 
  - Reduce refresh interval
  - Optimize dashboard code
  - Check system resources

---

## Complete Pipeline Workflow

For a complete end-to-end run:

```bash
# 1. Start Kafka
bash scripts/start_kafka.sh

# 2. Terminal 1: Start Producer
cd f1_streaming_pipeline
source venv/bin/activate
python -c "from src.kafka_producer import RealTimeProducer; p = RealTimeProducer(); p.load_cache('data/[latest_file]'); p.stream_at_frequency(duration_seconds=300)"

# 3. Terminal 2: Start Consumer
python -c "from src.kafka_consumer import RealTimeConsumer; c = RealTimeConsumer(); c.consume_messages(timeout_seconds=300)"

# 4. Terminal 3: Start Dashboard
streamlit run src/dashboard.py
```

---

## Validation Checklist

After completing all steps, verify:

- [ ] Step 1: Data exported successfully
- [ ] Step 2: Cache can iterate row-by-row
- [ ] Step 3: Messages arrive in Kafka topic
- [ ] Step 4: Topic created with correct partitions
- [ ] Step 5: Consumer processes all messages
- [ ] Step 6: Models trained and inference <10ms
- [ ] Step 7: Latency stable with scaling
- [ ] Step 8: Dashboard updates in real-time

---

## Tips and Best Practices

1. **Run notebooks in order**: Each step depends on previous steps
2. **Use separate terminals**: Run producer, consumer, and dashboard simultaneously for full pipeline
3. **Monitor Kafka**: Use `kafka-console-consumer` to verify messages
4. **Check logs**: Review notebook outputs and Python logs for errors
5. **Resource management**: Ensure sufficient memory/CPU for multiple consumers
6. **Frequency matching**: Verify producer frequency matches data frequency

---

**For detailed component documentation, see `README.md`**

