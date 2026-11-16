from rest_framework import authentication


class SessionAuthentication(authentication.SessionAuthentication):
    """Session authentication that answers 401 to anonymous requests.

    Stock DRF answers 403 both to "not signed in" and to "not allowed", because
    its session class sends no WWW-Authenticate header. The frontend needs to
    tell the two apart: 401 means "sign in again", 403 means "forbidden".
    """

    def authenticate_header(self, request):
        return "Session"
