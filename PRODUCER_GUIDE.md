# Kafka Producer Guide

## 🚀 Two Producer Options

### Option 1: Infinite Loop Producer (for continuous demo)
**File:** `scripts/simple_producer.py`

- ✅ Streams race data continuously
- ✅ Replays the race in an infinite loop
- ✅ Great for long-running demos/dashboards
- ⚠️ High CPU usage (99%+)
- ⚠️ Needs manual stop (Ctrl+C)

**Usage:**
```bash
cd "/Users/Ujjwal/Documents/DE Project/f1_streaming_pipeline"
source venv/bin/activate
python scripts/simple_producer.py
```

### Option 2: Single Race Producer (NEW!)
**File:** `scripts/simple_producer_once.py`

- ✅ Streams race data ONCE and stops
- ✅ Exits gracefully after completion
- ✅ Lower CPU usage
- ✅ Perfect for testing and project demos
- ⏱️ Runtime: ~2 hours (at 1.0x speed)

**Usage:**
```bash
cd "/Users/Ujjwal/Documents/DE Project/f1_streaming_pipeline"
source venv/bin/activate
python scripts/simple_producer_once.py
```

## 🛑 Stop Current Running Producer

### Step 1: Find the Producer Process
```bash
ps aux | grep simple_producer | grep -v grep
```

### Step 2: Kill the Process
```bash
# Option A: Kill by process ID (use PID from ps command)
kill -SIGINT 37426  # Replace 37426 with actual PID

# Option B: Kill all simple_producer processes
pkill -SIGINT -f simple_producer.py
```

### Step 3: Verify it's stopped
```bash
ps aux | grep simple_producer | grep -v grep
# Should return nothing
```

## 📊 Monitor Producer Status

### Check if producer is running
```bash
ps aux | grep -E "simple_producer|run_producer" | grep -v grep
```

### Check Kafka topics
```bash
/opt/homebrew/bin/kafka-topics --bootstrap-server localhost:9092 --list
```

### Check consumer lag (is data being consumed?)
```bash
/opt/homebrew/bin/kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group grafana_bridge
```

### View recent messages
```bash
/opt/homebrew/bin/kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic f1-telemetry \
  --max-messages 5
```

## ⚡ Quick Start (Recommended Workflow)

### For Testing/Development
```bash
# Stop any running producers
pkill -SIGINT -f simple_producer

# Run single race
cd "/Users/Ujjwal/Documents/DE Project/f1_streaming_pipeline"
source venv/bin/activate
python scripts/simple_producer_once.py
```

### For Long Demo/Presentation
```bash
# Stop any running producers
pkill -SIGINT -f simple_producer

# Run infinite loop
cd "/Users/Ujjwal/Documents/DE Project/f1_streaming_pipeline"
source venv/bin/activate
python scripts/simple_producer.py
```

## 🎛️ Customization Options

### Change Drivers
Edit the script and modify line 39:
```python
drivers = ['VER', 'HAM', 'LEC']  # Change to any driver codes
```

Available drivers depend on your race data. Common codes:
- VER (Verstappen)
- HAM (Hamilton)
- LEC (Leclerc)
- NOR (Norris)
- SAI (Sainz)
- RUS (Russell)
- PER (Perez)

### Change Speed Factor
Modify the `speed_factor` parameter:
```python
producer.stream_at_frequency(
    speed_factor=2.0,  # 2.0 = 2x speed, 0.5 = half speed
    ...
)
```

### Stream for Limited Duration
```python
producer.stream_at_frequency(
    speed_factor=1.0,
    duration_seconds=300,  # Only stream for 5 minutes
    ...
)
```

## 🔍 Troubleshooting

### Producer won't start
**Error:** `kafka.errors.NoBrokersAvailable`
**Solution:** Start Kafka first
```bash
/opt/homebrew/bin/kafka-server-start /opt/homebrew/etc/kafka/server.properties &
```

### No data files found
**Error:** `No data files found in data/ directory`
**Solution:** Run data preparation first
```bash
cd "/Users/Ujjwal/Documents/DE Project/f1_streaming_pipeline"
source venv/bin/activate
jupyter notebook notebooks/01_data_preparation.ipynb
```

### High CPU usage
**Issue:** Producer using 99% CPU
**Solutions:**
1. Use single-race version instead of infinite loop
2. Reduce speed_factor (e.g., 0.5 for half speed)
3. Add driver filtering to reduce message volume

### Producer seems stuck
**Issue:** No output for long time
**Check:**
```bash
# View producer logs
tail -f producer.log

# Check Kafka connection
telnet localhost 9092
```

## 📈 Performance Stats

### Expected Performance (2020 Bahrain GP)
- **Total messages:** ~770,000 per race
- **Duration (1.0x speed):** ~110 seconds
- **Average rate:** ~6,900 msg/s
- **Data size:** ~330 MB (uncompressed)
- **CPU usage:** 50-99% (depends on speed factor)

### Optimization Tips
1. Use Parquet files instead of CSV (faster loading)
2. Reduce driver count (fewer messages)
3. Enable Kafka compression (already enabled: gzip)
4. Increase batch size for higher throughput

## 🎯 Current Status

**Currently Running:**
```
PID: 37426
Script: simple_producer.py (INFINITE LOOP version)
Runtime: 7+ hours
Messages sent: 72+ million
CPU usage: 99.6%
Status: Active (looping)
```

**Recommendation:** 
Stop the infinite loop producer and switch to single-race version:
```bash
kill -SIGINT 37426
python scripts/simple_producer_once.py
```

## 💡 Pro Tips

1. **Use tmux/screen** for long-running producers:
   ```bash
   tmux new -s producer
   python scripts/simple_producer.py
   # Ctrl+B, then D to detach
   tmux attach -t producer  # Re-attach later
   ```

2. **Redirect output to log file:**
   ```bash
   python scripts/simple_producer.py > producer_$(date +%Y%m%d_%H%M%S).log 2>&1
   ```

3. **Monitor in real-time:**
   ```bash
   # Terminal 1: Run producer
   python scripts/simple_producer_once.py
   
   # Terminal 2: Monitor Kafka
   watch -n 1 '/opt/homebrew/bin/kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group grafana_bridge'
   ```

4. **For project demo/submission:**
   - Use `simple_producer_once.py` (cleaner, exits automatically)
   - Capture statistics at the end
   - Screenshot Grafana dashboard while running
   - Show consumer lag metrics

---

**Need help?** Check the main README.md or INSTRUCTIONS.md for more details.

