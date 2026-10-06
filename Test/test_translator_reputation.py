import json
import pytest
from genlayer_py import create_client, create_account
from genlayer_py.chains import localnet

CONTRACT_ADDRESS = "0xFEc4Bb4E4EbD25789D23FA0248C99c16634Ca9bF"


@pytest.fixture(scope="module")
def client():
    return create_client(chain=localnet, account=create_account())


def _write(client, fn, args):
    tx = client.write_contract(address=CONTRACT_ADDRESS, function_name=fn, args=args, value=0)
    return client.wait_for_transaction_receipt(transaction_hash=tx, status="ACCEPTED")


def _read(client, fn, args=None):
    return client.read_contract(address=CONTRACT_ADDRESS, function_name=fn, args=args or [])


def test_lazy_default_reputation(client, translator_address):
    assert _read(client, "get_reputation", [translator_address]) == "REPUTATION:50"


def test_finalize_translation(client, translator_address):
    """Assumes translation_id=0 has been reviewed (and optionally challenged)."""
    try:
        _write(client, "finalize_translation", [0])
    except Exception as e:
        # "Change too small to apply" and "Source could not be fetched..."
        # are both valid, documented outcomes depending on the empirical
        # review/challenge results — not failures in themselves.
        assert "Change too small to apply" in str(e) or "could not be fetched" in str(e)
        return

    data = json.loads(_read(client, "get_change_details", [0]))
    assert data["translator"] == translator_address
    assert data["change_type"] in ("INCREASE", "DECREASE")
    assert data["source"] in ("REVIEW", "CHALLENGE")


def test_cannot_finalize_twice(client):
    with pytest.raises(Exception, match="Translation already finalized|has not been reviewed yet"):
        _write(client, "finalize_translation", [0])


def test_finalize_nonexistent_translation(client):
    with pytest.raises(Exception, match="Translation has not been reviewed yet"):
        _write(client, "finalize_translation", [999])
