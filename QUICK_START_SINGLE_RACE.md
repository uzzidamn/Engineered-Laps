# 🏁 Quick Start: Single Race Producer

## 🎯 What I Created

I've created a **single-race producer** that stops automatically after streaming one complete race. This is perfect for your project demo and reduces CPU usage.

## 📦 New Files Created

1. **`scripts/simple_producer_once.py`** - Main script (streams once and exits)
2. **`scripts/stop_producer.sh`** - Helper to stop running producers
3. **`scripts/start_producer_once.sh`** - Helper to start single-race producer
4. **`PRODUCER_GUIDE.md`** - Complete documentation

## 🚀 How to Use (3 Simple Steps)

### Step 1: Stop Current Producer

Your infinite-loop producer has been running for 7+ hours. Stop it first:

```bash
cd "/Users/Ujjwal/Documents/DE Project/f1_streaming_pipeline"
./scripts/stop_producer.sh
```

Or manually:
```bash
kill -SIGINT 37426
```

### Step 2: Start Single-Race Producer

**Option A: Using the helper script (easiest)**
```bash
./scripts/start_producer_once.sh
```

**Option B: Run directly**
```bash
source venv/bin/activate
python scripts/simple_producer_once.py
```

### Step 3: Watch It Run

The producer will:
- ✅ Stream the entire Bahrain GP race (~110 seconds at 1.0x speed)
- ✅ Send ~770,000 messages to Kafka
- ✅ Exit automatically when complete
- ✅ Show final statistics

## 📊 What to Expect

```
🏎️  F1 Kafka Producer (Single Race)
============================================================
📂 Loading data from: 2023_Monaco_Race_20251119_182219.parquet
🏁 Monitoring drivers: VER, HAM, LEC
✅ Loaded 770,500 records

============================================================
   🚀 Starting Kafka Producer (ONE RACE ONLY)
============================================================

📡 Streaming F1 telemetry to Kafka...
   Topic: f1-telemetry
   Speed factor: 1.0x (real-time)
   Mode: Single race (will stop after completion)

💡 Open Grafana dashboard: http://localhost:3000

[Streaming messages...]

============================================================
   ✅ RACE COMPLETED!
============================================================

📊 Statistics:
   • Messages sent: 770,500
   • Duration: 110.2 seconds
   • Average rate: 6,992 msg/s
   • Records processed: 770,500

🏁 Producer finished. Exiting gracefully.
```

## ⚡ Comparison

| Feature | `simple_producer.py` | `simple_producer_once.py` ✨ |
|---------|---------------------|----------------------------|
| **Mode** | Infinite loop | Single race |
| **Runtime** | Forever (manual stop) | ~2 minutes (auto-stop) |
| **CPU Usage** | 99%+ continuously | 50-99% for 2 minutes |
| **Messages** | Unlimited | ~770K per run |
| **Use Case** | Long demos, testing | Project demo, testing |
| **Exit** | Ctrl+C required | Automatic |

## 🎓 For Your Project Demo

When demonstrating for your project:

1. **Stop any running producers:**
   ```bash
   ./scripts/stop_producer.sh
   ```

2. **Start Grafana (if not running):**
   ```bash
   brew services start grafana
   # or
   /opt/homebrew/opt/grafana/bin/grafana server &
   ```

3. **Start Grafana bridge (if not running):**
   ```bash
   ./scripts/start_grafana_bridge.sh
   ```

4. **Run single race:**
   ```bash
   ./scripts/start_producer_once.sh
   ```

5. **Monitor in Grafana:**
   - Open http://localhost:3000
   - Login: admin/admin
   - Watch real-time telemetry for 2 minutes
   - Show final statistics

6. **Check consumer performance:**
   ```bash
   /opt/homebrew/bin/kafka-consumer-groups \
     --bootstrap-server localhost:9092 \
     --describe --group grafana_bridge
   ```

## 🔧 Customization

### Run Faster (2x speed)
Edit `simple_producer_once.py` line 79:
```python
speed_factor=2.0,  # Completes in ~55 seconds
```

### Different Drivers
Edit line 39:
```python
drivers = ['VER', 'NOR', 'SAI']  # Any 3 drivers
```

### Limited Duration (for quick tests)
Edit line 81:
```python
duration_seconds=60  # Only stream for 1 minute
```

## 📈 Current Status

**Before (7+ hours ago):**
```
✅ Started: simple_producer.py (infinite loop)
🔄 Status: Running continuously
📊 Messages: 72+ million sent
⚡ CPU: 99.6% usage
```

**After (when you run new version):**
```
✅ Will start: simple_producer_once.py (single race)
⏱️ Duration: ~2 minutes
📊 Messages: ~770K per run
⚡ CPU: 50-99% for 2 minutes only
🎯 Result: Clean exit with statistics
```

## 💡 Benefits for Your Project Report

1. **Cleaner Demo:** Shows complete race cycle
2. **Measurable Results:** Clear start/end with statistics
3. **Resource Efficient:** Lower CPU usage
4. **Professional:** Graceful exit, not killed
5. **Reproducible:** Same results every time
6. **Evidence:** Can capture full output for report

## 🆘 Troubleshooting

### Producer Won't Stop
```bash
# Force kill
pkill -9 -f simple_producer
```

### Kafka Not Running
```bash
# Start Kafka
/opt/homebrew/bin/kafka-server-start \
  /opt/homebrew/etc/kafka/server.properties &
```

### Want to Test Without Waiting 2 Minutes
```bash
# Edit script to use 10x speed
# Change line 79: speed_factor=10.0
# Race completes in ~11 seconds
```

## ✅ Next Steps

1. Stop the current infinite-loop producer
2. Run the single-race version
3. Capture the output statistics
4. Screenshot Grafana dashboard
5. Add performance metrics to your report

---

**Ready to switch?** Run this now:
```bash
cd "/Users/Ujjwal/Documents/DE Project/f1_streaming_pipeline"
./scripts/stop_producer.sh
./scripts/start_producer_once.sh
```

🏎️ **Your dashboard will show the same real-time Kafka data, just with a cleaner start/stop!**

