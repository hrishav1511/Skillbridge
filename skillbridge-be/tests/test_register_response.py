from skillbridge.api.repositories.auth.register import _Returnable


def test_returnable_exposes_dict_values_as_attributes():
    payload = _Returnable({"id": "abc123", "full_name": "Test User"})

    assert payload.id == "abc123"
    assert payload.full_name == "Test User"
    assert payload.to_dict() == {"id": "abc123", "full_name": "Test User"}
