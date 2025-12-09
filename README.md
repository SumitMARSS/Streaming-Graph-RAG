# Streaming-KG

## Overview
Streaming-KG is a real-time Knowledge Graph pipeline that ingests unstructured data (like news articles), extracts structured knowledge using LLMs, and stores it in a graph database (Neo4j). The system enables advanced search, reasoning, and visualization over continuously updated knowledge.

## Complete Flow Diagram
<img width="3511" height="1057" alt="Flow_Diagram" src="https://github.com/user-attachments/assets/939b0e35-a8dc-432a-a3e0-944eb6ae49aa" />


## What is RAG (Retrieval-Augmentation-Generation)?
RAG is a modern approach to building AI systems that answer questions using both a knowledge base and a language model. Streaming-KG implements RAG as follows:

### 1. R = Retrieval (Fetching the Facts)
- **Where:** `app/database/neo4j_client.py`
- **Function:** `search_graph(query_text)`
- **What it does:** Instead of asking the LLM to guess, you query your Neo4j Graph Database. You look for nodes that match the user's keyword and "traverse" the graph to find connected neighbors (context).
- **The Code:**
  ```python
  # This is the "Retrieval" part
  cypher_query = """
  MATCH (n:Entity) WHERE ... CONTAINS ...
  MATCH path = (n)-[*1..2]-(m) ...
  RETURN ...
  """
  ```

### 2. A = Augmentation (Combining Context)
- **Where:** `app/main.py`
- **Function:** `/search` endpoint
- **What it does:** You take the user's raw question (`q`) and combine it with the data found in step 1 (`context`). You are "augmenting" the prompt with real facts.
- **The Code:**
  ```python
  # 1. Get facts from DB
  context, graph_visuals = neo4j_client.search_graph(clean_query)

  # 2. Pass BOTH the question AND the facts to the LLM
  answer = generate_answer(q, context)
  ```

### 3. G = Generation (The AI Answer)
- **Where:** `app/llm/extractor.py`
- **Function:** `generate_answer(query, context)`
- **What it does:** The LLM receives a prompt that says: "Here is some context I found in the database. Use ONLY this context to answer the user's question." It generates the final natural language sentence.
- **The Code:**
  ```python
  prompt = f"""
  Context from the Graph:
  {context_str}

  User Question: {query}
  ...
  """
  client.chat.completions.create(...) # Generates the answer
  ```

## 🛠️ Tech Stack
- **Backend:** Python 3.10+, FastAPI
- **Streaming:** Apache Kafka, Zookeeper
- **Database:** Neo4j (Graph Database)
- **AI/LLM:** Ollama (Local Llama 3) or HuggingFace
- **Infrastructure:** Docker & Docker Compose

## Why This Project?
- **Automated Knowledge Extraction:** Converts raw text into structured, queryable knowledge.
- **Real-Time Updates:** Ingests and processes data streams (e.g., news, research) as they arrive.
- **Graph Representation:** Uses Neo4j to model entities and relationships, enabling rich queries and visualizations.
- **AI Integration:** Leverages LLMs (e.g., Llama, Zephyr) for entity/relation extraction and natural language answers.
- **Scalable & Modular:** Built with Kafka for streaming, FastAPI for APIs, and modular Python code for easy extension.

## Architecture & Data Flow

```
[User/API/CSV] → [Kafka Producer] → [Kafka Topic] → [Kafka Consumer]
      |                                         |
      |                                         ↓
      |                                 [LLM Extraction]
      |                                         ↓
      |                                 [Neo4j Graph DB]
      |                                         ↓
      |                                 [FastAPI Search API]
      |                                         ↓
      |                                 [Frontend/UI]
```

### Step-by-Step Flow
1. **Ingestion:**
   - Data (news, research, etc.) is sent via API or CSV to a Kafka topic.
2. **Streaming:**
   - Kafka decouples producers and consumers, enabling scalable, real-time pipelines.
3. **Extraction:**
   - Kafka consumer reads messages and uses an LLM to extract entities and relationships.
4. **Graph Storage:**
   - Extracted knowledge is upserted into Neo4j as nodes (with dynamic labels) and relationships.
5. **Search & Reasoning:**
   - FastAPI provides endpoints for search and Q&A over the graph.
6. **Visualization:**
   - Frontend (or Neo4j Browser) visualizes the evolving knowledge graph.

## 📦 Installation & Setup

### 1. Prerequisites
- Docker Desktop (Required for Kafka & Neo4j)
- Ollama (Required for local LLM inference)
- Python 3.10+

### 2. Clone Repository
```bash
git clone <repo-url>
cd streaming-kg
```

### 3. Environment Setup
Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Create a `.env` file in the root directory:
```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=news-stream

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# LLM (Ollama)
OLLAMA_BASE_URL=http://localhost:11434/v1
MODEL_ID=llama3
```

### 4. Start Infrastructure
Run Docker Compose to spin up Kafka, Zookeeper, and Neo4j:
```bash
docker-compose up -d
```
- Neo4j UI: http://localhost:7474 (User: neo4j, Pass: password123)
- Kafka UI: http://localhost:8080

### 5. Start AI Model
Ensure Ollama is running and pull the model:
```bash
ollama pull llama3
```

## 🏃‍♂️ Usage
You need to run two terminals.

**Terminal 1: The Worker (Consumer)**
This listens to Kafka and processes data.
```bash
python -m app.kafka.consumer
```

**Terminal 2: The API (Server)**
This handles user requests and data ingestion.
```bash
uvicorn app.main:app --reload
```

## 🧪 Testing the Pipeline

### 1. Ingest Data (Simulate a News Stream)
Send a POST request to inject a news item.
```bash
curl -X POST "http://127.0.0.1:8000/ingest" \
     -H "Content-Type: application/json" \
     -d '{"text": "SpaceX launched the Starship rocket from Texas yesterday."}'
```
Check Terminal 1: You should see the extraction logs and Neo4j update.

### 2. Search the Graph (RAG)
Ask a natural language question.
```bash
# Open in Browser or use Curl
http://127.0.0.1:8000/search?q=What did SpaceX launch?
```
Response: "SpaceX launched the Starship rocket from Texas."

## 📂 Project Structure

```
streaming-kg/
├── docker-compose.yml       # Kafka & Neo4j Services
├── requirements.txt         # Python Dependencies
├── .env                    # Environment Variables
├── app/
│   ├── main.py              # FastAPI Entry Point (Ingest & Search)
│   ├── kafka/
│   │   ├── consumer.py      # The "Worker" (Kafka -> LLM -> Neo4j)
│   │   └── producer.py      # (Optional) Bulk CSV Loader
│   ├── llm/
│   │   ├── extractor.py     # LLM Logic (Ollama/OpenAI)
│   │   └── prompts.py       # System Prompts for JSON Extraction
│   └── database/
│       └── neo4j_client.py  # Graph Logic (Cypher Queries)
└── data/                    # Sample CSVs
```

## Why is This Useful?
- **Automates knowledge extraction and structuring from unstructured sources.**
- **Enables advanced search, reasoning, and analytics over dynamic data.**
- **Supports real-time updates and scalable ingestion.**
- **Flexible for many domains: news, research, finance, etc.**

## Future Directions
- Add more LLMs and prompt templates for better extraction.
- Integrate with more data sources (APIs, RSS, etc.).
- Enhance the frontend for interactive graph exploration.
- Add user authentication and access control.
- Support for temporal and event-based reasoning.
- Deploy as a cloud-native microservice.

## 🤝 Contributing
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License
MIT
