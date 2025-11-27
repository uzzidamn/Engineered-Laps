# F1 Real-Time Kafka CLI Dashboard Guide

## Overview

The F1 CLI Dashboard is a beautiful terminal-based monitoring tool for your Kafka streaming pipeline. Built with the Rich Python library, it provides real-time visualization of F1 telemetry data, wheel spin analysis, gear anomalies, and alerts - all without needing a browser.

## Features

✅ **Real-Time Monitoring** - Live updates at 10 Hz refresh rate
✅ **Beautiful Terminal UI** - Colored panels, progress bars, and sparklines
✅ **Kafka Integration** - Direct integration with your Kafka infrastructure
✅ **Multi-Consumer Support** - Monitors multiple consumer groups simultaneously
✅ **Event Logging** - Real-time event stream at the bottom
✅ **No Browser Required** - Perfect for SSH sessions and remote monitoring
✅ **Lightweight** - Minimal resource usage

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kafka Infrastructure                          │
│  Broker, Producer, Consumer Groups Status & Metrics             │
└─────────────────────────────────────────────────────────────────┘
┌──────────────────┬──────────────────┬──────────────────────────┐
│  Wheel Spin      │  Gear Anomalies  │  Alerts & Warnings       │
│  Analysis        │  Detection       │  (High/Medium/Low)       │
│                  │                  │                          │
│  - Events/Driver │  - Lugging       │  - High Speed            │
│  - Recent Spins  │  - Over-revving  │  - DRS Status            │
│  - Statistics    │  - Distribution  │  - Brake Temperature     │
└──────────────────┴──────────────────┴──────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                    Live Event Log                                │
│  Real-time stream of alerts, data events, and system messages   │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Kafka Running**
   ```bash
   # Start Kafka (if not already running)
   ./scripts/start_kafka.sh
   ```

2. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   # Includes: rich>=13.0.0, kafka-python, etc.
   ```

3. **Terminal Requirements**
   - Terminal with Unicode support
   - Minimum 80x24 characters (larger recommended)
   - Color support (most modern terminals)

## Installation

1. **Install Dependencies**
   ```bash
   cd /path/to/f1_streaming_pipeline
   pip install -r requirements.txt
   ```

2. **Verify Kafka Connection**
   ```bash
   python scripts/f1_cli_dashboard.py --setup
   ```
   
   This will:
   - Check Kafka broker connection
   - Create/verify all required topics
   - Display setup status

## Usage

### Basic Usage

Run the dashboard with default settings (VER, HAM, LEC drivers):

```bash
python scripts/f1_cli_dashboard.py
```

### Custom Drivers

Monitor specific drivers:

```bash
python scripts/f1_cli_dashboard.py --drivers VER HAM LEC SAI PER
```

### Data Source Selection

Choose between cached data or live FastF1 data:

```bash
# Use cached data (faster, recommended for demos)
python scripts/f1_cli_dashboard.py --data-source cache

# Use live FastF1 data (requires internet)
python scripts/f1_cli_dashboard.py --data-source fastf1
```

### Custom Frequency

Adjust streaming frequency (Hz):

```bash
# Stream at 20 Hz
python scripts/f1_cli_dashboard.py --frequency 20

