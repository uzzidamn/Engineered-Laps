# Grafana Setup Guide for F1 Streaming Pipeline

This guide will walk you through installing Grafana and integrating it with your F1 streaming pipeline using the Kafka bridge service.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Install Grafana](#install-grafana)
3. [Install Required Python Packages](#install-required-python-packages)
4. [Configure Grafana](#configure-grafana)
5. [Start the Bridge Service](#start-the-bridge-service)
6. [Configure Grafana Data Source](#configure-grafana-data-source)
7. [Import Dashboard](#import-dashboard)
8. [Verification](#verification)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- ✅ macOS (for Homebrew installation)
- ✅ Python 3.8+ with virtual environment activated
- ✅ Kafka broker running on `localhost:9092`
- ✅ F1 streaming pipeline repository cloned
- ✅ Kafka topics created (`f1-telemetry`, `f1-alerts`)

## Install Grafana

### Option 1: Homebrew (Recommended for macOS)

```bash
# Install Grafana
brew install grafana

# Start Grafana service
brew services start grafana

# Verify installation
brew services list | grep grafana
```

### Option 2: Docker

```bash
docker run -d \
  -p 3000:3000 \
  --name=grafana \
  -v "$PWD/grafana/provisioning:/etc/grafana/provisioning" \
  -v "$PWD/grafana/dashboards:/var/lib/grafana/dashboards" \
  grafana/grafana-oss:latest
```

### Option 3: Manual Download

Download from: https://grafana.com/grafana/download

Grafana will be accessible at: **http://localhost:3000**

Default credentials:
- **Username**: `admin`
- **Password**: `admin` (you'll be prompted to change this on first login)

---

## Install Required Python Packages

The bridge service requires Flask and Flask-CORS:

```bash
# Activate your virtual environment
source venv/bin/activate

# Install dependencies
pip install flask flask-cors

# Or update from requirements.txt
pip install -r requirements.txt
```

---

## Configure Grafana

### Step 1: Install JSON API Plugin

The bridge service uses Grafana's Simple JSON datasource plugin:

```bash
# Install plugin
grafana-cli plugins install grafana-simple-json-datasource

# Restart Grafana (if using Homebrew)
brew services restart grafana

# If using Docker
docker restart grafana
```

### Step 2: Update Grafana Configuration (Optional)

If you want to use auto-provisioning, configure Grafana to load from your project directory.

Edit Grafana config file:

**macOS (Homebrew)**: `/opt/homebrew/etc/grafana/grafana.ini`

Add/update these sections:

```ini
[paths]
provisioning = /Users/YOUR_USERNAME/Documents/DE Project/f1_streaming_pipeline/grafana/provisioning

[dashboards]
default_home_dashboard_path = /Users/YOUR_USERNAME/Documents/DE Project/f1_streaming_pipeline/grafana/dashboards/f1_consolidated.json
```

**Important**: Replace `YOUR_USERNAME` with your actual username.

Restart Grafana after making changes:

```bash
brew services restart grafana
```

---

## Start the Bridge Service

The Kafka-to-Grafana bridge service must be running for the dashboard to receive data.

### Step 1: Verify Kafka is Running

```bash
# Check if Kafka broker is accessible
nc -z localhost 9092 && echo "Kafka is running" || echo "Kafka is not running"

# If not running, start it
./scripts/start_kafka.sh
```

### Step 2: Start the Bridge Service

```bash
# Make script executable (first time only)
chmod +x scripts/start_grafana_bridge.sh

# Start the bridge
./scripts/start_grafana_bridge.sh
```

You should see output like:

```
========================================
   F1 Grafana Kafka Bridge Service
========================================

✓ Virtual environment found
✓ Configuration file found
✓ Kafka broker is running on localhost:9092

========================================
   Starting Bridge Service
========================================

Service will be available at:
  • Bridge API: http://localhost:5001
  • Stats: http://localhost:5001/stats
  • Drivers: http://localhost:5001/drivers

Configure Grafana datasource:
  • Type: JSON API
  • URL: http://localhost:5001
```

### Step 3: Verify Bridge is Running

Open a new terminal and test the bridge:

```bash
# Health check
curl http://localhost:5001/

# Get statistics
curl http://localhost:5001/stats

# List active drivers
curl http://localhost:5001/drivers
```

---

## Configure Grafana Data Source

If not using auto-provisioning, manually configure the data source:

### Step 1: Login to Grafana

1. Navigate to http://localhost:3000
2. Login with `admin` / `admin`
3. Change password when prompted

### Step 2: Add Data Source

1. Click **⚙️ Configuration** → **Data Sources**
2. Click **Add data source**
3. Search for and select **JSON API** (or **SimpleJson**)
4. Configure:
   - **Name**: `F1 Kafka Bridge`
   - **URL**: `http://localhost:5001`
   - **Access**: `Server (default)`
5. Click **Save & Test**

You should see: ✅ **Data source is working**

---

## Import Dashboard

### Option 1: Auto-Provisioning (If configured)

If you set up provisioning correctly, the dashboard will automatically appear in:

**Dashboards** → **F1 Racing** → **F1 Real-Time Telemetry Dashboard**

### Option 2: Manual Import

1. Click **+** → **Import**
2. Click **Upload JSON file**
3. Select: `grafana/dashboards/f1_consolidated.json`
4. Select data source: **F1 Kafka Bridge**
5. Click **Import**

---

## Verification

### Step 1: Start Kafka Producer

In a separate terminal, start streaming F1 telemetry data:

```bash
# Start producer (from Dash dashboard or script)
python scripts/run_producer.py
```

Or use the Dash dashboard:

```bash
python scripts/f1_dash_dashboard.py
```

Then start streaming from the UI.

### Step 2: Check Bridge is Receiving Data

```bash
# Watch statistics update
watch -n 1 curl -s http://localhost:5001/stats

# Sample output:
# {
#   "running": true,
#   "messages_received": 1234,
#   "alerts_received": 12,
#   "uptime_seconds": 45.6,
#   "drivers_count": 3
# }
```

### Step 3: View Dashboard

1. Open Grafana: http://localhost:3000
2. Navigate to **F1 Real-Time Telemetry Dashboard**
3. Set time range to **Last 5 minutes** (top right)
4. Set refresh interval to **1s** (top right dropdown)

You should see:
- ✅ Real-time speed, RPM, throttle, and gear charts
- ✅ Wheel spin analysis
- ✅ Gear anomaly detection
- ✅ Active drivers list
- ✅ Live statistics updating every second

---

## Troubleshooting

### Issue: "Data source is not working"

**Solution**:
```bash
# 1. Check bridge is running
curl http://localhost:5001/

# 2. Check bridge logs
tail -f logs/grafana_bridge.log

# 3. Restart bridge service
# Press Ctrl+C in bridge terminal, then restart:
./scripts/start_grafana_bridge.sh
```

### Issue: "No data points" in dashboard

**Possible causes**:

1. **Kafka producer not running**
   ```bash
   # Start producer
   python scripts/run_producer.py
   ```

2. **No data in time range**
   - Change time range to "Last 5 minutes"
   - Ensure data is being produced recently

3. **Bridge not receiving messages**
   ```bash
   # Check Kafka topics
   kafka-console-consumer.sh --bootstrap-server localhost:9092 \
     --topic f1-telemetry --from-beginning --max-messages 5
   ```

### Issue: "Error reading configuration"

**Solution**:
```bash
# Verify config file exists
ls -la config/grafana_bridge_config.yaml

# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config/grafana_bridge_config.yaml'))"
```

### Issue: Bridge crashes with "kafka.errors.NoBrokersAvailable"

**Solution**:
```bash
# Start Kafka
./scripts/start_kafka.sh

# Wait 10 seconds, then retry bridge
./scripts/start_grafana_bridge.sh
```

### Issue: "Cannot connect to Grafana"

**Solution**:
```bash
# Check if Grafana is running (Homebrew)
brew services list | grep grafana

# If not running, start it
brew services start grafana

# Check if port 3000 is in use
lsof -i :3000

# If port is taken by another process, stop it or configure Grafana to use different port
```

### Issue: JSON API plugin not found

**Solution**:
```bash
# Install plugin
grafana-cli plugins install grafana-simple-json-datasource

# Restart Grafana
brew services restart grafana

# Verify plugin is installed
grafana-cli plugins ls
```

---

## Performance Tips

### 1. Adjust Buffer Sizes

Edit `config/grafana_bridge_config.yaml`:

```yaml
buffer:
  max_points_per_driver: 2000  # Increase for longer history
  max_alerts: 1000
```

Restart bridge after changes.

### 2. Optimize Dashboard Refresh Rate

For better performance with many panels:
- Reduce refresh rate to 5s or 10s
- Reduce time range to "Last 1 minute"

### 3. Monitor Bridge Resource Usage

```bash
# Monitor CPU and memory
top -pid $(pgrep -f grafana_kafka_bridge)
```

---

## Next Steps

✅ Explore the **Grafana Dashboard Guide** for feature explanations

✅ Customize panels and queries

✅ Set up Grafana alerting for critical events

✅ Export and share dashboards with your team

---

## Useful Commands Reference

```bash
# Start Grafana
brew services start grafana

# Stop Grafana
brew services stop grafana

# Restart Grafana
brew services restart grafana

# Start Kafka
./scripts/start_kafka.sh

# Stop Kafka
./scripts/stop_kafka.sh

# Start Bridge
./scripts/start_grafana_bridge.sh

# Check Bridge Health
curl http://localhost:5001/stats

# Check Grafana Status
brew services list | grep grafana
```

---

## Additional Resources

- [Grafana Documentation](https://grafana.com/docs/)
- [JSON API Datasource Plugin](https://grafana.com/grafana/plugins/grafana-simple-json-datasource/)
- [Kafka Dashboard Guide](./KAFKA_DASHBOARD_GUIDE.md)
- [Main README](../README.md)

---

For issues or questions, please refer to the project documentation or open an issue on GitHub.

