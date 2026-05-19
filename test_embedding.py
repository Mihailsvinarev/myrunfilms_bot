from app.embeddings import create_embedding

embedding = create_embedding(
    "грустная фантастика"
)

print(len(embedding))