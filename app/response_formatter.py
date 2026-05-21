from dataclasses import dataclass


@dataclass
class RecommendationCard:
    title: str
    year: str
    rating: str
    countries: str
    genres: str
    overview: str


def format_recommendations(
    cards: list[RecommendationCard],
    media_type: str,
    *,
    requested: int,
) -> str:
    if not cards:
        return ""

    icon = "📺" if media_type == "tv" else "🎬"
    kind = "сериалов" if media_type == "tv" else "фильмов"
    lines: list[str] = []

    if len(cards) < requested:
        lines.append(
            f"Нашёл {len(cards)} из {requested} запрошенных {kind} в TMDB:\n"
        )
    else:
        lines.append(f"Подборка из {len(cards)} {kind}:\n")

    for card in cards:
        lines.append(f"{icon} {card.title} ({card.year})")
        lines.append(f"⭐ {card.rating} | {card.countries} | {card.genres}")
        if card.overview:
            lines.append(card.overview)
        lines.append("")

    return "\n".join(lines).strip()
