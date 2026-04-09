from cache import make_cache_key


def test_make_cache_key_format():
    assert make_cache_key("test question") == "research:test question"


def test_make_cache_key_lowercases():
    assert make_cache_key("Hello World") == "research:hello world"


def test_make_cache_key_strips_whitespace():
    assert make_cache_key("  hello  ") == "research:hello"


def test_make_cache_key_same_question_same_key():
    # Same question phrased with different casing should hit the same cache entry
    assert make_cache_key("LeBron James") == make_cache_key("lebron james")
