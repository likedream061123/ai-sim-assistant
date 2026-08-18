import os
from unittest.mock import patch, Mock
from agent import serpapi


def test_search_returns_results():
    fake = Mock()
    fake.raise_for_status = Mock()
    fake.json.return_value = {
        "organic_results": [
            {"title": "Steel elastic modulus", "snippet": "E = 200 GPa", "link": "https://x"},
        ]
    }
    with patch("agent.serpapi.requests.get", return_value=fake) as m:
        out = serpapi.search("steel elastic modulus")
    assert out[0]["title"] == "Steel elastic modulus"
    m.assert_called_once()


def test_search_requires_key():
    with patch.dict(os.environ, {"SERPAPI_KEY": ""}, clear=False):
        try:
            serpapi.search("steel", api_key=None)
            assert False, "should have raised"
        except ValueError as e:
            assert "SERPAPI_KEY" in str(e)
