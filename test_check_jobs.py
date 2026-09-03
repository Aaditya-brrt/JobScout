"""Minimal self-check: python test_check_jobs.py (no framework, no network)."""
import json, os, importlib.util
from unittest import mock

os.environ.setdefault("RUNWAY_COOKIE", "x")
os.environ.setdefault("GMAIL_ADDRESS", "a@b.com")
os.environ.setdefault("GMAIL_APP_PASSWORD", "x")
os.environ.setdefault("TO_EMAIL", "a@b.com,c@d.com")

spec = importlib.util.spec_from_file_location("cj", "check_jobs.py")
cj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cj)


def _resp(jobs):
    body = json.dumps([{"result": {"data": {"json": {"jobs": jobs}}}}]).encode()
    fake = mock.MagicMock()
    fake.__enter__.return_value.read.return_value = body
    return fake


def test_expired_cookie_raises():
    with mock.patch("urllib.request.urlopen", return_value=_resp([{"id": "1", "matchScore": 0}])):
        try:
            cj.fetch_jobs()
        except RuntimeError as e:
            assert "expired" in str(e)
        else:
            raise AssertionError("expired cookie went undetected")


def test_scored_jobs_pass():
    with mock.patch("urllib.request.urlopen", return_value=_resp([{"id": "1", "matchScore": 91}])):
        assert cj.fetch_jobs() == [{"id": "1", "matchScore": 91}]


def test_refused_recipient_raises():
    smtp = mock.MagicMock()
    smtp.__enter__.return_value.send_message.return_value = {"c@d.com": (550, b"nope")}
    with mock.patch("smtplib.SMTP_SSL", return_value=smtp):
        try:
            cj.send_email([{"id": "1", "title": "T", "company": "C", "matchScore": 91}])
        except RuntimeError as e:
            assert "refused" in str(e)
        else:
            raise AssertionError("refused recipient went unnoticed")


if __name__ == "__main__":
    test_expired_cookie_raises()
    test_scored_jobs_pass()
    test_refused_recipient_raises()
    print("ok")
