# Grafana Dashboard User Guide

Complete guide to using the F1 Real-Time Telemetry Dashboard in Grafana.

## Table of Contents

1. [Dashboard Overview](#dashboard-overview)
2. [Dashboard Layout](#dashboard-layout)
3. [Panel Descriptions](#panel-descriptions)
4. [Using Dashboard Features](#using-dashboard-features)
5. [Real-Time Monitoring](#real-time-monitoring)
6. [Analyzing Data](#analyzing-data)
7. [Customization](#customization)
8. [Best Practices](#best-practices)

---

## Dashboard Overview

The F1 Real-Time Telemetry Dashboard provides comprehensive real-time monitoring of F1 race telemetry data streamed through Kafka. It combines multiple visualizations to give you complete insight into:

- **Vehicle Performance**: Speed, RPM, throttle, gear selection
- **Anomaly Detection**: Wheel spin events, gear selection issues
- **Multi-Driver Comparison**: Compare multiple drivers simultaneously
- **Alert Monitoring**: Track and analyze system alerts

### Key Features

✅ **Real-Time Updates**: 1-second refresh rate for live monitoring  
✅ **Multi-Driver Support**: Monitor multiple drivers simultaneously  
✅ **Historical Analysis**: Query past telemetry data  
✅ **Anomaly Detection**: Automatic wheel spin and gear anomaly detection  
✅ **Interactive**: Zoom, pan, and explore data interactively  
✅ **Alert Annotations**: Visual markers for important events  

---

## Dashboard Layout

The dashboard is organized into 6 rows:

```
┌─────────────────────────────────────────────────────────┐
│  Row 1: Header & System Status                          │
│  [Messages] [Throughput] [Active Drivers] [Uptime]      │
├─────────────────────────────────────────────────────────┤
│  Row 2: Real-Time Telemetry (4 panels)                  │
│  [Speed] [RPM] [Throttle] [Gear]                        │
├─────────────────────────────────────────────────────────┤
│  Row 3: Wheel Spin Analysis                             │
│  [Wheel Spin %]  [Actual vs Expected Speed]             │
├─────────────────────────────────────────────────────────┤
│  Row 4: Gear Anomalies                                  │
│  [Anomaly Events]  [Driver Statistics Table]            │
├─────────────────────────────────────────────────────────┤
│  Row 5: Alerts & Monitoring                             │
│  [Alert Distribution]  [Recent Alerts Table]            │
└─────────────────────────────────────────────────────────┘
```

---

## Panel Descriptions

### Row 1: System Status

#### 📊 Messages Received
- **Type**: Stat panel
- **Shows**: Total Kafka messages consumed by bridge
- **Use**: Monitor data pipeline health

#### 📈 Throughput
- **Type**: Stat panel with trend
- **Shows**: Messages per second
- **Use**: Verify streaming performance
- **Expected**: 10-50 msg/s depending on speed factor

#### 👥 Active Drivers
- **Type**: Stat panel
- **Shows**: Number of drivers currently transmitting data
- **Use**: Verify which drivers are active

#### ⏱️ Uptime
- **Type**: Stat panel
- **Shows**: Bridge service uptime in seconds
- **Use**: Monitor service stability

---

### Row 2: Real-Time Telemetry

#### 🏎️ Speed (km/h)
- **Type**: Time series
- **Y-Axis**: Speed in km/h
- **Legend**: Shows last value and max for each driver
- **Colors**: Each driver has unique color
- **Interpolation**: Smooth lines for better readability

**How to read**:
- Sharp drops = Braking zones
- Plateaus = Straight sections
- Spikes = Acceleration zones

#### 🔧 RPM
- **Type**: Time series
- **Y-Axis**: Engine revolutions per minute
- **Legend**: Shows last and max RPM per driver
- **Typical range**: 8,000 - 15,000 RPM

**How to read**:
- High RPM (>13,000) = High gear, high speed
- Low RPM (<8,000) = Low gear or coasting
- Rapid drops = Gear shifts

#### ⚡ Throttle (%)
- **Type**: Time series with area fill
- **Y-Axis**: Throttle percentage (0-100%)
- **Fill**: Shows throttle application intensity
- **Legend**: Shows last and mean throttle per driver

**How to read**:
- 100% = Full throttle
- 0% = Coasting/braking
- Oscillations = Traction control activation or wheel spin

#### ⚙️ Gear
- **Type**: Step line chart
- **Y-Axis**: Gear number (1-8)
- **Interpolation**: Step-after (shows discrete gear changes)
- **Legend**: Shows current gear

**How to read**:
- Steps up/down = Gear shifts
- Long horizontal lines = Stable gear
- Rapid changes = Corner exit/entry

---

### Row 3: Wheel Spin Analysis

#### 🔄 Wheel Spin Percentage
- **Type**: Time series with threshold line
- **Y-Axis**: Wheel spin percentage
- **Threshold**: Red line at 15%
- **Calculation**: `(expected_speed - actual_speed) / actual_speed * 100`

**Interpretation**:
- **< 5%**: Normal traction
- **5-15%**: Minor wheel spin (acceptable)
- **> 15%**: Significant wheel spin (alert threshold)
- **> 30%**: Severe wheel spin (traction loss)

**Legend values**:
- **Last**: Current wheel spin %
- **Max**: Maximum recorded
- **Mean**: Average over time window

#### 🎯 Actual vs Expected Speed
- **Type**: Dual time series
- **Blue solid line**: Actual speed from telemetry
- **Red dashed line**: Expected speed based on RPM and gear
- **Gap between lines**: Indicates wheel spin

**How to use**:
1. When lines overlap = Good traction
2. Red above blue = Wheel spinning (wheels faster than vehicle)
3. Large gap = More severe wheel spin
4. Check correlation with throttle panel

---

### Row 4: Gear Anomalies

#### ⚠️ Gear Anomaly Events
- **Type**: Scatter plot
- **Points**: Each point = detected anomaly
- **Colors**: Different colors per driver
- **Size**: Large points (8px) for visibility

**Anomaly types detected**:
1. **Lugging**: Too high gear for speed (gear > optimal + 2)
2. **Over-Revving**: Too low gear for speed (gear < optimal - 2)
3. **Wrong gear range**: Speed outside optimal range for current gear

**Optimal gear ranges**:
```
Gear 1: 0-80 km/h
Gear 2: 60-120 km/h
Gear 3: 100-160 km/h
Gear 4: 140-200 km/h
Gear 5: 180-240 km/h
Gear 6: 220-280 km/h
Gear 7: 260-320 km/h
Gear 8: 300+ km/h
```

#### 📋 Driver Statistics Table
- **Type**: Table
- **Columns**: Driver, Speed, RPM, Throttle, Brake, Gear, DRS, etc.
- **Values**: Latest (last recorded) for each metric
- **Sorting**: Click column headers to sort

**Use cases**:
- Quick comparison of all drivers
- Identify slowest/fastest driver
- Check who's in highest gear
- Monitor current DRS status

---

### Row 5: Alerts & Monitoring

#### 🥧 Alert Distribution
- **Type**: Pie chart
- **Segments**:
  - 🔴 High severity (red)
  - 🟡 Medium severity (yellow)
  - ⚪ Low severity (gray)
- **Legend**: Shows count per severity

**Interpretation**:
- **High**: Critical alerts requiring immediate attention
- **Medium**: Warning alerts, monitor closely
- **Low**: Informational alerts

#### 📝 Recent Alerts Table
- **Type**: Table with colored rows
- **Columns**: Timestamp, Severity, Driver, Type, Description
- **Row colors**: Background color based on severity
- **Sorting**: Most recent first
- **Limit**: Shows last 20 alerts

**Common alert types**:
- `wheel_spin_detected`
- `gear_lugging`
- `over_revving`
- `rapid_shifting`
- `brake_temp_high` (if configured)

---

## Using Dashboard Features

### Time Range Selection

Located in top-right corner:

**Quick ranges**:
- Last 5 minutes (default)
- Last 15 minutes
- Last 30 minutes
- Last 1 hour

**Custom range**:
1. Click time range dropdown
2. Select "Custom range"
3. Choose start and end times
4. Apply

**Tips**:
- Use shorter ranges (5-15 min) for real-time monitoring
- Use longer ranges for post-race analysis
- Click "Zoom to data" to auto-fit time range

### Refresh Interval

**Options**:
- Off (manual only)
- 1s (recommended for live)
- 5s
- 10s
- 30s
- 1m

**How to set**:
1. Click refresh dropdown (top-right)
2. Select interval
3. Dashboard auto-refreshes

**Performance tip**: Use 5s or 10s if dashboard feels sluggish

### Driver Filtering

Use the **Driver** dropdown (top-left):

**Options**:
- All (default) - shows all drivers
- Individual drivers (VER, HAM, LEC, etc.)
- Multiple selection - hold Cmd/Ctrl to select multiple

**Effect**: Filters all panels to show only selected drivers

### Zooming and Panning

**Zoom in**:
- Click and drag horizontally on any time series chart
- Scroll wheel on chart (if enabled)

**Zoom out**:
- Double-click on chart
- Click "Reset zoom" icon (top-right of panel)

**Pan (move time window)**:
- Hold Shift + click and drag

### Panel Actions

Hover over any panel title for menu (three dots):

**Options**:
- **View**: Fullscreen mode
- **Edit**: Modify panel settings
- **Share**: Share snapshot or embed
- **Explore**: Deep dive into data
- **Inspect**: View raw JSON/data
- **More...**: Additional options

---

## Real-Time Monitoring

### Typical Monitoring Workflow

1. **Start streaming**:
   ```bash
   # Terminal 1: Start Kafka
   ./scripts/start_kafka.sh
   
   # Terminal 2: Start bridge
   ./scripts/start_grafana_bridge.sh
   
   # Terminal 3: Start producer
   python scripts/run_producer.py
   ```

2. **Open dashboard**:
   - Navigate to http://localhost:3000
   - Open "F1 Real-Time Telemetry Dashboard"

3. **Configure view**:
   - Set time range: "Last 5 minutes"
   - Set refresh: "1s"
   - Select drivers: "All" or specific

4. **Monitor**:
   - Watch speed/RPM patterns
   - Check for wheel spin events (>15%)
   - Monitor gear anomalies
   - Review alerts as they appear

### What to Look For

#### 🏁 Race Start
- All drivers accelerate together
- High wheel spin (20-40%) normal at start
- Rapid gear changes (1→8 quickly)
- High RPM sustained

#### 🏎️ Qualifying Lap
- Maximum speed on straights
- Aggressive braking (throttle 0%, high brake)
- Optimal gear selection
- Minimal wheel spin (<10%)

#### 🛑 Pit Stop
- Speed drops to ~80 km/h in pit lane
- Gear stays in 1st or 2nd
- Brief data gap during stop

#### ⚠️ Anomalies
- Sudden wheel spin spike → Potential traction loss
- Gear anomaly cluster → Driver struggling
- RPM drops to 0 → Potential engine issue

---

## Analyzing Data

### Comparing Drivers

1. **Select multiple drivers** from dropdown
2. **Observe**:
   - Who reaches higher top speed (speed panel)
   - Who maintains higher RPM (better acceleration)
   - Throttle application differences
   - Gear shift timing differences

3. **Look for patterns**:
   - Consistent leader → Faster car or better driver
   - Similar speeds, different RPM → Different setups
   - More wheel spin → Less traction (tire wear, setup, or track)

### Identifying Issues

#### High Wheel Spin
1. Check wheel spin % panel
2. If consistently >15%:
   - ⚠️ Tire degradation
   - ⚠️ Poor traction control
   - ⚠️ Aggressive throttle application
3. Cross-reference with throttle panel
4. Check alerts table for frequency

#### Gear Selection Problems
1. Check gear anomaly events panel
2. Cluster of anomalies suggests:
   - 🔴 Driver error (wrong gear)
   - 🔴 Gearbox issue
   - 🔴 Strategy (short-shifting to save fuel)
3. Check driver statistics for current gear
4. Compare with optimal gear for current speed

#### Performance Degradation
1. Check speed trend over time
2. Declining max speed suggests:
   - 🔋 Engine mode change (power saving)
   - 🏴 Tire degradation
   - ⛽ Fuel weight reduction (speed increase)
3. Check RPM for engine health
4. Monitor throttle % for driver confidence

---

## Customization

### Modifying Panels

1. Enter edit mode (🔧 icon, top-right)
2. Click panel title → Edit
3. Modify:
   - **Query**: Change target metric
   - **Visualization**: Change chart type
   - **Field options**: Units, thresholds, colors
   - **Panel options**: Title, description
4. Apply changes
5. Save dashboard (💾 icon, top-right)

### Adding New Panels

1. Click "Add panel" (➕ icon, top-right)
2. Select visualization type
3. Configure data source: "F1 Kafka Bridge"
4. Enter query:
   - Target: `speed` (or other metric)
   - Or: `VER.speed` (specific driver)
5. Customize appearance
6. Save

### Available Metrics

Query any of these in panels:

**Basic telemetry**:
- `speed` - km/h
- `rpm` - Engine RPM
- `throttle` - Throttle %
- `brake` - Brake %
- `gear` - Gear number
- `drs` - DRS status

**Derived metrics**:
- `wheel_spin` - Boolean (0 or 1)
- `wheel_spin_pct` - Percentage
- `expected_speed` - Calculated expected speed
- `gear_anomaly` - Boolean (0 or 1)

**Driver-specific** (replace VER with driver code):
- `VER.speed`
- `VER.rpm`
- `VER.wheel_spin_pct`
- etc.

### Creating Alerts

1. Edit any panel
2. Go to **Alert** tab
3. Click "Create alert rule"
4. Configure:
   - **Condition**: e.g., `wheel_spin_pct > 30`
   - **Evaluation**: Every 10s
   - **For**: 1m
5. **Notification**: Select channel (email, Slack, etc.)
6. Save

---

## Best Practices

### Performance Optimization

1. **Limit time range**: Use 5-15 minutes for real-time
2. **Reduce refresh rate**: 5s instead of 1s if laggy
3. **Filter drivers**: Show only relevant drivers
4. **Disable unused panels**: Hide panels you're not monitoring

### Monitoring Tips

1. **Use multiple screens**: Dashboard on one, analysis on another
2. **Create playlists**: Rotate between multiple dashboards
3. **Snapshot important moments**: Share → Snapshot
4. **Export data**: Panel menu → Inspect → Data → Download CSV

### Troubleshooting Dashboard Issues

#### Panel shows "No data"
- ✅ Check time range includes recent data
- ✅ Verify bridge service is running: `curl http://localhost:5001/stats`
- ✅ Check producer is streaming: `curl http://localhost:5001/drivers`
- ✅ Refresh dashboard (Ctrl+R)

#### Slow performance
- Reduce time range to 1-5 minutes
- Increase refresh interval to 5s or 10s
- Close unused browser tabs
- Restart Grafana: `brew services restart grafana`

#### Metrics not updating
- Check refresh interval is enabled (not "Off")
- Verify bridge is receiving messages: `curl http://localhost:5001/stats`
- Check browser console for errors (F12)

#### Driver filter not working
- Ensure datasource query uses variable: `$driver.speed`
- Check variable syntax in panel query
- Refresh variables: Dashboard settings → Variables → Refresh

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `d` + `k` | Open search |
| `f` | Full screen mode |
| `Esc` | Exit full screen |
| `Ctrl + S` | Save dashboard |
| `t` + `z` | Zoom to data |
| `t` + `s` | Time range picker |
| `?` | Show all shortcuts |

---

## Advanced Features

### Annotations

Annotations are visual markers on charts showing important events (alerts).

**Enable/disable**:
1. Dashboard settings (⚙️)
2. Annotations
3. Toggle "F1 Alerts" on/off

**What they show**:
- Red markers = High severity alerts
- Yellow markers = Medium severity
- Gray markers = Low severity

**Hover** over markers to see details.

### Variables

Use dashboard variables for dynamic filtering:

**Current variables**:
- `$driver` - Selected driver(s)

**Add new variable**:
1. Dashboard settings → Variables
2. Add variable
3. Configure query against bridge API
4. Use in panel queries: `$variable_name.metric`

### Templating

Create dashboard templates to reuse with different data sources or configurations.

**Export dashboard**:
1. Dashboard settings → JSON Model
2. Copy JSON
3. Edit as needed
4. Import via UI

---

## Integration with F1 Pipeline

### Data Flow

```
Kafka Producer → f1-telemetry topic → Bridge Service → Grafana
                → f1-alerts topic   →
```

### Bridge Service Endpoints

The dashboard queries these endpoints:

- `/search` - List available metrics
- `/query` - Fetch time-series data
- `/annotations` - Fetch alert markers
- `/stats` - Service statistics
- `/drivers` - Active drivers list

### Customizing Bridge

Edit `config/grafana_bridge_config.yaml`:

```yaml
buffer:
  max_points_per_driver: 2000  # Increase buffer size

telemetry:
  derived_metrics:
    wheel_spin:
      threshold: 1.10  # Adjust threshold (10% instead of 15%)
```

Restart bridge after changes.

---

## Additional Resources

- [Grafana Setup Guide](./GRAFANA_SETUP.md)
- [Grafana Official Docs](https://grafana.com/docs/)
- [Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/best-practices/)
- [Main Project README](../README.md)

---

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting-dashboard-issues) section
2. Review logs: `tail -f logs/grafana_bridge.log`
3. Test bridge endpoints: `curl http://localhost:5001/stats`
4. Refer to project documentation

---

**Happy Monitoring! 🏎️💨**

