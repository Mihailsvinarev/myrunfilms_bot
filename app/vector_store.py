import chromadb

from app.embeddings import create_embedding


client = chromadb.PersistentClient(
    path="chroma_db"
)

collection = client.get_or_create_collection(
    name="movies"
)


def add_movie(movie_id, title):

    embedding = create_embedding(title)

    collection.add(
        ids=[str(movie_id)],
        documents=[title],
        embeddings=[embedding],
    )


def search_movies(query, n_results=5):

    query_embedding = create_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
    )

    return results