from fastapi.testclient import TestClient
from main import app
client=TestClient(app)
def test_health_without_firebase_credentials():
    assert client.get('/health').json()=={'status':'ok'}
def test_commands_require_bearer_identity():
    assert client.post('/commands',json={'command':'issue','args':[]}).status_code in (401,403)
