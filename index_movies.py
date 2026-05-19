from app.movie_search import load_movies
from app.vector_store import add_movie


movies = load_movies()

print("INDEXING MOVIES...")

for _, row in movies.iterrows():

    add_movie(
        movie_id=row["movieId"],
        title=row["title"],
    )

print("DONE")