# 🚀 Grafana Quick Start Guide

Get your F1 telemetry dashboard up and running in 5 minutes!

## ✅ What's Been Set Up

All code and configurations are ready:
- ✅ Kafka-to-Grafana bridge service
- ✅ Comprehensive Grafana dashboard JSON
- ✅ Auto-provisioning configurations
- ✅ Wheel spin and gear anomaly detection
- ✅ Real-time data streaming
- ✅ Startup and test scripts

## 📋 Prerequisites

Before starting, make sure you have:
1. ✅ Python virtual environment activated
2. ✅ Kafka installed and accessible
3. ✅ All Python dependencies installed (`pip install -r requirements.txt`)

## 🎯 Installation Steps

### Step 1: Install Grafana

**Due to Homebrew permission issues, see [GRAFANA_INSTALL_INSTRUCTIONS.txt](GRAFANA_INSTALL_INSTRUCTIONS.txt) for installation options.**

**Quick options:**
- Fix Homebrew and install: `brew install grafana`
- Use Docker: `docker run -d -p 3000:3000 grafana/grafana-oss`
- Download: https://grafana.com/grafana/download

### Step 2: Start Grafana

```bash
# If using Homebrew
brew services start grafana

# If using Docker
docker start grafana

# Access at http://localhost:3000 (admin/admin)
```

### Step 3: Install JSON API Plugin

```bash
# Homebrew
grafana-cli plugins install grafana-simple-json-datasource
brew services restart grafana

# Docker
docker exec grafana grafana-cli plugins install grafana-simple-json-datasource
docker restart grafana
```

## 🎬 Running the Complete Pipeline

### Terminal 1: Start Kafka

```bash
./scripts/start_kafka.sh
```

Wait ~10 seconds for Kafka to fully start.

### Terminal 2: Start Grafana Bridge

```bash
./scripts/start_grafana_bridge.sh
```

You should see:
```
✓ Kafka broker is running on localhost:9092
✓ Bridge service started successfully
Service will be available at: http://localhost:5001
```

### Terminal 3: Start F1 Data Producer

**Option A: Use existing Dash dashboard**
```bash
python scripts/f1_dash_dashboard.py
```
Then navigate to http://localhost:8050 and start streaming.

**Option B: Use producer script directly**
```bash
python scripts/run_producer.py
```

### Terminal 4: Test Bridge (Optional)

```bash
./scripts/test_grafana_bridge.sh
```

This verifies all endpoints are working correctly.

## 🖥️ Configure Grafana Dashboard

### Option 1: Manual Configuration (Recommended First Time)

1. **Open Grafana**: http://localhost:3000
2. **Login**: admin / admin (change password when prompted)
3. **Add Data Source**:
   - Click ⚙️ → Data Sources → Add data source
   - Search for "JSON API" (or "SimpleJson")
   - Configure:
     - Name: `F1 Kafka Bridge`
     - URL: `http://localhost:5001`
     - Access: Server (default)
   - Click "Save & Test" → Should show ✅ "Data source is working"

4. **Import Dashboard**:
   - Click + → Import
   - Upload: `grafana/dashboards/f1_consolidated.json`
   - Select data source: `F1 Kafka Bridge`
   - Click Import

5. **View Dashboard**:
   - Time range: Last 5 minutes
   - Refresh: 1s
   - Driver filter: All

### Option 2: Auto-Provisioning (Advanced)

Edit Grafana config to use auto-provisioning:

**macOS (Homebrew)**: `/opt/homebrew/etc/grafana/grafana.ini`

```ini
[paths]
provisioning = /Users/YOUR_USERNAME/Documents/DE Project/f1_streaming_pipeline/grafana/provisioning
```

Replace `YOUR_USERNAME` with your actual username, then restart Grafana.

## 🎉 Verify Everything Works

1. **Check Bridge Status**:
   ```bash
   curl http://localhost:5001/stats
   ```
   Should show:
   ```json
   {
     "running": true,
     "messages_received": 1234,
     "drivers_count": 3
   }
   ```

