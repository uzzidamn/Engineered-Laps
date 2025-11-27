"""
Real-time metrics collection and aggregation
Collects data from Kafka consumers and calculates statistics
"""

import json
import time
import threading
from datetime import datetime
from collections import deque, defaultdict
from typing import Dict, List, Any, Optional


class MetricsCollector:
    """
    Collects and aggregates metrics from Kafka consumers
    Maintains historical data for visualization
    """
    
    def __init__(self, history_size: int = 1000):
        """
        Initialize metrics collector
        
        Args:
            history_size: Number of historical data points to keep
        """
        self.history_size = history_size
        
        # Thread-safe data structures
        self.lock = threading.Lock()
        
        # Wheel spin metrics
        self.wheel_spin_events = deque(maxlen=history_size)
        self.wheel_spin_by_driver = defaultdict(int)
        
        # Gear anomaly metrics
        self.gear_anomalies = deque(maxlen=history_size)
        self.gear_lugging = 0
        self.gear_over_rev = 0
        self.gear_by_gear = defaultdict(int)
        self.total_gear_samples = 0
        
        # Alert metrics
        self.alerts = deque(maxlen=history_size)
        self.alerts_by_severity = defaultdict(int)
        
        # Telemetry metrics (for graphs)
        self.telemetry_data = deque(maxlen=100)  # Last 100 data points for graphing
        self.speed_history = deque(maxlen=50)
        self.rpm_history = deque(maxlen=50)
        self.throttle_history = deque(maxlen=50)
        self.telemetry_by_driver = defaultdict(lambda: {
            'speed': deque(maxlen=20),
            'rpm': deque(maxlen=20),
            'throttle': deque(maxlen=20)
        })
        
        # Producer/consumer metrics
        self.producer_messages = 0
        self.producer_start_time = time.time()
        self.consumer_messages = defaultdict(int)
        self.consumer_start_times = defaultdict(lambda: time.time())
        
        # Event log
        self.events = deque(maxlen=100)
        
        # Add startup event
        self._add_event('INFO', 'Metrics collector initialized')
    
    def add_message(self, consumer_name: str, message: Any):
        """
        Process and add a message from a consumer
        
        Args:
            consumer_name: Name of the consumer ('wheel_spin', 'gear_anomalies', 'alerts')
            message: The Kafka message
        """
        with self.lock:
            # Update consumer count
            self.consumer_messages[consumer_name] += 1
            
            # Parse message value
            try:
                if hasattr(message, 'value'):
                    data = json.loads(message.value.decode('utf-8'))
                else:
                    data = message
                
                # Route to appropriate handler
                if consumer_name == 'wheel_spin':
                    self._process_wheel_spin(data)
                elif consumer_name == 'gear_anomalies':
                    self._process_gear_anomaly(data)
                elif consumer_name == 'alerts':
                    self._process_alert(data)
                    
            except Exception as e:
                self._add_event('WARNING', f'Error processing message: {str(e)}')
    
    def _process_wheel_spin(self, data: Dict[str, Any]):
        """Process wheel spin telemetry data"""
        # Calculate wheel spin (simplified logic)
        rpm = data.get('RPM', 0)
        speed = data.get('Speed', 0)
        gear = data.get('nGear', 0)
        throttle = data.get('Throttle', 0)
        driver = data.get('driver_id', 'UNK')
        
        # Store telemetry data for graphs
        self._store_telemetry(driver, speed, rpm, throttle)
        
        # Simple wheel spin detection: high RPM but low speed
        if rpm > 12000 and speed < 150 and gear > 0:
            event = {
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'driver': driver,
                'speed': speed,
                'gear': gear,
                'rpm': rpm
            }
            self.wheel_spin_events.append(event)
            self.wheel_spin_by_driver[driver] += 1
            self._add_event('DATA', f'Wheel spin detected: {driver}')
    
    def _store_telemetry(self, driver: str, speed: float, rpm: float, throttle: float):
        """Store telemetry data for graphing"""
        # Global history
        self.speed_history.append(speed)
        self.rpm_history.append(rpm)
        self.throttle_history.append(throttle)
        
        # Per-driver history
        self.telemetry_by_driver[driver]['speed'].append(speed)
        self.telemetry_by_driver[driver]['rpm'].append(rpm)
        self.telemetry_by_driver[driver]['throttle'].append(throttle)
        
        # Store complete telemetry point
        self.telemetry_data.append({
            'driver': driver,
            'speed': speed,
            'rpm': rpm,
            'throttle': throttle,
            'timestamp': time.time()
        })
    
    def _process_gear_anomaly(self, data: Dict[str, Any]):
        """Process gear anomaly data"""
        self.total_gear_samples += 1
        
        rpm = data.get('RPM', 0)
        speed = data.get('Speed', 0)
        gear = data.get('nGear', 0)
        throttle = data.get('Throttle', 0)
        driver = data.get('driver_id', 'UNK')
        
        # Store telemetry data for graphs
        self._store_telemetry(driver, speed, rpm, throttle)
        
        # Detect lugging (low RPM for gear)
        if gear > 2 and rpm < 8000 and speed > 50:
            self.gear_lugging += 1
            self.gear_by_gear[gear] += 1
            event = {
                'type': 'lugging',
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'driver': driver,
                'gear': gear,
                'rpm': rpm
            }
            self.gear_anomalies.append(event)
        
        # Detect over-revving (high RPM for gear)
        elif gear < 8 and rpm > 14000:
            self.gear_over_rev += 1
            self.gear_by_gear[gear] += 1
            event = {
                'type': 'over_rev',
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'driver': driver,
                'gear': gear,
                'rpm': rpm
            }
            self.gear_anomalies.append(event)
    
    def _process_alert(self, data: Dict[str, Any]):
        """Process alert data"""
        severity = data.get('severity', 'low')
        alert_type = data.get('alert_type', 'unknown')
        driver = data.get('driver_id', 'UNK')
        value = data.get('value', '')
        
        alert = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'severity': severity,
            'type': alert_type,
            'driver': driver,
            'value': value
        }
        
        self.alerts.append(alert)
        self.alerts_by_severity[severity] += 1
        
        # Add to event log
        if severity == 'high':
            self._add_event('ALERT', f'{driver} high speed detected: {value} km/h')
        elif alert_type == 'drs_status':
            self._add_event('INFO', f'{driver} DRS status: {value}')
        elif alert_type == 'brake_temp':
            self._add_event('WARNING', f'{driver} brake temperature: {value}°C')
    
    def _add_event(self, level: str, message: str):
        """Add an event to the log"""
        event = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'level': level,
            'message': message
        }
        self.events.append(event)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get current metrics summary
        
        Returns:
            Dictionary with all current metrics
        """
        with self.lock:
            # Calculate rates
            producer_uptime = time.time() - self.producer_start_time
            producer_rate = self.producer_messages / producer_uptime if producer_uptime > 0 else 0
            
            consumer_rates = {}
            for name, count in self.consumer_messages.items():
                uptime = time.time() - self.consumer_start_times[name]
                consumer_rates[name] = {
                    'message_rate': count / uptime if uptime > 0 else 0,
                    'total_messages': count,
                    'lag': 0  # TODO: Calculate actual lag
                }
            
            return {
                'producer': {
                    'total_messages': self.producer_messages,
                    'message_rate': producer_rate,
                    'uptime': producer_uptime
                },
                'wheel_spin': {
                    'total_events': len(self.wheel_spin_events),
                    'by_driver': dict(self.wheel_spin_by_driver),
                    'recent': list(self.wheel_spin_events)[-10:],
                    **consumer_rates.get('wheel_spin', {})
                },
                'gear_anomalies': {
                    'lugging': self.gear_lugging,
                    'over_rev': self.gear_over_rev,
                    'total_samples': self.total_gear_samples,
                    'by_gear': dict(self.gear_by_gear),
                    'recent': list(self.gear_anomalies)[-10:],
                    **consumer_rates.get('gear_anomalies', {})
                },
                'alerts': {
                    'by_severity': dict(self.alerts_by_severity),
                    'recent': list(self.alerts)[-10:],
                    **consumer_rates.get('alerts', {})
                },
                'telemetry': {
                    'speed_history': list(self.speed_history),
                    'rpm_history': list(self.rpm_history),
                    'throttle_history': list(self.throttle_history),
                    'by_driver': {
                        driver: {
                            'speed': list(data['speed']),
                            'rpm': list(data['rpm']),
                            'throttle': list(data['throttle'])
                        }
                        for driver, data in self.telemetry_by_driver.items()
                    },
                    'current_speed': self.speed_history[-1] if self.speed_history else 0,
                    'current_rpm': self.rpm_history[-1] if self.rpm_history else 0,
                    'current_throttle': self.throttle_history[-1] if self.throttle_history else 0,
                    'avg_speed': sum(self.speed_history) / len(self.speed_history) if self.speed_history else 0,
                    'max_speed': max(self.speed_history) if self.speed_history else 0,
                }
            }
    
    def get_recent_events(self, n: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent events from the log
        
        Args:
            n: Number of recent events to return
            
        Returns:
            List of recent events
        """
        with self.lock:
            return list(self.events)[-n:]
    
    def update_producer_count(self, count: int):
        """
        Update producer message count
        
        Args:
            count: New total message count
        """
        with self.lock:
            self.producer_messages = count
            if count % 100 == 0:  # Log every 100 messages
                self._add_event('INFO', f'Producer sent {count} messages')
    
    def reset(self):
        """Reset all metrics"""
        with self.lock:
            # Clear collections
            self.wheel_spin_events.clear()
            self.wheel_spin_by_driver.clear()
            self.gear_anomalies.clear()
            self.alerts.clear()
            self.alerts_by_severity.clear()
            
            # Reset counters
            self.gear_lugging = 0
            self.gear_over_rev = 0
            self.gear_by_gear.clear()
            self.total_gear_samples = 0
            self.producer_messages = 0
            self.consumer_messages.clear()
            
            # Reset timestamps
            self.producer_start_time = time.time()
            self.consumer_start_times.clear()
            
            # Clear events but add reset event
            self.events.clear()
            self._add_event('INFO', 'Metrics reset')
    
    def get_wheel_spin_sparkline(self, width: int = 20) -> str:
        """
        Generate a sparkline for wheel spin events over time
        
        Args:
            width: Width of sparkline in characters
            
        Returns:
            Unicode sparkline string
        """
        with self.lock:
            if not self.wheel_spin_events:
                return '▁' * width
            
            # Count events in time buckets
            now = time.time()
            bucket_size = 60 / width  # 1 minute divided into buckets
            buckets = [0] * width
            
            # This is simplified - in production you'd track timestamps properly
            # For now, just show relative distribution
            max_val = max(self.wheel_spin_by_driver.values()) if self.wheel_spin_by_driver else 1
            
            # Create sparkline characters
            chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
            return ''.join([chars[min(7, int(v / max_val * 8))] for v in buckets])
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics for analysis
        
        Returns:
            Dictionary with detailed statistics
        """
        with self.lock:
            return {
                'wheel_spin': {
                    'total_events': len(self.wheel_spin_events),
                    'events_per_driver': dict(self.wheel_spin_by_driver),
                    'avg_events_per_driver': sum(self.wheel_spin_by_driver.values()) / len(self.wheel_spin_by_driver) if self.wheel_spin_by_driver else 0
                },
                'gear_anomalies': {
                    'total_anomalies': self.gear_lugging + self.gear_over_rev,
                    'lugging_count': self.gear_lugging,
                    'over_rev_count': self.gear_over_rev,
                    'anomaly_rate': ((self.gear_lugging + self.gear_over_rev) / self.total_gear_samples * 100) if self.total_gear_samples > 0 else 0,
                    'by_gear': dict(self.gear_by_gear)
                },
                'alerts': {
                    'total_alerts': len(self.alerts),
                    'by_severity': dict(self.alerts_by_severity),
                    'high_percentage': (self.alerts_by_severity.get('high', 0) / len(self.alerts) * 100) if len(self.alerts) > 0 else 0
                },
                'overall': {
                    'total_messages': sum(self.consumer_messages.values()),
                    'producer_messages': self.producer_messages,
                    'uptime_seconds': time.time() - self.producer_start_time
                }
            }

