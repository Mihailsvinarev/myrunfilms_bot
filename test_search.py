from app.vector_store import search_movies

query = "мрачная фантастика"

results = search_movies(query)

print("\nTOP MOVIES:\n")

for doc in results["documents"][0]:
    print("-", doc)