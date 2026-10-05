import base64
import os
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(SERVER.parents[1] / "engine"))
os.environ["PEHCHAAN_NO_AUTOAPP"] = "1"

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from pehchaan_api.main import create_app  # noqa: E402

ANALYST = {"X-Role": "fraud_analyst", "X-Analyst": "a.verma", "X-Access-Reason": "test"}


class Device:
    def __init__(self, client, device_id, user_id):
        self.key = Ed25519PrivateKey.generate()
        pub = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.device_id = device_id
        r = client.post("/v1/devices/register", json={"device_id": device_id, "user_id": user_id,
                                                      "public_key_b64": base64.b64encode(pub).decode()})
        assert r.status_code == 200

    def sign(self, challenge_id, nonce, answer):
        return base64.b64encode(self.key.sign(f"pehchaan-fv|{challenge_id}|{nonce}|{answer}".encode())).decode()


@pytest.fixture()
def client(tmp_path):
    os.environ["PEHCHAAN_DATA"] = str(tmp_path)
    app = create_app(db_path=str(tmp_path / "t.db"), key_path=str(tmp_path / "k.pem"))
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def device_factory():
    return Device
