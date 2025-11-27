# Kafka Dashboard Guide

This guide explains the two ways to monitor Kafka streaming in the F1 Streaming Pipeline project.

## Option 1: Jupyter Notebook Dashboard (`notebooks/04_kafka_dashboard.ipynb`)

### Overview
An interactive Jupyter notebook for real-time Kafka telemetry monitoring with live visualizations.

### Features
- ✅ Real-time telemetry consumption from Kafka
- ✅ Live matplotlib/plotly visualizations that update automatically
- ✅ Consumer metrics and statistics
- ✅ Independent consumer group (`notebook_monitor`) - won't interfere with Streamlit
- ✅ Data export capabilities

### Usage

1. **Start Kafka and Producer** (from Streamlit or command line)

2. **Open the notebook:**
   ```bash
   jupyter notebook notebooks/04_kafka_dashboard.ipynb
   ```

3. **Run cells in order:**
   - Cell 1: Import dependencies
   - Cell 2: Load configuration
   - Cell 3: Start live monitoring (auto-updates every ~2.5 seconds)

4. **Stop monitoring:**
   - Click `Kernel > Interrupt` or press `I, I` (press I twice)

### Configuration
Edit the notebook cell to customize:
```python
DRIVER_IDS = ['VER', 'HAM']  # Monitor specific drivers
MAX_POINTS = 500              # Number of data points to keep
```

### Advantages
- ✅ Can run alongside Streamlit dashboard
- ✅ Better for data exploration and analysis
- ✅ Easy to customize visualizations
- ✅ Can export data for offline analysis

---

## Option 2: Streamlit Dashboard - Kafka Wheel Spin Monitor Tab

### Overview
A dedicated tab in the main Streamlit dashboard for real-time wheel spin anomaly detection using Kafka streaming.

### Features
- ✅ Real-time wheel spin percentage calculation
- ✅ Actual vs Expected speed comparison
- ✅ Wheel spin event detection and alerts
- ✅ Multiple driver support
- ✅ Dedicated consumer group (`streamlit_wheel_spin`)
- ✅ Interactive Plotly charts

### Usage

1. **Start the Streamlit dashboard:**
   ```bash
   streamlit run scripts/f1_anomaly_dashboard.py
   ```

2. **Navigate to the "🔥 Kafka Wheel Spin Monitor" tab**

3. **Configure streaming:**
   - Select data source (Cache File or FastF1)
   - Choose drivers to monitor
   - Adjust speed factor (1.0 = real-time)

4. **Start monitoring:**
   - Click "▶️ Start Wheel Spin Monitoring"
   - Watch real-time wheel spin analysis
   - View actual vs expected speed charts
   - Monitor spin event statistics

5. **Stop monitoring:**
   - Click "⏹️ Stop Monitoring"

### Visualizations

1. **Wheel Spin Percentage Chart**
   - Rolling 20-message window average
   - Per-driver traces
   - Alert threshold line at 15%

2. **Actual vs Expected Speed**
   - Blue line: Actual speed from telemetry
   - Red dashed line: Expected speed based on RPM/Gear
   - Gaps indicate wheel spin

3. **Speed Difference Distribution**
   - Histogram showing speed delta
   - Positive values = wheel spin
   - Negative values = traction

4. **Latest Spin Events Table**
   - Most recent 10 wheel spin detections
   - Driver, actual speed, expected speed

### How Wheel Spin Detection Works

```python
# Calculation
wheel_rpm = engine_rpm / gear_ratio
expected_speed = (wheel_rpm * 2π * wheel_radius) / 60 * 3.6
wheel_spin = expected_speed > (actual_speed * 1.15)  # 15% threshold
```

### Advantages
- ✅ Integrated with main dashboard
- ✅ Real-time anomaly detection
- ✅ Professional UI with Streamlit
- ✅ Multiple visualizations in one view
- ✅ Persistent monitoring (auto-reruns)

---

## Comparison: Notebook vs Streamlit Tab

