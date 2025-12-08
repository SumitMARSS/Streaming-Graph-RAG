# Script to read CSV & send to Kafka (Phase 2)

import pandas as pd
import json
import time
import os
from kafka import KafkaProducer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "news-stream")

def json_serializer(data):
    """Helper to convert dictionary to JSON string"""
    return json.dumps(data).encode("utf-8")

def start_stream():
    print(f"🔄 Connecting to Kafka at {KAFKA_SERVER}...")
    
    # Initialize Producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_SERVER],
            value_serializer=json_serializer
        )
        print("✅ Connected to Kafka!")
    except Exception as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        return

    # Read CSV
    csv_path = os.path.join("data", "news_data.csv")
    if not os.path.exists(csv_path):
        print(f"❌ Error: File {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    print(f"🚀 Starting stream to topic: '{TOPIC_NAME}'...")

    # Iterate and Send
    for index, row in df.iterrows():
        message = {
            "id": int(row["id"]), # Convert numpy int to python int
            "text": row["text"],
            "timestamp": row["timestamp"]
        }
        
        # Send to Kafka
        producer.send(TOPIC_NAME, value=message)
        print(f"Sent ID {row['id']}: {row['text'][:40]}...")
        
        # Simulate real-time delay (2 seconds)
        time.sleep(2)

    # Ensure all messages are sent
    producer.flush()
    producer.close()
    print("✅ Stream finished.")

if __name__ == "__main__":
    start_stream()