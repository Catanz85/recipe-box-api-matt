class DevelopmentConfig:
    TESTING = False
    DATABASE = "recipes.db"


class TestingConfig:
    TESTING = True
    DATABASE = "testing-recipes.db"


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
}