| Feature | Jupyter Notebook | Streamlit Tab |
|---------|-----------------|---------------|
| **Setup Complexity** | Low | Medium |
| **Customization** | High (direct code access) | Medium (pre-built UI) |
| **Visualizations** | Matplotlib/Plotly | Plotly only |
| **Live Updates** | Every ~2.5s | Every ~0.1s |
| **Data Export** | Easy (built-in) | Manual |
| **Wheel Spin Analysis** | Requires custom code | Built-in |
| **Multi-driver** | Yes | Yes |
| **Consumer Group** | `notebook_monitor` | `streamlit_wheel_spin` |
| **Best For** | Exploration, analysis | Monitoring, operations |

---

## Consumer Groups

The project uses multiple consumer groups to allow parallel monitoring:

1. **`streamlit_anomalies`** - Main Streamlit "Kafka Live Streaming" tab (Tab 3)
2. **`streamlit_wheel_spin`** - Wheel Spin Monitor tab (Tab 4)
3. **`notebook_monitor`** - Jupyter notebook monitoring

Each consumer group receives **all** messages independently, allowing:
- ✅ Multiple dashboards running simultaneously
- ✅ No message loss or interference
- ✅ Independent offset tracking

---

## Architecture

```
┌─────────────────┐
│  Kafka Producer │
│  (Dashboard or  │
│   Notebook)     │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│  Kafka Topic        │
│  f1_telemetry_data  │
└─────┬───────┬───────┘
      │       │
      │       └──────────────┐
      │                      │
      ▼                      ▼
┌──────────────┐     ┌──────────────────┐
│  Streamlit   │     │  Jupyter Notebook│
│  Tab 3: Live │     │  04_kafka_       │
│  Streaming   │     │  dashboard.ipynb │
│              │     │                  │
│  Tab 4: WS   │     │  Consumer Group: │
│  Monitor     │     │  notebook_monitor│
│              │     └──────────────────┘
│  Consumer    │
│  Groups:     │
│  - anomalies │
│  - wheel_spin│
└──────────────┘
```

---

## Troubleshooting

### Notebook Not Receiving Messages
1. Check Kafka is running: `docker ps` or check broker at `localhost:9092`
2. Verify producer is streaming (from Streamlit or other source)
3. Ensure consumer group is unique (not conflicting)
4. Check topic name in config matches producer

### Streamlit Tab Not Updating
1. Ensure streaming is started (green "🟢 Monitoring Active")
2. Check browser console for errors (F12)
3. Verify sufficient telemetry fields (speed, rpm, gear) in messages
4. Try restarting monitoring

### No Wheel Spin Detected
1. Verify RPM and Gear data is present in telemetry
2. Check threshold (15% by default may be too high/low)
3. Ensure speed > 0 (wheel spin not calculated during stops)
4. Try different drivers (some may have better traction control)

---

## Tips

1. **Run Both Simultaneously**
   - Use notebook for detailed analysis
   - Use Streamlit for real-time monitoring
   - Different consumer groups = no interference

2. **Customize Thresholds**
   - Wheel spin threshold: 1.15 (15% over actual speed)
   - Adjust in code for different sensitivity

3. **Performance**
   - Notebook updates every ~2.5s (less CPU)
   - Streamlit updates every ~0.1s (smoother but more CPU)
   - Reduce MAX_POINTS if experiencing lag

4. **Data Export**
   - Notebook has built-in export cell
   - Streamlit: manually copy data from session state

---

## Next Steps

- [ ] Add ML-based wheel spin prediction in Tab 4
- [ ] Implement alert notifications (email/Slack)
- [ ] Add historical comparison (current race vs past races)
- [ ] Export wheel spin reports as PDF
- [ ] Add configurable alert thresholds in UI

---

## Related Documentation

- [Main README](../README.md)
- [Kafka Setup Guide](../notebooks/03_kafka_producer.ipynb)
- [Data Preparation](../notebooks/01_data_preparation.ipynb)
- [Configuration](../config/config.yaml)

