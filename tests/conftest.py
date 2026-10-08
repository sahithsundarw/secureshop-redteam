import pytest
from werkzeug.security import generate_password_hash as _real_hash

import routes_auth
import seed


def _fast_hash(password):
    # Same salted-hash format, far fewer iterations: seeding runs for every test.
    return _real_hash(password, method="pbkdf2:sha256:1000")


@pytest.fixture(autouse=True)
def fast_hashing_and_private_log(monkeypatch, tmp_path_factory):
    monkeypatch.setattr(seed, "generate_password_hash", _fast_hash)
    monkeypatch.setattr(routes_auth, "generate_password_hash", _fast_hash)
    monkeypatch.setenv("SECURESHOP_LOG", str(tmp_path_factory.mktemp("logs") / "security.log"))
