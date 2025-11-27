#!/usr/bin/env python3
"""
Standalone Kafka Producer Script
Run this script in the background to continuously stream F1 telemetry data to Kafka.

Usage:
    python scripts/run_producer.py [--speed-factor SPEED] [--loop]
    
    --speed-factor: Playback speed multiplier (default: 1.0 = real-time)
    --loop: Loop data continuously (replay from beginning when finished)
    
Examples:
    # Real-time streaming (all data once)
    python scripts/run_producer.py
    
    # 10x speed (faster for testing)
    python scripts/run_producer.py --speed-factor 10.0
    
    # Continuous loop (replay data forever)
    python scripts/run_producer.py --loop
    
    # Run in background
    nohup python scripts/run_producer.py --speed-factor 10.0 > producer.log 2>&1 &
"""

import sys
import os
import argparse
import signal
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.kafka_producer import RealTimeProducer
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global producer instance for signal handling
producer_instance = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    logger.info("\n🛑 Shutdown signal received. Closing producer...")
    if producer_instance:
        producer_instance.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def find_latest_data_file(data_dir):
    """Find the most recent data file"""
    data_path = project_root / "data"
    if not data_path.exists():
        logger.error(f"Data directory not found: {data_path}")
        return None
    
    data_files = list(data_path.glob("*.csv")) + list(data_path.glob("*.parquet"))
    if not data_files:
        logger.error(f"No data files found in {data_path}")
        return None
    
    latest_file = max(data_files, key=lambda f: f.stat().st_mtime)
    return latest_file

def main():
    parser = argparse.ArgumentParser(description='Kafka Producer for F1 Telemetry Streaming')
    parser.add_argument('--speed-factor', type=float, default=1.0,
                       help='Playback speed multiplier (1.0 = real-time, 10.0 = 10x faster)')
    parser.add_argument('--loop', action='store_true',
                       help='Loop data continuously (replay from beginning when finished)')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                       help='Path to config file (relative to project root)')
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("F1 Telemetry Kafka Producer - Continuous Streaming")
    logger.info("=" * 60)
    logger.info(f"Speed factor: {args.speed_factor}x")
    logger.info(f"Loop mode: {'Enabled' if args.loop else 'Disabled'}")
    logger.info("=" * 60)
    
    # Find data file
    data_file = find_latest_data_file(project_root / "data")
    if not data_file:
        sys.exit(1)
    
    logger.info(f"📁 Using data file: {data_file.name}")
    
    # Initialize producer
    config_path = project_root / args.config
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        sys.exit(1)
    
    global producer_instance
    producer_instance = RealTimeProducer(config_path=str(config_path))
    
    # Load data
    format_type = 'parquet' if data_file.suffix == '.parquet' else 'csv'
    if not producer_instance.load_cache(str(data_file), format=format_type):
        logger.error("Failed to load data cache")
        sys.exit(1)
    
    num_records = producer_instance.cache_manager.get_num_records()
    frequency = producer_instance.cache_manager.get_frequency()
    estimated_duration = num_records / frequency / args.speed_factor
    
    logger.info(f"📊 Loaded {num_records:,} records")
    logger.info(f"📊 Frequency: {frequency:.2f} Hz")
    logger.info(f"⏱️  Estimated duration: {estimated_duration/3600:.2f} hours ({estimated_duration/60:.1f} minutes)")
    logger.info("")
    
    # Stream data
    iteration = 1
    total_messages = 0
    
    try:
        while True:
            logger.info(f"🔄 Starting stream iteration {iteration}...")
            
            stats = producer_instance.stream_at_frequency(
                duration_seconds=None,  # No limit
                speed_factor=args.speed_factor
            )
            
            total_messages += stats.get('messages_sent', 0)
            logger.info(f"✅ Iteration {iteration} completed: {stats.get('messages_sent', 0):,} messages")
            logger.info(f"📈 Total messages sent: {total_messages:,}")
            
            if not args.loop:
                logger.info("✅ All data streamed. Exiting (use --loop to replay continuously)")
                break
            
            # Reset cache for next iteration
            logger.info("🔄 Resetting cache for next iteration...")
            producer_instance.cache_manager.reset()
            iteration += 1
            time.sleep(1)  # Brief pause between iterations
            
    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error during streaming: {e}", exc_info=True)
    finally:
        if producer_instance:
            producer_instance.close()
        logger.info("👋 Producer stopped")

if __name__ == "__main__":
    main()