# Stream at 5 Hz (lower resource usage)
python scripts/f1_cli_dashboard.py --frequency 5
```

### Complete Example

```bash
python scripts/f1_cli_dashboard.py \
    --drivers VER HAM LEC \
    --data-source cache \
    --frequency 10
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--drivers` | List of driver IDs to monitor | VER HAM LEC |
| `--data-source` | Data source: `cache` or `fastf1` | cache |
| `--frequency` | Streaming frequency in Hz | 10 |
| `--setup` | Only create topics and exit | - |
| `--help` | Show help message | - |

## Dashboard Panels

### 1. Kafka Infrastructure Panel (Top)

Shows:
- **Broker Status**: Connection status to Kafka broker
- **Producer Status**: Streaming state, message rate, total messages, uptime
- **Drivers**: Currently monitored drivers
- **Consumer Groups**: Status, message rate, and lag for each consumer

Example:
```
┌─ Kafka Infrastructure ─────────────────────────────────────┐
│ Broker: ● ONLINE (localhost:9092)                          │
│ Producer: ▶ STREAMING | 1,234 msg/s | Total: 45,678 msgs  │
│ Drivers: VER, HAM, LEC                                     │
│                                                             │
│ Consumer Groups:                                            │
│   ● wheel_spin: 450 msg/s | Lag: 12                       │
│   ● gear_anomalies: 450 msg/s | Lag: 8                    │
│   ● alerts: 23 msg/s | Lag: 0                             │
└─────────────────────────────────────────────────────────────┘
```

### 2. Wheel Spin Analysis Panel

Shows:
- **Total Events**: Number of wheel spin events detected
- **Per-Driver Breakdown**: Bar chart showing events per driver
- **Recent Spins**: Last 5 wheel spin events with details

Example:
```
┌─ Wheel Spin Analysis ─────┐
│ Total Events: 47           │
│ VER: 15 ████████░░         │
│ HAM: 22 ████████████░░     │
│ LEC: 10 ████░░░░░░         │
│                            │
│ Recent Spins:              │
│ 10:23:15 VER 305km/h G7   │
│ 10:23:12 HAM 298km/h G6   │
│ 10:23:08 LEC 310km/h G7   │
└────────────────────────────┘
```

### 3. Gear Anomalies Panel

Shows:
- **Lugging Count**: Low RPM for current gear
- **Over-Rev Count**: Excessive RPM for current gear
- **Anomaly Rate**: Percentage of samples with anomalies
- **Gear Distribution**: Bar chart showing anomalies by gear

Example:
```
┌─ Gear Anomalies ──────────┐
│ Lugging: 12               │
│ Over-Rev: 8               │
│ Rate: 3.2%                │
│                            │
│ Distribution:              │
│ Gear 1: ██░░░░░░░░ 20%   │
│ Gear 2: ████░░░░░░ 40%   │
│ Gear 3: ███░░░░░░░ 30%   │
│ Gear 4: █░░░░░░░░░ 10%   │
└────────────────────────────┘
```

### 4. Alerts & Warnings Panel

Shows:
- **Severity Counts**: High (red), Medium (yellow), Low (white)
- **Recent Alerts**: Last 5 alerts with details

Example:
```
┌─ Alerts & Warnings ───────┐
│ 🔴 High: 5                │
│ 🟡 Medium: 12             │
│ ⚪ Low: 3                 │
│                            │
│ Recent Alerts:             │
│ 🔴 VER High Speed 325km/h │
│ 🟡 HAM DRS ON             │
│ 🔴 LEC Brake Temp 850°C   │
└────────────────────────────┘
```

### 5. Live Event Log Panel (Bottom)

Shows:
- Real-time stream of events
- Color-coded by severity (ALERT, WARNING, INFO, DATA)
- Last 8 events displayed

Example:
```
┌─ Live Events ──────────────────────────────────────────────┐
│ 10:23:45 [INFO] Consumer lag: 5ms                         │
│ 10:23:44 [ALERT] VER high speed detected: 325 km/h        │
│ 10:23:43 [DATA] Wheel spin detected: HAM                  │
│ 10:23:42 [INFO] Producer rate: 1,234 msg/s                │
└─────────────────────────────────────────────────────────────┘
```

## Keyboard Controls

| Key | Action |
|-----|--------|
| `Ctrl+C` | Quit dashboard and stop all streaming |

> **Note**: Additional interactive controls (pause, reset) are implemented in the code structure but require a key listener library for full functionality in terminal mode.

## Workflow

### Standard Workflow

1. **Start Kafka** (if not running)
   ```bash
   ./scripts/start_kafka.sh
   ```

2. **Setup Topics** (first time only)
   ```bash
   python scripts/f1_cli_dashboard.py --setup
   ```

3. **Run Dashboard**
   ```bash
   python scripts/f1_cli_dashboard.py --drivers VER HAM LEC
   ```

4. **Monitor Real-Time Data**
   - Observe producer and consumer metrics
   - Watch for wheel spin events
   - Monitor gear anomalies
   - Track alerts by severity

5. **Stop Dashboard**
   - Press `Ctrl+C` to gracefully shutdown

### Demo Workflow

Perfect for presentations:

```bash
# Terminal 1: Start dashboard with specific drivers
python scripts/f1_cli_dashboard.py \
    --drivers VER HAM \
    --data-source cache \
    --frequency 10

# Dashboard will show beautiful real-time updates
# Perfect for demonstrating the streaming pipeline!
```

## Data Flow

```
┌─────────────┐
│   FastF1    │
│ Telemetry   │
│   Data      │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────┐
│   Kafka     │─────▶│   f1-        │
│  Producer   │      │  telemetry   │
└─────────────┘      │   topic      │
                     └───────┬──────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  Wheel Spin │  │    Gear     │  │   Alerts    │
    │  Consumer   │  │  Anomalies  │  │  Consumer   │
    │             │  │  Consumer   │  │             │
    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
           │                │                │
           └────────────────┼────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  CLI Dashboard  │
                   │   Renderer      │
                   └─────────────────┘
                            │
                            ▼
                   Terminal Display
