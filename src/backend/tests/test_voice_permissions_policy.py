"""Test that Permissions-Policy allows microphone=(self)."""


def test_permissions_policy_allows_microphone():
    from security.security_headers import BASE_HEADERS
    pp = dict(BASE_HEADERS).get(b"permissions-policy", b"")
    assert b"microphone=(self)" in pp
    assert b"camera=()" in pp
    assert b"geolocation=()" in pp
