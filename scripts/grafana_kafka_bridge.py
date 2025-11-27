#!/usr/bin/env python3
"""
Grafana Kafka Bridge Service
Bridges Kafka F1 telemetry data to Grafana via JSON API datasource
Provides real-time streaming with SSE and historical queries
"""

import os
import sys
import yaml
import time
import logging
import threading
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import deque, defaultdict
from typing import Dict, List, Any, Optional
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.kafka_consumer import RealTimeConsumer

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for troubleshooting
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelemetryBuffer:
    """Manages rolling buffers for telemetry data"""
    
    def __init__(self, max_points: int = 1000):
        self.max_points = max_points
        self.buffers = defaultdict(lambda: {
            'timestamps': deque(maxlen=max_points),
            'speed': deque(maxlen=max_points),
            'rpm': deque(maxlen=max_points),
            'throttle': deque(maxlen=max_points),
            'brake': deque(maxlen=max_points),
            'gear': deque(maxlen=max_points),
            'drs': deque(maxlen=max_points),
            'wheel_spin': deque(maxlen=max_points),
            'wheel_spin_pct': deque(maxlen=max_points),
            'expected_speed': deque(maxlen=max_points),
            'gear_anomaly': deque(maxlen=max_points),
        })
        self.lock = threading.Lock()
    
    def add_datapoint(self, driver_id: str, data: Dict[str, Any]):
        """Add a telemetry datapoint for a driver"""
        with self.lock:
            buffer = self.buffers[driver_id]
            
            # Use CURRENT wall clock time for real-time visualization
            # This ensures data always appears in the dashboard's time window
            # regardless of when the original F1 session was recorded
            timestamp = datetime.utcnow()
            
            buffer['timestamps'].append(timestamp)
            buffer['speed'].append(float(data.get('speed', 0)))
            buffer['rpm'].append(float(data.get('rpm', 0)))
            buffer['throttle'].append(float(data.get('throttle', 0)))
            buffer['brake'].append(float(data.get('brake', 0)))
            buffer['gear'].append(int(data.get('gear', 0) or data.get('n_gear', 0)))
            buffer['drs'].append(int(data.get('drs', 0)))
            
            # Calculate wheel spin
            wheel_spin, expected_speed, spin_pct = self._calculate_wheel_spin(
                rpm=buffer['rpm'][-1],
                gear=buffer['gear'][-1],
                speed=buffer['speed'][-1]
            )
            buffer['wheel_spin'].append(1 if wheel_spin else 0)
            buffer['wheel_spin_pct'].append(spin_pct)
            buffer['expected_speed'].append(expected_speed)
            
            # Calculate gear anomaly
            anomaly = self._detect_gear_anomaly(
                speed=buffer['speed'][-1],
                gear=buffer['gear'][-1],
                rpm=buffer['rpm'][-1]
            )
            buffer['gear_anomaly'].append(1 if anomaly else 0)
    
    def _calculate_wheel_spin(self, rpm: float, gear: int, speed: float) -> tuple:
        """Calculate wheel spin detection"""
        gear_ratios = {1: 13.0, 2: 10.5, 3: 8.5, 4: 7.0, 5: 6.0, 6: 5.2, 7: 4.5, 8: 4.0}
        wheel_radius_m = 0.33
        threshold = 1.15
        
        if gear == 0 or rpm == 0:
            return False, 0.0, 0.0
        
        gear_ratio = gear_ratios.get(gear, 5.0)
        wheel_rpm = rpm / gear_ratio
        expected_speed = (wheel_rpm * 2 * np.pi * wheel_radius_m) / 60 * 3.6
        
        wheel_spin = expected_speed > (speed * threshold)
        spin_pct = ((expected_speed - speed) / speed * 100) if speed > 0 else 0
        
        return wheel_spin, expected_speed, max(0, spin_pct)
    
    def _detect_gear_anomaly(self, speed: float, gear: int, rpm: float) -> bool:
        """Detect gear selection anomalies"""
        optimal_gear_ranges = {
            1: (0, 80), 2: (60, 120), 3: (100, 160), 4: (140, 200),
            5: (180, 240), 6: (220, 280), 7: (260, 320), 8: (300, 400)
        }
        
        if gear == 0 or speed == 0:
            return False
        
        # Check if gear is within optimal range for speed
        gear_range = optimal_gear_ranges.get(gear)
        if gear_range:
            min_speed, max_speed = gear_range
            if speed < min_speed * 0.8 or speed > max_speed * 1.2:
                return True
        
        # Check for lugging (high gear, low RPM)
        if gear > 3 and rpm < 8000 and speed > 50:
            return True
        
        # Check for over-revving (low gear, high RPM)
        if gear < 5 and rpm > 13000:
            return True
        
        return False
    
    def get_driver_data(self, driver_id: str, metric: str, 
                       from_time: Optional[datetime] = None,
                       to_time: Optional[datetime] = None) -> List[tuple]:
        """Get time-series data for a specific driver and metric"""
        with self.lock:
            if driver_id not in self.buffers:
                return []
            
            buffer = self.buffers[driver_id]
            
            if metric not in buffer:
                return []
            
            timestamps = list(buffer['timestamps'])
            values = list(buffer[metric])
            
            if not timestamps:
                return []
            
            # Filter by time range
            if from_time or to_time:
                filtered = []
                logger.debug(f"Filtering {driver_id}.{metric}: from={from_time}, to={to_time}, buffer_size={len(timestamps)}")
                if timestamps:
                    logger.debug(f"First timestamp in buffer: {timestamps[0]}, Last: {timestamps[-1]}")
                for ts, val in zip(timestamps, values):
                    if from_time and ts < from_time:
                        continue
                    if to_time and ts > to_time:
                        continue
                    filtered.append((ts, val))
                logger.debug(f"Filtered result: {len(filtered)} datapoints")
                return filtered
            
            return list(zip(timestamps, values))
    
    def get_all_drivers(self) -> List[str]:
        """Get list of all drivers with data"""
        with self.lock:
            return list(self.buffers.keys())
    
    def get_latest_values(self, driver_id: str) -> Dict[str, Any]:
        """Get latest values for all metrics for a driver"""
        with self.lock:
            if driver_id not in self.buffers:
                return {}
            
            buffer = self.buffers[driver_id]
            if not buffer['timestamps']:
                return {}
            
            return {
                'timestamp': buffer['timestamps'][-1],
                'speed': buffer['speed'][-1],
                'rpm': buffer['rpm'][-1],
                'throttle': buffer['throttle'][-1],
                'brake': buffer['brake'][-1],
                'gear': buffer['gear'][-1],
                'drs': buffer['drs'][-1],
                'wheel_spin': buffer['wheel_spin'][-1],
                'wheel_spin_pct': buffer['wheel_spin_pct'][-1],
                'expected_speed': buffer['expected_speed'][-1],
                'gear_anomaly': buffer['gear_anomaly'][-1],
            }


