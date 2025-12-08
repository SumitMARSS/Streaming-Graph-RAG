# # Neo4j connection & Cypher queries (Phase 4)
# import os
# from neo4j import GraphDatabase
# from dotenv import load_dotenv

# load_dotenv()

# # Configuration
# URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
# USER = os.getenv("NEO4J_USER", "neo4j")
# PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

# class Neo4jClient:
#     def __init__(self):
#         self.driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

#     def close(self):
#         self.driver.close()

#     def upsert_graph_data(self, data):
#         """
#         Takes the JSON output from the LLM and writes it to Neo4j.
#         Uses MERGE to ensure no duplicates.
#         """
#         if not data:
#             return

#         # Build a mapping from name to label for all entities
#         name_to_label = {e["name"]: e.get("label", "Entity") for e in data.get("entities", [])}

#         with self.driver.session() as session:
#             # 1. Create Nodes (Entities)
#             for entity in data.get("entities", []):
#                 session.execute_write(self._create_node, entity)
            
#             # 2. Create Relationships
#             for relation in data.get("relationships", []):
#                 # Add head_label and tail_label if not present
#                 relation = dict(relation)  # make a copy
#                 if "head_label" not in relation:
#                     relation["head_label"] = name_to_label.get(relation["head"], "Entity")
#                 if "tail_label" not in relation:
#                     relation["tail_label"] = name_to_label.get(relation["tail"], "Entity")
#                 session.execute_write(self._create_relationship, relation)

#     @staticmethod
#     def _create_node(tx, entity):
#         label = entity["label"].replace(" ", "_") if "label" in entity else "Entity"
#         query = (
#             f"MERGE (n:{label} {{name: $name}}) "
#             "ON CREATE SET n.created_at = timestamp() "
#             "ON MATCH SET n.last_seen = timestamp()"
#         )
#         tx.run(query, name=entity["name"])


#     @staticmethod
#     def _create_relationship(tx, relation):
#         # We sanitize the relationship type to be uppercase and safe
#         rel_type = relation["type"].upper().replace(" ", "_")
#         # Use dynamic labels for head and tail if available
#         head_label = relation.get("head_label", "Entity").replace(" ", "_")
#         tail_label = relation.get("tail_label", "Entity").replace(" ", "_")
#         query = f'''
#         MATCH (h:{head_label} {{name: $head}})
#         MATCH (t:{tail_label} {{name: $tail}})
#         MERGE (h)-[r:{rel_type}]->(t)
#         ON CREATE SET r.created_at = timestamp()
#         '''
#         tx.run(query, head=relation["head"], tail=relation["tail"])



#     # def search_graph(self, query_text):
#     #     """
#     #     1. Fuzzy search for nodes that match the query text.
#     #     2. Return the node and its immediate neighbors (1-hop context).
#     #     """
#     #     with self.driver.session() as session:
#     #         # Cypher query:
#     #         # 1. Search for a node where the name contains the search term (case-insensitive)
#     #         # 2. MATCH that node and its neighbors
#     #         # 3. Return the relationship and the neighbor
#     #         cypher_query = """
#     #         MATCH (n:Entity)
#     #         WHERE toLower(n.name) CONTAINS toLower($query)
#     #         MATCH (n)-[r]-(neighbor)
#     #         RETURN n.name as subject, type(r) as relation, neighbor.name as object
#     #         LIMIT 25
#     #         """
#     #         result = session.run(cypher_query, {"query": query_text})
            
#     #         # Format the results into a list of sentences
#     #         context_lines = []
#     #         for record in result:
#     #             # "Apple ACQUIRES Anthropic"
#     #             line = f"{record['subject']} {record['relation']} {record['object']}"
#     #             context_lines.append(line)
            
#     #         return context_lines



#     def search_graph(self, query_text):
#         """
#         1. Fuzzy search for nodes that match the query text.
#         2. Return 1-hop AND 2-hop neighbors (Friends of Friends).
#         """
#         with self.driver.session() as session:
#             # Updated Cypher Query for 2-Hop Traversal
#             cypher_query = """
#             MATCH (n:Entity)
#             WHERE toLower(n.name) CONTAINS toLower($query)
            
#             // Find paths up to 2 steps away
#             MATCH path = (n)-[*1..2]-(m)
            
#             // We unwind the path to get every relationship in the chain
#             UNWIND relationships(path) AS r
            
#             // Return unique triples
#             RETURN DISTINCT startNode(r).name as subject, type(r) as relation, endNode(r).name as object
#             LIMIT 50
#             """
#             result = session.run(cypher_query, {"query": query_text})
#             context_lines = []
#             graph_edges = []  # <--- FIX: create graph edge list

#             for rec in result:
#                 # Build sentence for LLM
#                 context_lines.append(
#                     f"{rec['subject']} {rec['relation']} {rec['object']}"
#                 )

#                 # Build graph JSON for frontend
#                 graph_edges.append({
#                     "source": rec["subject"],
#                     "relation": rec["relation"],
#                     "target": rec["object"]
#                 })

#             # Return only serializable objects
#             return list(set(context_lines)), graph_edges

# # Singleton instance for easy import
# neo4j_client = Neo4jClient()

  
import os
import textwrap
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

    def close(self):
        self.driver.close()

    def upsert_graph_data(self, data):
        """
        Takes the JSON output from the LLM and writes it to Neo4j.
        """
        if not data:
            return

        with self.driver.session() as session:
            # 1. Create Nodes (Entities)
            for entity in data.get("entities", []):
                session.execute_write(self._create_node, entity)
            
            # 2. Create Relationships
            for relation in data.get("relationships", []):
                session.execute_write(self._create_relationship, relation)

    @staticmethod
    def _create_node(tx, entity):
        raw_label = entity.get("label", "Entity")
        safe_label = "".join(char for char in raw_label if char.isalnum())
        if not safe_label: safe_label = "Entity"

        # FIX: Moved 'SET n:{safe_label}' to the END.
        # Order must be: MERGE -> ON CREATE/MATCH -> SET
        query = textwrap.dedent(f"""
            MERGE (n:Entity {{name: $name}})
            ON CREATE SET n.created_at = timestamp()
            ON MATCH SET n.last_seen = timestamp()
            SET n:{safe_label}
        """)
        
        tx.run(query, name=entity["name"])

    @staticmethod
    def _create_relationship(tx, relation):
        rel_type = relation["type"].upper().replace(" ", "_")
        
        # Robust Logic: MERGE nodes first to ensure they exist
        query = textwrap.dedent(f"""
            MERGE (h:Entity {{name: $head}})
            MERGE (t:Entity {{name: $tail}})
            MERGE (h)-[r:{rel_type}]->(t)
            ON CREATE SET r.created_at = timestamp()
        """)
        
        tx.run(query, head=relation["head"], tail=relation["tail"])

    def search_graph(self, query_text):
        with self.driver.session() as session:
            cypher_query = """
            MATCH (n:Entity)
            WHERE toLower(n.name) CONTAINS toLower($query)
            MATCH path = (n)-[*1..2]-(m)
            UNWIND relationships(path) AS r
            RETURN DISTINCT startNode(r).name as subject, type(r) as relation, endNode(r).name as object
            LIMIT 50
            """
            result = session.run(cypher_query, {"query": query_text})
            
            context_lines = []
            graph_data = []

            for rec in result:
                context_lines.append(f"{rec['subject']} {rec['relation']} {rec['object']}")
                graph_data.append({
                    "source": rec["subject"],
                    "target": rec["object"],
                    "label": rec["relation"]
                })

            return list(set(context_lines)), graph_data

neo4j_client = Neo4jClient()