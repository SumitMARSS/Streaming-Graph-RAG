# # Script to read Kafka & trigger AI (Phase 3)
# import json
# import os
# from kafka import KafkaConsumer
# from dotenv import load_dotenv
# from app.llm.extractor import extract_entities

# load_dotenv()

# KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
# TOPIC_NAME = os.getenv("KAFKA_TOPIC", "news-stream")

# def start_consumer():
#     print(f"👂 Connecting Consumer to {KAFKA_SERVER}...")
    
#     try:
#         # Initialize Consumer
#         consumer = KafkaConsumer(
#             TOPIC_NAME,
#             bootstrap_servers=[KAFKA_SERVER],
#             auto_offset_reset='earliest', # Start from beginning if we missed data
#             enable_auto_commit=True,
#             group_id='kg-builder-group',  # Important for keeping track of what we read
#             value_deserializer=lambda x: json.loads(x.decode('utf-8'))
#         )
#         print(f"✅ Consumer listening on topic: '{TOPIC_NAME}'")
#     except Exception as e:
#         print(f"❌ Connection Failed: {e}")
#         return

#     # The Infinite Loop
#     for message in consumer:
#         news_item = message.value
#         print(f"\n📥 Received News ID: {news_item.get('id')}")
        
#         # 1. Extract Entities (The AI Step)
#         print("   🧠 Analyzing with LLM...")
#         graph_data = extract_entities(news_item.get('text', ''))
        
#         if graph_data:
#             # 2. Visualize what we got (Debugging)
#             print(f"   ✅ Extracted: {len(graph_data.get('entities', []))} Entities, {len(graph_data.get('relationships', []))} Relationships")
#             print(f"   Structure: {json.dumps(graph_data, indent=2)}")
            
#             # TODO (Phase 4): Insert into Neo4j
#             # save_to_neo4j(graph_data)
#         else:
#             print("   ⚠️ No data extracted.")

# if __name__ == "__main__":
#     start_consumer()


# Script for saving in Neo4j (Phase 4)

import json
import os
from kafka import KafkaConsumer
from dotenv import load_dotenv
from app.llm.extractor import extract_entities
from app.database.neo4j_client import neo4j_client

load_dotenv()

# Configuration
KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "news-stream")

def start_consumer():
    print(f"👂 Connecting Consumer to {KAFKA_SERVER}...")
    
    try:
        # Initialize Consumer
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=[KAFKA_SERVER],
            auto_offset_reset='earliest', # Start from beginning if we missed data
            enable_auto_commit=True,
            group_id='kg-builder-group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        print(f"✅ Consumer listening on topic: '{TOPIC_NAME}'")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    try:
        # The Infinite Loop
        for message in consumer:
            news_item = message.value
            print(f"\n📥 Received News ID: {news_item.get('id')}")
            
            # 1. AI Extraction
            print("   🧠 Analyzing with LLM...")
            graph_data = extract_entities(news_item.get('text', ''))
            
            if graph_data:
                # 2. PRINT to Terminal (Detailed View)
                print(f"   ✅ Extracted: {len(graph_data.get('entities', []))} Entities, {len(graph_data.get('relationships', []))} Relationships")
                print(f"   Structure: {json.dumps(graph_data, indent=2)}")
                
                # 3. SAVE to Neo4j (Database Storage)
                print("   💾 Saving to Neo4j...")
                try:
                    neo4j_client.upsert_graph_data(graph_data)
                    print("   ✨ Graph Updated Successfully!")
                except Exception as db_err:
                    print(f"   ❌ Database Error: {db_err}")
            else:
                print("   ⚠️ No data extracted.")
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping consumer...")
        neo4j_client.close()
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    start_consumer()