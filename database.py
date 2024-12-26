from pinecone import Pinecone
import os
from dotenv import load_dotenv
import openai  

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

index_name = os.getenv("INDEX_NAME", "callerbotindex")
# index_name = pc.Index("callerbotindex")

# Initialize OpenAI API client
openai.api_key = os.getenv("OPENAI_API_KEY")

# Setup function (no need to create the index since it's manually created)
def setup_pinecone():
    """Function to setup Pinecone and ensure the index exists."""
    try:
        # Ensure the index exists
        if index_name not in pc.list_indexes().names():
            print(f"Index {index_name} not found in Pinecone.")
        else:
            print(f"Index {index_name} is available.")
    except Exception as e:
        print(f"Error while checking index: {e}")

# Function to read data from the product_info.txt file
def read_product_info(file_path="/home/rudra/Desktop/callerbot/data/product_info.txt"):
    """Reads product information from the provided file."""
    try:
        with open(file_path, "r") as file:
            # Each line in the file represents a product's info
            product_info = [line.strip() for line in file.readlines()]
        return product_info
    except Exception as e:
        print(f"Error reading product info from {file_path}: {e}")
        return []

# Function to generate embeddings for product info using OpenAI
def generate_embeddings(texts):
    """Generate embeddings using OpenAI's model."""
    try:
        embeddings = []
        for text in texts:
            response = openai.Embedding.create(  
                model="text-embedding-ada-002",  
                input=text
            )
            embedding = response.data[0].embedding
            print(f"Generated Embedding: {embedding[:5]}...")  # Print first 5 values for validation
            embeddings.append(embedding)
        return embeddings
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return []

# Function to upsert product info embeddings into Pinecone
def upsert_product_info_to_pinecone():
    """Upserts product info embeddings into the Pinecone index."""
    product_info = read_product_info()

    if not product_info:
        print("No product information found to upsert.")
        return

    # Generate embeddings for the product information
    embeddings = generate_embeddings(product_info)

    if not embeddings:
        print("Failed to generate embeddings.")
        return

    # Prepare the data for upsert
    vectors = []
    for i, embedding in enumerate(embeddings):
        vectors.append({
            "id": f"product_{i+1}",  # Unique ID for each product
            "values": embedding,
            "metadata": {"product_info": product_info[i]}  # Storing the original product information as metadata
        })

    try:
        # Connect to the index
        index = pc.Index(index_name)
        
        # Upsert the vectors into Pinecone (adjust namespace as needed)
        index.upsert(vectors=vectors, namespace="product_info")
        print(f"Successfully upserted {len(vectors)} product information vectors into Pinecone.")
    except Exception as e:
        print(f"Error while upserting into Pinecone: {e}")

# Function to retrieve product info embeddings from Pinecone
def get_product_info_from_pinecone(query="loan product details", top_k=5):
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

# def get_product_info_from_pinecone(query="loan product details"):
#     """Function to retrieve product info from Pinecone."""
#     # try:
#     #     index = pc.Index(index_name)  
#     #     # result = index.query(query, top_k=5, namespace="product_info")  
#     #     response = openai.Embedding.create(
#     #         model="text-embedding-ada-002",
#     #         input=query
#     #     )
#     #     query_embedding = response.data[0].embedding
#     #     result = index.query(queries=[query_embedding], top_k=5, namespace="product_info")
#     #     return result['matches']  
#     try:
#         # Generate embedding for the query
#         query_embedding = generate_embeddings([query])[0]
#         # Connect to the index
#         index = pc.Index(index_name)
#         # Query the index
#         results = index.query(queries=[query_embedding], top_k=5)
#         return results["matches"]
    
#     except Exception as e:
#         print(f"Error while querying Pinecone: {e}")
#         return []

# If you want to run the upsert_product_info_to_pinecone function, you can call it here
# upsert_product_info_to_pinecone()  # Uncomment to run the upsert when required

# Run the setup_pinecone function
# setup_pinecone()
