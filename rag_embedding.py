"""
Rag module
"""

import csv, chromadb, config
from mistralai import Mistral

MODEL = "mistral-embed"
DB = chromadb.Client().get_or_create_collection("docs")
client = Mistral(api_key=config.MISTRAL_API_KEY)

def read_memory(n, query=""):
    with open("data.csv", newline="", encoding="utf-8") as f:
        docs = [f"{r['content']}" for r in csv.DictReader(f)]

    embeds_response = client.embeddings.create(model=MODEL, inputs=docs)
    embeds =[item.embedding for item in embeds_response.data]
    DB.upsert(ids=[str(i) for i in range(len(docs))], embeddings=embeds, documents=docs)

    q_embed_response = client.embeddings.create(model=MODEL, inputs=[query])
    q_embed = q_embed_response.data[0].embedding
    res = DB.query(query_embeddings=[q_embed], n_results=n)
    
    return res['documents'][0] if res['documents'] else[]

def write_memory(content):
    with open("data.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["content"])
        if f.tell() == 0: writer.writeheader()
        writer.writerow({"content": content})

if __name__ == "__main__":
    write_memory("Néo dislike eating plastic.")
    print(read_memory(5, query="What does Néo dislike?"))