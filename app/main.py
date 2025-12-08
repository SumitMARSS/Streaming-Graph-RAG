import json
import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer
from dotenv import load_dotenv
from app.database.neo4j_client import neo4j_client
from app.llm.extractor import generate_answer, extract_search_term

load_dotenv()

app = FastAPI(title="Streaming Knowledge Graph API")

# --- Configuration ---
KAFKA_SERVER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME = os.getenv("KAFKA_TOPIC", "news-stream")

# --- Kafka Producer Setup ---
# We create a global producer instance
producer = None

@app.on_event("startup")
async def startup_event():
    global producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_SERVER],
            value_serializer=lambda x: json.dumps(x).encode("utf-8")
        )
        print("✅ Kafka Producer initialized for API.")
    except Exception as e:
        print(f"❌ Failed to start Kafka Producer: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if producer:
        producer.close()

# --- Data Models ---
class NewsIngestRequest(BaseModel):
    text: str
    source: str = "API"

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"status": "Knowledge Graph API is running"}

@app.post("/ingest")
async def ingest_data(item: NewsIngestRequest):
    """
    Receives text data and pushes it to Kafka for processing.
    {
        "text": "A research team at the University of Kyoto has developed a bioengineered coral capable of surviving rising ocean temperatures. According to their report, the modified coral showed a 40% higher heat tolerance and is scheduled to be deployed in the Great Barrier Reef in early 2026.",
        "source": "Scientific Daily"
    }

    """
    if not producer:
        raise HTTPException(status_code=500, detail="Kafka Producer is not active")

    # Create a message payload
    message = {
        "id": int(time.time()),  # Use timestamp as a simple unique ID
        "text": item.text,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": item.source
    }

    try:
        # Send to Kafka (Fire and Forget)
        producer.send(TOPIC_NAME, value=message)
        return {"status": "success", "message": "Data queued for processing", "data_id": message["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
def search(q: str):
    # (Keep your existing search logic here)
    print(f"🔎 Raw User Query: {q}")
    clean_query = extract_search_term(q)
    context, graph_edges = neo4j_client.search_graph(clean_query)
    answer = generate_answer(q, context)
    
    return {
        "original_query": q,
        "search_term": clean_query,
        "context_found": context,
        "answer": answer,
        "graph": graph_edges
    }