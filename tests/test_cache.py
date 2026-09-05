from cache import make_cache_key


def test_make_cache_key_format():
    assert make_cache_key("test question", 4) == "research:test question:4"


def test_make_cache_key_lowercases():
    assert make_cache_key("Hello World", 4) == "research:hello world:4"


def test_make_cache_key_strips_whitespace():
    assert make_cache_key("  hello  ", 4) == "research:hello:4"


def test_make_cache_key_same_question_same_key():
    # Same question phrased with different casing should hit the same cache entry
    assert make_cache_key("LeBron James", 4) == make_cache_key("lebron james", 4)


def test_make_cache_key_varies_with_num_agents():
    # A 12-agent run must not be served research cached under a 4-agent run
    assert make_cache_key("same question", 4) != make_cache_key("same question", 12)
