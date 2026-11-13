"""Local browser request boundaries and walkthrough media delivery."""
import urllib.request
from unittest.mock import Mock
import pytest
from test_server import server, _post  # noqa: F401
from orthoplan.server import Handler


@pytest.mark.parametrize("error", [BrokenPipeError, ConnectionResetError])
def test_cancelled_scan_response_does_not_attempt_second_response(error):
    handler = object.__new__(Handler)
    handler.path = "/"
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = Mock()
    handler.wfile.write.side_effect = error("client cancelled download")
    handler._send_json = Mock()
    handler.do_GET()
    handler.send_response.assert_called_once_with(200)
    handler.wfile.write.assert_called_once()
    handler._send_json.assert_not_called()


@pytest.mark.parametrize("origin", ["https://untrusted.example", "null"])
def test_cross_origin_posts_are_rejected_before_dispatch(server, monkeypatch, origin):  # noqa: F811 - pytest fixture injection
    def unexpected(*args, **kwargs):
        pytest.fail("Cross-origin request reached model dispatch")
    monkeypatch.setattr("orthoplan.server.preview_goal_payload", unexpected)
    status, _ = _post(server, b'{}', {"Origin": origin, "Content-Type": "text/plain"}, path="/api/preview-goal")
    assert status == 403


def test_same_origin_requests_remain_supported(server):  # noqa: F811 - pytest fixture injection
    status, payload = _post(server, b'{"id":"same-origin"}', {"Origin": f"http://127.0.0.1:{server}"})
    assert status == 200 and payload["ok"]


@pytest.mark.parametrize("path,mime", [("/workflow-demo.webm", "video/webm"), ("/workflow-demo.vtt", "text/vtt")])
def test_walkthrough_media_uses_browser_supported_content_types(server, path, mime):  # noqa: F811 - pytest fixture injection
    with urllib.request.urlopen(f"http://127.0.0.1:{server}{path}") as response:
        assert response.headers.get_content_type() == mime


def test_geometry_job_round_trip_and_release(server):  # noqa: F811 - pytest fixture injection
    import json
    import time
    status, started = _post(server, json.dumps({'operation': 'evaluate', 'payload': {'id': 'job-http'}}).encode(), path='/api/geometry-jobs')
    assert status == 200 and started['ok']
    key = started['job_id']
    for _ in range(100):
        with urllib.request.urlopen(f'http://127.0.0.1:{server}/api/geometry-jobs/{key}') as response:
            job = json.load(response)
        if job['status'] != 'running':
            break
        time.sleep(.05)
    assert job['status'] == 'complete' and job['result']['ok']
    status, released = _post(server, json.dumps({'job_id': key}).encode(), path='/api/geometry-jobs/cancel')
    assert status == 200 and released['status'] == 'released'


def test_geometry_capacity_is_explicitly_retryable(server, monkeypatch):  # noqa: F811 - pytest fixture injection
    from orthoplan.geometry_jobs import GeometryBusy
    def busy(*args, **kwargs):
        raise GeometryBusy('Geometry workers are busy. Retry shortly.')
    monkeypatch.setattr('orthoplan.server.jobs.start', busy)
    status, result = _post(server, b'{"operation":"evaluate","payload":{}}', path='/api/geometry-jobs')
    assert status == 200 and result['retryable'] and not result['ok']
