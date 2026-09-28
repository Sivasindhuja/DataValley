import pytest
from app.auth.models import AuthContext
from app.auth.service import create_access_token, decode_access_token
from app.tools.seed import seed

@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    seed()
    return True

@pytest.fixture
def auth_c102():
    return AuthContext(authenticated=True, user_id="C102", customer_id="C102", roles=["customer"])

@pytest.fixture
def auth_c103():
    return AuthContext(authenticated=True, user_id="C103", customer_id="C103", roles=["customer"])

@pytest.fixture
def auth_c104_locked():
    return AuthContext(authenticated=True, user_id="C104", customer_id="C104", roles=["customer"])

@pytest.fixture
def unauth():
    return AuthContext(authenticated=False, customer_id=None, roles=["customer"])

def make_auth(customer_id: str, roles=None):
    roles = roles or ["customer"]
    return AuthContext(authenticated=True, user_id=customer_id, customer_id=customer_id, roles=roles)

@pytest.fixture
def make_auth_fixture():
    return make_auth
