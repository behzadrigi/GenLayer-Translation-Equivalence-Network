import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0x381f31CFA75a4A81D791fDEb32B928847E0D0c02"


@pytest.fixture(scope="module")
def client():
    return create_client(chain=localnet, account=create_account())


def _write(client, fn, args):
    tx = client.write_contract(address=CONTRACT_ADDRESS, function_name=fn, args=args, value=0)
    return client.wait_for_transaction_receipt(transaction_hash=tx, status="ACCEPTED")


def _read(client, fn, args=None):
    return client.read_contract(address=CONTRACT_ADDRESS, function_name=fn, args=args or [])


def test_invalid_source_url_rejected(client):
    with pytest.raises(Exception, match="Invalid source URL"):
        _write(client, "submit_translation", ["not_a_url", "Spanish", "texto"])


def test_empty_target_lang_rejected(client):
    with pytest.raises(Exception, match="Target language cannot be empty"):
        _write(client, "submit_translation", ["https://www.python.org/about", "", "texto"])


def test_empty_translated_text_rejected(client):
    with pytest.raises(Exception, match="Translated text cannot be empty"):
        _write(client, "submit_translation", ["https://www.python.org/about", "Spanish", ""])


def test_submit_translation(client, sender_address):
    _write(client, "submit_translation", [
        "https://www.python.org/about", "Spanish",
        "Python es un lenguaje de programación potente y fácil de aprender.",
    ])
    data = json.loads(_read(client, "get_translation_data", [0]))
    assert data["translator"] == sender_address
    assert data["status"] == "SUBMITTED"
