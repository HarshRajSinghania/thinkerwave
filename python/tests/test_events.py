from thinkerwave.events import parse_sse


def test_parse_sse_frames_comments_and_multiline_data():
    lines = ["id: 3", "event: round.started", 'data: {"round": 1}', "", ": keepalive", "",
             "event: x", "data: a", "data: b", ""]
    assert list(parse_sse(lines)) == [("3", "round.started", '{"round": 1}'), (None, "x", "a\nb")]
