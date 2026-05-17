import pytest

from trojanspec.utils.json_extract import JSONExtractionError, extract_json


def test_bare_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_fenced_json():
    assert extract_json("text\n```json\n{\"a\": 2}\n```\nmore") == {"a": 2}


def test_unlabelled_fence():
    assert extract_json("```\n{\"a\": 3}\n```") == {"a": 3}


def test_braces_inside_strings_do_not_unbalance():
    txt = 'prefix {"code": "method F() { return {}; }", "ok": true} suffix'
    assert extract_json(txt) == {"code": "method F() { return {}; }", "ok": True}


def test_escaped_quotes_in_strings():
    assert extract_json(r'{"s": "a \" brace } here"}') == {"s": 'a " brace } here'}


def test_failure_raises():
    with pytest.raises(JSONExtractionError):
        extract_json("no json at all")
    with pytest.raises(JSONExtractionError):
        extract_json("")
