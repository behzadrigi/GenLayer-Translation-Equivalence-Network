import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x49e619D87E43348C9081d8c6760A6A559e6A6b7C"
VERDICTS = ("UPHELD", "OVERTURNED")


@pytest.fixture(scope="module")
def client():
    return create_client(chain=localnet, account=create_account())


def _write(client, address_client, fn, args):
    tx = address_client.write_contract(address=CONTRACT_ADDRESS, function_name=fn, args=args, value=0)
    return address_client.wait_for_transaction_receipt(transaction_hash=tx, status="ACCEPTED")


def _read(client, fn, args=None):
    return client.read_contract(address=CONTRACT_ADDRESS, function_name=fn, args=args or [])


def test_translator_cannot_self_challenge(client, translator_client):
    """Assumes translation_id=0 (reviewed) belongs to translator_client's address."""
    with pytest.raises(Exception, match="Translator cannot challenge their own translation"):
        _write(client, translator_client, "raise_challenge", [0, "test reason"])


def test_challenge_unreviewed_translation(client, challenger_client):
    with pytest.raises(Exception, match="Translation has not been reviewed yet"):
        _write(client, challenger_client, "raise_challenge", [999, "test reason"])


def test_raise_challenge(client, challenger_client, challenger_address):
    _write(client, challenger_client, "raise_challenge", [0, "I dispute this review"])
    data = json.loads(_read(client, "get_challenge_data", [0]))
    assert data["challenger"] == challenger_address
    assert data["verdict"] in VERDICTS
    assert isinstance(data["source_fetched"], bool)


def test_cannot_challenge_twice(client, challenger_client):
    with pytest.raises(Exception, match="Already challenged"):
        _write(client, challenger_client, "raise_challenge", [0, "another reason"])
