import json
import pathlib

import yaml  # dev dependency: pyyaml
from jsonschema import Draft202012Validator

from fake_api import ANSWER, EVENTS

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_answer_schema_accepts_the_fake_answer():
    schema = json.loads((ROOT / "spec/answer.schema.json").read_text())
    Draft202012Validator(schema).validate(ANSWER)


def test_events_schema_covers_every_public_event():
    schema = json.loads((ROOT / "spec/events.schema.json").read_text())
    for name, data in EVENTS:
        if name == "future.event":
            continue
        Draft202012Validator(schema["$defs"][name]).validate(data)


def test_openapi_lists_exactly_the_public_paths():
    spec = yaml.safe_load((ROOT / "spec/openapi.yaml").read_text())
    assert set(spec["paths"]) == {"/me", "/runs", "/runs/{id}", "/runs/{id}/stop", "/runs/{id}/answer",
                                  "/runs/{id}/rounds", "/runs/{id}/files", "/runs/{id}/files/{path}",
                                  "/runs/{id}/events"}
    assert spec["servers"][0]["url"] == "https://api.thinkerwave.ai/api/v1"