2. **View Dashboard**:
   - Open http://localhost:3000
   - Navigate to your dashboard
   - You should see real-time telemetry updating every second

3. **Check Data Flow**:
   - Speed, RPM, Throttle, Gear panels should show live data
   - Driver statistics table should list active drivers
   - Wheel spin analysis should show calculations
   - Alerts panel may show detected anomalies

## 🐛 Troubleshooting

### "Data source is not working"
```bash
# Check bridge is running
curl http://localhost:5001/

# Restart bridge
# Press Ctrl+C in bridge terminal, then:
./scripts/start_grafana_bridge.sh
```

### "No data points"
```bash
# Check producer is running and sending data
curl http://localhost:5001/drivers

# Should show list of active drivers, e.g.:
# [{"driver_id": "VER", "speed": 234.5, ...}]
```

### "Kafka connection error"
```bash
# Check Kafka is running
nc -z localhost 9092 && echo "OK" || echo "Not running"

# Restart Kafka
./scripts/stop_kafka.sh
./scripts/start_kafka.sh
```

### Bridge crashes
```bash
# Check logs
tail -f logs/grafana_bridge.log

# Verify config
cat config/grafana_bridge_config.yaml

# Check Python dependencies
pip install flask flask-cors
```

## 📖 Complete Documentation

For detailed information, see:

- **[docs/GRAFANA_SETUP.md](docs/GRAFANA_SETUP.md)** - Complete setup guide with all options
- **[docs/GRAFANA_DASHBOARD_GUIDE.md](docs/GRAFANA_DASHBOARD_GUIDE.md)** - How to use the dashboard
- **[GRAFANA_INSTALL_INSTRUCTIONS.txt](GRAFANA_INSTALL_INSTRUCTIONS.txt)** - Grafana installation help

## 🎨 Dashboard Features

Your dashboard includes:

### Row 1: System Status
- Messages received, throughput, active drivers, uptime

### Row 2: Real-Time Telemetry
- Speed (km/h) - Multi-driver time series
- RPM - Engine revolutions
- Throttle (%) - With area fill
- Gear - Step line chart

### Row 3: Wheel Spin Analysis
- Wheel spin percentage with 15% threshold line
- Actual vs expected speed comparison
- Automatic wheel spin detection

### Row 4: Gear Anomalies
- Gear anomaly events (scatter plot)
- Driver statistics table
- Lugging, over-revving, rapid shifting detection

### Row 5: Alerts & Monitoring
- Alert distribution pie chart
- Recent alerts table with severity colors
- Alert annotations on time series

## 🔄 Typical Workflow

1. **Start services** (Kafka → Bridge → Producer)
2. **Open Grafana** (http://localhost:3000)
3. **Monitor dashboard** with 1s refresh
4. **Analyze data** as it streams
5. **Customize panels** as needed
6. **Export snapshots** for sharing
7. **Stop gracefully** (Ctrl+C in each terminal)

## 💡 Tips

- Use **Last 5 minutes** time range for real-time monitoring
- Set **refresh to 1s** for smooth updates
- Filter by specific drivers using the dropdown
- Zoom into panels by clicking and dragging
- Use fullscreen mode (hover → View)
- Check bridge stats regularly: `curl http://localhost:5001/stats`

## 🚀 Next Steps

1. ✅ Explore different race sessions
2. ✅ Customize panel queries and visualizations
3. ✅ Set up Grafana alerting for critical events
4. ✅ Export and share dashboards with team
5. ✅ Monitor long races with historical data
6. ✅ Compare multiple drivers' strategies

## 📞 Need Help?

- Check troubleshooting section above
- Review complete setup guide: `docs/GRAFANA_SETUP.md`
- Test bridge endpoints: `./scripts/test_grafana_bridge.sh`
- Check logs: `tail -f logs/grafana_bridge.log`

---

**Happy Monitoring! 🏎️💨**

All the hard work is done - just install Grafana and you're ready to go!

