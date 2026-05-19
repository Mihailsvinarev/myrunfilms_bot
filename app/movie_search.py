import pandas as pd


def load_movies():

    movies = pd.read_csv("data/movies.csv")

    return movies


def get_movie_titles():

    movies = load_movies()

    return movies["title"].tolist()