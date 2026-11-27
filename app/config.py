class DevelopmentConfig:
    TESTING = False
    DATABASE = "recipes.db"
    CACHE_TYPE = "SimpleCache"


class TestingConfig:
    TESTING = True
    DATABASE = "testing-recipes.db"
    CACHE_TYPE = "SimpleCache"


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}
