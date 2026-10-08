import pytest

from scripts.zap_scan import check_target


@pytest.mark.parametrize("url", ["http://127.0.0.1:8080", "http://localhost:8080/search?q=a"])
def test_local_targets_allowed(url):
    assert check_target(url) == url


@pytest.mark.parametrize("url", [
    "http://example.com", "https://10.0.0.5:8080", "http://127.0.0.1.evil.com", "http://0.0.0.0:8080",
])
def test_non_local_targets_refused(url):
    with pytest.raises(ValueError):
        check_target(url)
