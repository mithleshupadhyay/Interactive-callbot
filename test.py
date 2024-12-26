from database import generate_embeddings
from pinecone import Pinecone
import os
from dotenv import load_dotenv
import openai

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = os.getenv("INDEX_NAME", "callerbotindex")

# Initialize OpenAI API client
openai.api_key = os.getenv("OPENAI_API_KEY")

def query_existing_pinecone_index(query, top_k=5):
    """Query the existing Pinecone index."""
    try:
        # Generate query embedding
        query_embedding = generate_embeddings([query])  # Note: Expecting a list input
        if not query_embedding or not isinstance(query_embedding[0], list):
            print("Failed to generate query embedding or invalid embedding format.")
            return None

        # Connect to Pinecone index
        index = pc.Index(index_name)

        # Query the Pinecone index
        # results = index.query(queries=[query_embedding[0]], top_k=top_k, namespace="product_info")
        results = index.query(
            namespace="product_info",
            # vector=[0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
            vector=query_embedding,
            top_k=top_k,
            # include_values=True
            include_metadata=True
        )

        # Process and return the results
        return [
            {
                "id": match["id"],
                "score": match["score"],
                "metadata": match.get("metadata")
            }
            for match in results["matches"]
        ]
    except Exception as e:
        print(f"Error querying Pinecone: {e}")
        return None

# Example execution
if __name__ == "__main__":
    query = "Home Loan N: Interest rate 5.15%, 15 years term, 30% Down payment"
    results = query_existing_pinecone_index(query)
    if results:
        print("Query Results:")
        for result in results:
            print(result)
    else:
        print("No results found.")
