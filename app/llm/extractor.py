# Functions to call OpenAI/Ollama
import json
import os
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
from app.llm.prompts import SYSTEM_PROMPT

load_dotenv()

# Configuration
HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
# We use a model known for good JSON instruction following
MODEL_ID = os.getenv("HF_MODEL_ID", "meta-llama/Llama-3.1-8B-Instruct")

client = InferenceClient(token=HF_TOKEN)

def extract_entities(text: str):
    """
    Sends text to Hugging Face Inference API and returns a structured dictionary.
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract knowledge from this text: {text}"}
            ],
            temperature=0.1,  # Low temperature = more deterministic/consistent
            max_tokens=500
        )
        
        raw_content = response.choices[0].message.content
        
        # CLEANUP: LLMs often wrap JSON in ```json ... ``` code blocks. We remove them.
        clean_content = raw_content.replace("```json", "").replace("```", "").strip()
        
        # Parse JSON
        data = json.loads(clean_content)
        return data

    except json.JSONDecodeError:
        print(f"❌ LLM failed to return valid JSON. Raw output: {raw_content[:50]}...")
        return None
    except Exception as e:
        print(f"❌ Error calling Hugging Face: {e}")
        return None
    


def generate_answer(query: str, context: list):
    """
    Sends the User Query + Graph Context to the LLM to generate a natural answer.
    """
    if not context:
        return "I don't know based on the current data."

    # Turn list of strings into a single block of text
    context_str = "\n".join(context)
    
    # BALANCED PROMPT
    prompt = f"""
    Context:
    {context_str}
    
    User Question: {query}
    
    Instructions:
    1. Answer the question in a **complete, natural sentence**.
    2. Do NOT use introductory filler like "Based on the context", "The data indicates", or "According to the graph".
    3. Do NOT just output a single word (e.g., instead of "Starship", say "SpaceX is going to launch Starship").
    4. Combine relevant details if possible (e.g., mention the location if it is in the context).
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                # Changed system role to encourage natural speech
                {"role": "system", "content": "You are a direct and helpful assistant. You answer using full sentences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3, # Slight increase to allow better sentence structure
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"



def extract_search_term(user_query: str):
    """
    Uses the LLM to extract the core entity name from a conversational query.
    Example: "Tell me about Elon Musk" -> "Elon Musk"
    """
    # Simple heuristic: If it's short (1-2 words), just return it.
    if len(user_query.split()) <= 2:
        return user_query

    prompt = f"""
    Extract the main Entity or Topic from this user query. 
    Return ONLY the entity name. Do not add punctuation or extra words.
    
    Query: "{user_query}"
    Entity:
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=10
        )
        cleaned_term = response.choices[0].message.content.strip()
        # Remove any accidental quotes the LLM might add
        return cleaned_term.replace('"', '').replace("'", "")
    except Exception:
        # Fallback: Just return the original query if LLM fails
        return user_query