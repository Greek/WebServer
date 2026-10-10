status_codes = {
    200: "OK",
    304: "Not Modified",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    418: "I'm a teapot",
    500: "Internal Server Error",
    501: "Not Implemented",
}

DEFAULT_STATUS_CODE = 500


def make_response_status_line(code: int):
    """
    Make HTTP status line for a given response code to use in the
    final segment response.
    """

    if status_codes[code] is None:
        return f"{DEFAULT_STATUS_CODE} {status_codes.get(DEFAULT_STATUS_CODE)}\r\n"

    return f"{code} {status_codes.get(code)}\r\n"