class AlertsBuffer:
    """Manages alerts buffer"""
    
    def __init__(self, max_alerts: int = 500):
        self.max_alerts = max_alerts
        self.alerts = deque(maxlen=max_alerts)
        self.lock = threading.Lock()
    
    def add_alert(self, alert: Dict[str, Any]):
        """Add an alert"""
        with self.lock:
            timestamp = alert.get('timestamp')
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now()
            
            alert_data = {
                'timestamp': timestamp,
                'severity': alert.get('severity', 'low'),
                'driver_id': alert.get('driver_id', 'UNKNOWN'),
                'alert_type': alert.get('alert_type', 'unknown'),
                'description': alert.get('description', ''),
                'value': alert.get('value', 0),
            }
            self.alerts.append(alert_data)
    
    def get_alerts(self, from_time: Optional[datetime] = None,
                   to_time: Optional[datetime] = None,
                   severity: Optional[str] = None) -> List[Dict]:
        """Get filtered alerts"""
        with self.lock:
            filtered = []
            for alert in self.alerts:
                if from_time and alert['timestamp'] < from_time:
                    continue
                if to_time and alert['timestamp'] > to_time:
                    continue
                if severity and alert['severity'] != severity:
                    continue
                filtered.append(alert.copy())
            return filtered
    
    def get_alert_count_by_severity(self) -> Dict[str, int]:
        """Get alert counts by severity"""
        with self.lock:
            counts = {'high': 0, 'medium': 0, 'low': 0}
            for alert in self.alerts:
                severity = alert['severity']
                if severity in counts:
                    counts[severity] += 1
            return counts