```

## Performance Considerations

### Refresh Rate

- **Default**: 10 Hz (100ms intervals)
- **Higher rates** (20 Hz): More responsive but higher CPU usage
- **Lower rates** (5 Hz): Lower CPU usage, slightly less smooth

### Resource Usage

Typical resource usage (3 drivers, 10 Hz):
- **CPU**: 5-10% (single core)
- **Memory**: ~50-100 MB
- **Network**: Minimal (local Kafka)

### Optimization Tips

1. **Reduce Drivers**: Monitor fewer drivers to reduce data volume
2. **Lower Frequency**: Use `--frequency 5` for less resource usage
3. **Use Cache**: `--data-source cache` is faster than FastF1
4. **Terminal Size**: Smaller terminals render faster

## Troubleshooting

### Cannot Connect to Kafka

```
❌ Cannot connect to Kafka broker at localhost:9092
```

**Solution**: Start Kafka first
```bash
./scripts/start_kafka.sh
```

### Import Errors

```
ModuleNotFoundError: No module named 'rich'
```

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Terminal Display Issues

If the dashboard doesn't render correctly:

1. **Check terminal size**: Minimum 80x24 characters
   ```bash
   echo $COLUMNS x $LINES
   ```

2. **Check Unicode support**: Terminal must support Unicode
   ```bash
   locale  # Should show UTF-8
   ```

3. **Check colors**: Terminal must support ANSI colors
   ```bash
   tput colors  # Should return 256
   ```

### No Data Showing

If panels show "No events detected":

1. **Check producer**: Ensure producer is sending data
2. **Check topics**: Verify topics exist
   ```bash
   python scripts/f1_cli_dashboard.py --setup
   ```
3. **Check consumer groups**: Verify consumers are receiving messages

### High CPU Usage

If CPU usage is too high:

1. Reduce frequency: `--frequency 5`
2. Monitor fewer drivers: `--drivers VER`
3. Check for errors in event log

## Advanced Usage

### Running Over SSH

The CLI dashboard works perfectly over SSH:

```bash
ssh user@remote-server
cd /path/to/f1_streaming_pipeline
python scripts/f1_cli_dashboard.py
```

### Screen/Tmux Sessions

Run in detached session:

```bash
# Using screen
screen -S f1-dashboard
python scripts/f1_cli_dashboard.py
# Ctrl+A, D to detach

# Using tmux
tmux new -s f1-dashboard
python scripts/f1_cli_dashboard.py
# Ctrl+B, D to detach
```

### Multiple Dashboards

Run multiple dashboards for different driver sets:

```bash
# Terminal 1: Top drivers
python scripts/f1_cli_dashboard.py --drivers VER HAM

# Terminal 2: Other drivers
python scripts/f1_cli_dashboard.py --drivers LEC SAI PER
```

## Comparison with Other Dashboards

| Feature | CLI Dashboard | Streamlit | Dash | Jupyter |
|---------|--------------|-----------|------|---------|
| Browser Required | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| SSH Friendly | ✅ Yes | ⚠️ Tunneling | ⚠️ Tunneling | ⚠️ Tunneling |
| Resource Usage | Low | Medium | Medium | High |
| Real-Time Updates | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Manual |
| Setup Complexity | Simple | Medium | Medium | Simple |
| Interactivity | Limited | High | High | Medium |
| Demo Ready | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Limited |

## Architecture Integration

The CLI dashboard integrates with the existing Kafka architecture:

```yaml
Consumer Groups Used:
  - streamlit-wheel-spin-group: Wheel spin analysis
  - streamlit-gear-anomalies-group: Gear anomaly detection
  - alert-processor-group: Alert monitoring

Topics Consumed:
  - f1-telemetry: Main telemetry stream
  - f1-alerts: Alert notifications

Partitioning:
  - Telemetry: Hash-based by driver_id (4 partitions)
  - Alerts: Severity-based (3 partitions: high/medium/low)
```

## Future Enhancements

Planned improvements:

- [ ] Interactive keyboard controls (pause, reset, filter)
- [ ] Sparkline graphs for time-series trends
- [ ] Export snapshot to HTML/JSON
- [ ] Record session to video (asciinema)
- [ ] Multiple layout modes (compact, detailed)
- [ ] Filter by specific driver
- [ ] Historical playback mode
- [ ] Custom alert thresholds

## Support

For issues or questions:

1. Check this guide
2. Review `docs/KAFKA_ARCHITECTURE.md`
3. Check event log in dashboard for errors
4. Verify Kafka broker is running

## Examples

### Example 1: Quick Demo

```bash
# 1. Setup (first time)
python scripts/f1_cli_dashboard.py --setup

# 2. Run dashboard
python scripts/f1_cli_dashboard.py

# 3. Watch the magic! 🚀
```

### Example 2: Production Monitoring

```bash
# Run with all drivers at high frequency
python scripts/f1_cli_dashboard.py \
    --drivers VER HAM LEC SAI PER NOR \
    --data-source cache \
    --frequency 20
```

### Example 3: Low-Resource Mode

```bash
# Minimal resource usage
python scripts/f1_cli_dashboard.py \
    --drivers VER \
    --frequency 5
```

## Conclusion

The F1 CLI Dashboard provides a lightweight, beautiful way to monitor your Kafka streaming pipeline directly in the terminal. Perfect for:

- **Demos and Presentations**: No browser setup required
- **Remote Monitoring**: Works perfectly over SSH
- **Development**: Quick feedback during development
- **Production**: Lightweight monitoring without web overhead

Enjoy your real-time F1 streaming dashboard! 🏎️💨

