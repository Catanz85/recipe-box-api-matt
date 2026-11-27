class DevelopmentConfig:
    TESTING = False
    DATABASE = "recipes.db"
    CACHE_TYPE = "SimpleCache"
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = True


class TestingConfig:
    TESTING = True
    DATABASE = "testing-recipes.db"
    CACHE_TYPE = "SimpleCache"
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = True


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}