class GrafanaKafkaBridge:
    """Main bridge service"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        
        # Initialize buffers
        max_points = self.config['buffer']['max_points_per_driver']
        max_alerts = self.config['buffer']['max_alerts']
        
        self.telemetry_buffer = TelemetryBuffer(max_points=max_points)
        self.alerts_buffer = AlertsBuffer(max_alerts=max_alerts)
        
        # Initialize Kafka consumers
        self.telemetry_consumer = None
        self.alerts_consumer = None
        
        # Control flags
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.stats = {
            'messages_received': 0,
            'alerts_received': 0,
            'start_time': None,
        }
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def start(self):
        """Start Kafka consumers in background threads"""
        if self.running:
            return
        
        self.running = True
        self.shutdown_event.clear()
        self.stats['start_time'] = datetime.now()
        
        # Initialize consumers
        logger.info("Initializing Kafka consumers...")
        
        kafka_config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config', 'config.yaml'
        )
        
        self.telemetry_consumer = RealTimeConsumer(
            config_path=kafka_config_path,
            consumer_group=self.config['kafka']['consumer_group'],
            topics=[self.config['kafka']['topics']['telemetry']]
        )
        
        self.alerts_consumer = RealTimeConsumer(
            config_path=kafka_config_path,
            consumer_group=f"{self.config['kafka']['consumer_group']}_alerts",
            topics=[self.config['kafka']['topics']['alerts']]
        )
        
        # Start consumer threads
        telemetry_thread = threading.Thread(
            target=self._telemetry_consumer_loop,
            daemon=True
        )
        telemetry_thread.start()
        
        alerts_thread = threading.Thread(
            target=self._alerts_consumer_loop,
            daemon=True
        )
        alerts_thread.start()
        
        logger.info("✅ Bridge service started successfully")
    
    def stop(self):
        """Stop the bridge service"""
        if not self.running:
            return
        
        self.running = False
        self.shutdown_event.set()
        
        if self.telemetry_consumer:
            self.telemetry_consumer.close()
        if self.alerts_consumer:
            self.alerts_consumer.close()
        
        logger.info("Bridge service stopped")
    
    def _telemetry_consumer_loop(self):
        """Consumer loop for telemetry data"""
        try:
            while self.running and not self.shutdown_event.is_set():
                messages = self.telemetry_consumer.poll_messages(
                    timeout_ms=self.config['kafka']['poll_timeout_ms'],
                    max_messages=self.config['kafka']['max_messages']
                )
                
                for msg_wrapper in messages:
                    msg = msg_wrapper.get('message', {})
                    driver_id = msg.get('driver_id') or msg.get('driver', 'UNKNOWN')
                    
                    if driver_id != 'UNKNOWN':
                        self.telemetry_buffer.add_datapoint(driver_id, msg)
                        self.stats['messages_received'] += 1
                
                time.sleep(0.01)
        
        except Exception as e:
            logger.error(f"Telemetry consumer error: {e}")
    
    def _alerts_consumer_loop(self):
        """Consumer loop for alerts"""
        try:
            while self.running and not self.shutdown_event.is_set():
                messages = self.alerts_consumer.poll_messages(
                    timeout_ms=self.config['kafka']['poll_timeout_ms'],
                    max_messages=self.config['kafka']['max_messages']
                )
                
                for msg_wrapper in messages:
                    msg = msg_wrapper.get('message', {})
                    self.alerts_buffer.add_alert(msg)
                    self.stats['alerts_received'] += 1
                
                time.sleep(0.01)
        
        except Exception as e:
            logger.error(f"Alerts consumer error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            'running': self.running,
            'messages_received': self.stats['messages_received'],
            'alerts_received': self.stats['alerts_received'],
            'uptime_seconds': uptime,
            'drivers_count': len(self.telemetry_buffer.get_all_drivers()),
        }


# Global bridge instance
bridge = None


# ==================== GRAFANA API ENDPOINTS ====================

@app.route('/')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'F1 Grafana Kafka Bridge',
        'version': '1.0.0'
    })


@app.route('/search', methods=['POST', 'GET'])
def search():
    """
    Grafana datasource search endpoint
    Returns list of available metrics/targets
    """
    logger.info("Search request received")
    
    # Return available metrics
    metrics = [
        'speed',
        'rpm',
        'throttle',
        'brake',
        'gear',
        'drs',
        'wheel_spin',
        'wheel_spin_pct',
        'expected_speed',
        'gear_anomaly',
    ]
    
    # Add driver-specific metrics
    drivers = bridge.telemetry_buffer.get_all_drivers()
    
    targets = []
    for metric in metrics:
        targets.append(metric)
        for driver in drivers:
            targets.append(f"{driver}.{metric}")
    
    return jsonify(targets)


@app.route('/query', methods=['GET', 'POST'])
def query():
    """
    Grafana datasource query endpoint
    Returns time-series data
    """
    try:
        # Handle both GET and POST requests
        if request.method == 'GET':
            # Parse query parameters for GET request
            from_str = request.args.get('from')
            to_str = request.args.get('to')
            target_str = request.args.get('target', 'speed')  # Default to speed
            
            data = {
                'range': {
                    'from': from_str,
                    'to': to_str
                },
                'targets': [{'target': target_str}]
            }
            logger.info(f"Query request (GET): target={target_str}, from={from_str}, to={to_str}")
        else:
            # POST request - use JSON body
            data = request.get_json()
            logger.info(f"Query request (POST): {json.dumps(data, default=str)[:200]}")
        
        # Parse request
        range_data = data.get('range', {})
        from_str = range_data.get('from')
        to_str = range_data.get('to')
        
        # Parse timestamps (make timezone-naive for comparison)
        # For replayed data, use very wide time range if not specified
        from_time = None
        to_time = None
        if from_str:
            try:
                dt = datetime.fromisoformat(from_str.replace('Z', '+00:00'))
                from_time = dt.replace(tzinfo=None)  # Make naive
            except:
                from_time = datetime.now() - timedelta(hours=24)  # Last 24 hours default
        else:
            from_time = datetime.now() - timedelta(hours=24)  # Default: last 24 hours
            
        if to_str:
            try:
                dt = datetime.fromisoformat(to_str.replace('Z', '+00:00'))
                to_time = dt.replace(tzinfo=None)  # Make naive
            except:
                to_time = datetime.now() + timedelta(hours=1)  # Future buffer
        else:
            to_time = datetime.now() + timedelta(hours=1)  # Default: now + 1 hour
        
        # Process targets
        results = []
        targets = data.get('targets', [])
        logger.info(f"Processing {len(targets)} targets. From: {from_time}, To: {to_time}")
        
        for target in targets:
            target_str = target.get('target', '')
            logger.info(f"Processing target: '{target_str}'")
            
            if not target_str:
                continue
            
            # Parse target: format is "DRIVER.metric" or just "metric"
            if '.' in target_str:
                driver, metric = target_str.split('.', 1)
                logger.info(f"Specific driver query: {driver}.{metric}")
            else:
                # Return data for all drivers
                metric = target_str
                drivers = bridge.telemetry_buffer.get_all_drivers()
                logger.info(f"All drivers query for metric '{metric}': {drivers}")
                
                for driver in drivers:
                    datapoints = bridge.telemetry_buffer.get_driver_data(
                        driver, metric, from_time, to_time
                    )
                    
                    # If no datapoints with time filter, try without filter (get all buffered data)
                    if not datapoints:
                        logger.info(f"No data in time range for {driver}.{metric}, fetching all buffered data")
                        datapoints = bridge.telemetry_buffer.get_driver_data(
                            driver, metric, None, None
                        )
                    
                    if datapoints:
                        logger.debug(f"Adding {len(datapoints)} datapoints for {driver}.{metric}")
                        results.append({
                            'target': f"{driver}.{metric}",
                            'datapoints': [
                                [float(val), int(ts.timestamp() * 1000)]
                                for ts, val in datapoints
                            ]
                        })
                    else:
                        logger.debug(f"No datapoints for {driver}.{metric}")
                continue
            
            # Get data for specific driver
            datapoints = bridge.telemetry_buffer.get_driver_data(
                driver, metric, from_time, to_time
            )
            
            # If no datapoints with time filter, try without filter (get all buffered data)
            if not datapoints:
                logger.info(f"No data in time range for {driver}.{metric}, fetching all buffered data")
                datapoints = bridge.telemetry_buffer.get_driver_data(
                    driver, metric, None, None
                )
            
            if datapoints:
                results.append({
                    'target': target_str,
                    'datapoints': [
                        [float(val), int(ts.timestamp() * 1000)]
                        for ts, val in datapoints
                    ]
                })
        
        return jsonify(results)
    
    except Exception as e:
        logger.error(f"Query error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/query_flat', methods=['GET', 'POST'])
@app.route('/query_flat/<target_metric>', methods=['GET', 'POST'])
def query_flat(target_metric=None):
    """
    Marcus Olsson JSON datasource compatible endpoint
    Returns flat time-series data: [{time: ISO, metric_driver: value}, ...]
    
    Accepts target from:
    - URL path: /query_flat/speed
    - Query param: /query_flat?target=speed
    - POST body: {target: "speed"}
    """
    try:
        # Get parameters from multiple sources
        if request.method == 'POST':
            data = request.get_json() or {}
            target = data.get('target', '')
        else:
            target = request.args.get('target', '')
        
        # Use path parameter if query param is empty
        if not target and target_metric:
            target = target_metric
        
        # Default to 'speed' if still empty
        if not target:
            target = 'speed'
        
        logger.info(f"Flat query: target={target}")
        
        # Get all drivers
        all_drivers = bridge.telemetry_buffer.get_all_drivers()
        if not all_drivers:
            return jsonify([])
        
        # Build time series - array of objects
        # Focus on key drivers: LEC, HAM, VER (top 3 in standings)
        key_drivers = ['LEC', 'HAM', 'VER']
        time_points = {}
        
        for driver in key_drivers:
            if driver not in all_drivers:
                continue
            data_points = bridge.telemetry_buffer.get_driver_data(driver, target)
            for ts, value in data_points:
                # Round to nearest 100ms
                ms = ts.microsecond // 100000 * 100000
                ts_rounded = ts.replace(microsecond=ms)
                # Use ISO format for time (Grafana prefers this)
                ts_iso = ts_rounded.strftime('%Y-%m-%dT%H:%M:%S.') + f'{ms // 1000:03d}Z'
                
                if ts_iso not in time_points:
                    time_points[ts_iso] = {'time': ts_iso}
                time_points[ts_iso][f'{target}_{driver}'] = float(value)
        
        # Only keep rows with ALL 3 key drivers
        result = [
            point for point in time_points.values()
            if len(point) == 4  # time + 3 drivers
        ]
        result = sorted(result, key=lambda x: x['time'])
        
        logger.info(f"Flat query returning {len(result)} complete time points for {key_drivers}")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Flat query error: {e}", exc_info=True)
        return jsonify([])


@app.route('/annotations', methods=['POST'])
def annotations():
    """
    Grafana annotations endpoint
    Returns alert markers
    """
    try:
        data = request.get_json()
        logger.info("Annotations request received")
        
        # Parse time range
        range_data = data.get('range', {})
        from_str = range_data.get('from')
        to_str = range_data.get('to')
        
        from_time = None
        to_time = None
        if from_str:
            try:
                from_time = datetime.fromisoformat(from_str.replace('Z', '+00:00'))
            except:
                pass
        if to_str:
            try:
                to_time = datetime.fromisoformat(to_str.replace('Z', '+00:00'))
            except:
                pass
        
        # Get alerts
        alerts = bridge.alerts_buffer.get_alerts(from_time, to_time)
        
        # Format for Grafana
        annotations = []
        for alert in alerts:
            annotations.append({
                'time': int(alert['timestamp'].timestamp() * 1000),
                'title': alert['alert_type'],
                'text': f"{alert['driver_id']}: {alert['description']}",
                'tags': [alert['severity'], alert['driver_id']],
            })
        
        return jsonify(annotations)
    
    except Exception as e:
        logger.error(f"Annotations error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/tag-keys', methods=['POST'])
def tag_keys():
    """Return available tag keys"""
    return jsonify([
        {'type': 'string', 'text': 'driver'},
        {'type': 'string', 'text': 'metric'},
        {'type': 'string', 'text': 'severity'},
    ])


@app.route('/tag-values', methods=['POST'])
def tag_values():
    """Return tag values for a given key"""
    data = request.get_json()
    key = data.get('key', '')
    
    if key == 'driver':
        drivers = bridge.telemetry_buffer.get_all_drivers()
        return jsonify([{'text': d} for d in drivers])
    elif key == 'severity':
        return jsonify([
            {'text': 'high'},
            {'text': 'medium'},
            {'text': 'low'}
        ])
    
    return jsonify([])


@app.route('/stats', methods=['GET'])
def stats():
    """Service statistics endpoint"""
    return jsonify(bridge.get_stats())


@app.route('/drivers', methods=['GET'])
def drivers():
    """Get all active drivers"""
    drivers_list = bridge.telemetry_buffer.get_all_drivers()
    
    # Get latest values for each driver
    result = []
    for driver_id in drivers_list:
        latest = bridge.telemetry_buffer.get_latest_values(driver_id)
        if latest:
            result.append({
                'driver_id': driver_id,
                **latest
            })
    
    return jsonify(result)


@app.route('/alerts/summary', methods=['GET'])
def alerts_summary():
    """Get alert summary by severity"""
    counts = bridge.alerts_buffer.get_alert_count_by_severity()
    recent = bridge.alerts_buffer.get_alerts()[-10:]  # Last 10 alerts
    
    return jsonify({
        'counts': counts,
        'recent': [
            {
                'timestamp': alert['timestamp'].isoformat(),
                'severity': alert['severity'],
                'driver_id': alert['driver_id'],
                'type': alert['alert_type'],
                'description': alert['description'],
            }
            for alert in recent
        ]
    })


def main():
    """Main entry point"""
    global bridge
    
    # Load configuration
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'config', 'grafana_bridge_config.yaml'
    )
    
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    # Initialize bridge
    bridge = GrafanaKafkaBridge(config_path)
    
    # Start bridge service
    bridge.start()
    
    # Get server config
    host = bridge.config['bridge']['host']
    port = bridge.config['bridge']['port']
    debug = bridge.config['bridge']['debug']
    
    logger.info(f"Starting Grafana Kafka Bridge on {host}:{port}")
    logger.info("Grafana datasource URL: http://localhost:5001")
    logger.info("Press Ctrl+C to stop")
    
    try:
        app.run(host=host, port=port, debug=debug, threaded=True)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        bridge.stop()


if __name__ == '__main__':
    main()

