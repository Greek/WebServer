# Skeleton program
from datetime import datetime
import pathlib
import signal
import socket
import sys
from urllib.parse import urlsplit

from status_codes import status_codes, make_response_status_line

HOST = None  # Symbolic name meaning all available interfaces
PORT = 50000  # Arbitrary non-privileged port


def get_socket() -> socket.socket:
    """Create a socket and begin listening."""
    s = None

    for res in socket.getaddrinfo(
        HOST, PORT, socket.AF_INET, socket.SOCK_STREAM, 0, socket.AI_PASSIVE
    ):
        af, socktype, proto, _canonname, sa = res
        try:
            s = socket.socket(af, socktype, proto)
        except OSError as msg:
            s = None
            continue
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(sa)
            s.listen(1)
            print("Server is running. Waiting for connection...")
        except OSError as msg:
            s.close()
            s = None
            continue
        break
    if s is None:
        print("could not open socket")
        sys.exit(1)

    return s


def get_request_headers(raw: str) -> dict[str, str]:
    """Returns a dictionary of request headers."""
    headers = {}
    lines = raw.splitlines()

    headers["RequestSegmentHeader"] = lines[0]
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip()] = value.strip()

    return headers


def get_request_body(raw: str) -> list[str]:
    """Returns the entire body after the carriage return."""
    return raw.split("\r\n")[-2:][1]


def get_request_method(headers: dict[str, str]) -> str:
    """Get an HTTP request's method by parsing its headers."""
    request_line = headers.get("RequestSegmentHeader", "")
    if not request_line:
        return ""
    return request_line.split(" ", 1)[0]


def make_response_headers(headers: list[str]) -> str:
    """
    Make HTTP-complaint response headers with proper carriage return,
    from a list of header strings.
    """

    res = ""
    for _, v in enumerate(headers):
        res += f"{v}\r\n"

    return res


def get_file_contents(path: str) -> tuple[str | None, datetime | None]:
    """Return a file's contents and last modified date from the public directory."""

    if not path:
        return None, None

    normalized_path = urlsplit(path).path
    if not normalized_path or normalized_path == "/":
        normalized_path = "index.html"

    normalized_path = normalized_path.lstrip("/")
    if normalized_path.startswith("public/"):
        normalized_path = normalized_path.removeprefix("public/")
    if normalized_path == ".":
        normalized_path = "index.html"
    if normalized_path.endswith("/"):
        normalized_path = normalized_path.rstrip("/")
        if not normalized_path:
            normalized_path = "index.html"
        else:
            normalized_path += "/index.html"

    public_root = pathlib.Path("public").resolve()
    candidate = (public_root / normalized_path).resolve(strict=False)

    try:
        candidate.relative_to(public_root)
    except ValueError:
        return None, None

    if candidate.is_dir():
        candidate = candidate / "index.html"

    try:
        with candidate.open("r", encoding="utf-8") as file:
            file_contents = file.read()
        file_modified_date = datetime.fromtimestamp(candidate.stat().st_mtime)
        return file_contents, file_modified_date
    except (FileNotFoundError, PermissionError, IsADirectoryError, OSError):
        return None, None


HTTP_BUFFER_SIZE = pow(10, 9)  # 1 gb
HTTP_DATE_FMT = "%a, %d %b %Y %H:%M:%S GMT"


def main():
    """Run the HTTP server by exposing a socket and handling connections."""
    s = get_socket()
    while s.fileno() != -1:
        conn, addr = s.accept()

        with conn:
            print("Connected by", addr)
            while conn.fileno() != -1:
                http_request = conn.recv(HTTP_BUFFER_SIZE).decode(
                    "utf-8", errors="ignore"
                )
                if not http_request:
                    break

                print()
                print("===== Raw HTTP Request =====")
                headers = get_request_headers(http_request)
                body = get_request_body(http_request)
                req_method = get_request_method(headers)
                req_target_path = headers.get("RequestSegmentHeader", "").split(" ")[1]

                print(f"Method and Path: {headers.get('RequestSegmentHeader')}")
                print(f"\nHeaders: {headers}")
                print(f"\nBody: {body if len(body) > 0 else 'No body detected.'}")

                print()
                print("===== Response Segment =====")
                response_segment = ""
                requested_modified_date = None
                send_empty_body = False
                response_body = ""
                file_contents, file_last_modified = get_file_contents(req_target_path)

                if req_method not in ["POST", "GET", "HEAD"]:
                    send_empty_body = True
                    response_segment += make_response_status_line(405)
                elif req_method == "HEAD":
                    response_segment += make_response_status_line(200)
                    response_body = ""
                elif file_contents is None:
                    not_found_contents, _ = get_file_contents("not_found.html")
                    response_body = not_found_contents or ""
                    response_segment += make_response_status_line(404)
                else:
                    requested_modified_date = (
                        datetime.strptime(
                            headers.get("If-Modified-Since"), HTTP_DATE_FMT
                        )
                        if headers.get("If-Modified-Since") is not None
                        else None
                    )
                    if (
                        requested_modified_date is not None
                        and requested_modified_date < file_last_modified
                    ):
                        response_segment += make_response_status_line(304)
                        send_empty_body = True
                    else:
                        response_segment += make_response_status_line(200)

                    if send_empty_body:
                        response_body = ""
                    else:
                        response_body = file_contents

                response_body_length = len(response_body)
                last_modified_header = (
                    f"Last-Modified: {file_last_modified.strftime(HTTP_DATE_FMT)}"
                    if file_last_modified is not None and req_method != "HEAD"
                    else "Last-Modified: "
                )
                response_headers = [
                    "Server: Extremely Reliable COSC 350 Server For Real Production Needs",
                    f"Date: {datetime.now().strftime(HTTP_DATE_FMT)}",
                    last_modified_header,
                    f"Content-Length: {response_body_length}",
                ]

                response_segment += make_response_headers(response_headers)
                payload = f"HTTP/1.1 {response_segment}\r\n{response_body}".encode(
                    "utf-8"
                )

                print(f"Headers: {response_headers}")
                print(
                    f"\nBody: {response_body if len(response_body) > 0 else 'No response body sent.'}"
                )
                print(f"\nFull Segment:\n{payload.rstrip()}")
                conn.send(payload)


def sigint_handler():
    sys.exit(1)


if __name__ == "__main__":
    main()
    signal.signal(signal.SIGINT, sigint_handler())
