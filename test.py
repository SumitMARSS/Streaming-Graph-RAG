from neo4j import GraphDatabase
from kafka import KafkaAdminClient

def check_connections():
    # 1. Check Neo4j
    try:
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"))
        driver.verify_connectivity()
        print("✅ Neo4j Connection Successful!")
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j Failed: {e}")

    # 2. Check Kafka
    try:
        admin_client = KafkaAdminClient(bootstrap_servers="localhost:9092")
        print("✅ Kafka Connection Successful!")
        admin_client.close()
    except Exception as e:
        print(f"❌ Kafka Failed: {e}")

if __name__ == "__main__":
    check_connections()