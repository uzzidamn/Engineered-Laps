#!/usr/bin/env python3
"""
Simple Kafka Producer for Grafana Dashboard
Streams F1 telemetry data to Kafka without any web UI
"""

import os
import sys
import glob

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.kafka_producer import RealTimeProducer

def main():
    print("\n" + "=" * 60)
    print("   🏎️  F1 Kafka Producer (for Grafana)")
    print("=" * 60)
    
    # Find latest data file
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "data")
    
    data_files = glob.glob(os.path.join(data_dir, "*.csv"))
    data_files += glob.glob(os.path.join(data_dir, "*.parquet"))
    
    if not data_files:
        print("❌ No data files found in data/ directory")
        print("   Please run data preparation first.")
        sys.exit(1)
    
    latest_file = max(data_files, key=os.path.getmtime)
    format_type = 'parquet' if latest_file.endswith('.parquet') else 'csv'
    
    print(f"\n📂 Loading data from: {os.path.basename(latest_file)}")
    
    # Initialize producer with drivers
    drivers = ['VER', 'HAM', 'LEC']  # Change these if you want different drivers
    print(f"🏁 Monitoring drivers: {', '.join(drivers)}")
    
    config_path = os.path.join(project_root, "config", "config.yaml")
    producer = RealTimeProducer(config_path=config_path, driver_ids=drivers)
    
    # Load data
    print(f"⏳ Loading cache file...")
    if not producer.load_cache(latest_file, format=format_type):
        print("❌ Failed to load cache file")
        sys.exit(1)
    
    print(f"✅ Loaded {producer.cache_manager.get_num_records()} records")
    
    # Start streaming
    print("\n" + "=" * 60)
    print("   🚀 Starting Kafka Producer")
    print("=" * 60)
    print("\n📡 Streaming F1 telemetry to Kafka...")
    print("   Topic: f1-telemetry")
    print("   Speed factor: 1.0x (real-time)")
    print("\n💡 Open Grafana dashboard: http://localhost:3000")
    print("   Press Ctrl+C to stop\n")
    
    try:
        # Stream in a loop for continuous data
        loop_count = 0
        while True:
            loop_count += 1
            print(f"\n🔄 Starting loop {loop_count}...")
            
            # Reload cache for each loop
            if loop_count > 1:
                print(f"⏳ Reloading cache...")
                if not producer.load_cache(latest_file, format=format_type):
                    print("❌ Failed to reload cache")
                    break
            
            # Stream at real-time frequency
            stats = producer.stream_at_frequency(
                speed_factor=1.0,
                start_immediately=True,
                duration_seconds=None  # Stream all data
            )
            
            if stats:
                print(f"✅ Loop {loop_count} completed: {stats.get('messages_sent', 0)} messages sent")
            
            print(f"⏳ Waiting 2 seconds before next loop...")
            import time
            time.sleep(2)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping producer...")
        print("✅ Producer stopped\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

