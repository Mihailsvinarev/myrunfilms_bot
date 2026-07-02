from app.composition import AppServices, build_app_services
from app.protocols import MovieSearchService


def test_build_app_services_returns_search_service():
    services = build_app_services()
    assert isinstance(services, AppServices)
    assert isinstance(services.search_service, MovieSearchService)
