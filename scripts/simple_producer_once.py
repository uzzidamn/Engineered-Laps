#!/usr/bin/env python3
"""
Simple Kafka Producer - Single Race Version
Streams F1 telemetry data to Kafka ONCE and then stops
"""

import os
import sys
import glob

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.kafka_producer import RealTimeProducer

def main():
    print("\n" + "=" * 60)
    print("   🏎️  F1 Kafka Producer (Single Race)")
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
    
    num_records = producer.cache_manager.get_num_records()
    print(f"✅ Loaded {num_records} records")
    
    # Start streaming
    print("\n" + "=" * 60)
    print("   🚀 Starting Kafka Producer (ONE RACE ONLY)")
    print("=" * 60)
    print("\n📡 Streaming F1 telemetry to Kafka...")
    print("   Topic: f1-telemetry")
    print("   Speed factor: 1.0x (real-time)")
    print("   Mode: Single race (will stop after completion)")
    print("\n💡 Open Grafana dashboard: http://localhost:3000")
    print("   Press Ctrl+C to stop early\n")
    
    try:
        # Stream ONCE - no loop
        stats = producer.stream_at_frequency(
            speed_factor=1.0,
            start_immediately=True,
            duration_seconds=None  # Stream all data
        )
        
        if stats:
            messages_sent = stats.get('messages_sent', 0)
            duration = stats.get('duration_seconds', 0)
            rate = stats.get('messages_per_second', 0)
            
            print("\n" + "=" * 60)
            print("   ✅ RACE COMPLETED!")
            print("=" * 60)
            print(f"\n📊 Statistics:")
            print(f"   • Messages sent: {messages_sent:,}")
            print(f"   • Duration: {duration:.1f} seconds")
            print(f"   • Average rate: {rate:.1f} msg/s")
            print(f"   • Records processed: {num_records:,}")
            print("\n🏁 Producer finished. Exiting gracefully.\n")
        else:
            print("\n❌ No statistics returned from streaming")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user. Stopping producer...")
        print("✅ Producer stopped\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

