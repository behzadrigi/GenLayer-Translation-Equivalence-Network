import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0xd46F053d1B6d521c905CcC21B3aCD7BE689Db31A"


@pytest.fixture(scope="module")
def client():
    return create_client(chain=localnet, account=create_account())


def _write(client, fn, args):
    tx = client.write_contract(address=CONTRACT_ADDRESS, function_name=fn, args=args, value=0)
    return client.wait_for_transaction_receipt(transaction_hash=tx, status="ACCEPTED")


def _read(client, fn, args=None):
    return client.read_contract(address=CONTRACT_ADDRESS, function_name=fn, args=args or [])


def test_review_translation(client):
    """Assumes translation_id=0 from test_translation_registry.py exists."""
    _write(client, "review_translation", [0])
    data = json.loads(_read(client, "get_review_data", [0]))
    assert isinstance(data["source_fetched"], bool)
    # finalize-worthy data should only be trusted when source_fetched is true;
    # report the actual empirical values either way.
    for field in ("semantic_equivalence", "no_omissions", "no_additions"):
        assert isinstance(data[field], bool)
    assert data["status"] == "REVIEWED"


def test_cannot_review_twice(client):
    with pytest.raises(Exception, match="Already reviewed"):
        _write(client, "review_translation", [0])


def test_review_nonexistent_translation(client):
    with pytest.raises(Exception, match="Translation not found in registry"):
        _write(client, "review_translation", [999])
