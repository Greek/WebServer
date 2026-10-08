# Skeleton program
import signal
import socket
import sys

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


def get_request_headers(raw: str) -> list[str]:
    """Returns a list of headers before the last carriage return."""
    return raw.split("\r\n")[:-2]


def get_request_body(raw: str) -> list[str]:
    """Returns the entire body after the carriage return."""
    return raw.split("\r\n")[-2:][1]


def get_request_method(headers: list[str]) -> str:
    """Get an HTTP request's method by parsing its headers."""
    return headers[0].split(" ")[0].strip().upper()


def make_response_headers(headers: list[str]) -> str:
    """
    Make HTTP-complaint response headers with proper carriage return,
    from a list of header strings.
    """

    res = ""
    for _, v in enumerate(headers):
        res += f"{v}\r\n"

    return res


def get_file_contents(path: str) -> str:
    """Get a file and its contents without handling error."""

    file_contents = None
    if path == "/":
        path = "index.html"

    try:
        with open(f"public/{path}", "r", encoding="utf-8") as file:
            file_contents = file.read()
    except (FileNotFoundError, PermissionError):
        pass

    return file_contents


HTTP_BUFFER_SIZE = pow(10, 9)  # 1 gb


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
                req_target_path = headers[0].split(" ")[1]

                print(f"Method and Headers: {headers[0]}")
                print(
                    f"\nHeaders: {headers[1:] if len(headers) > 1 else "No headers detected."}"
                )
                print(
                    f"\nBody: {f"\n{body}" if len(body) > 0 else "No body detected."}"
                )

                print()
                print("===== Response Segment =====")
                response_segment = ""
                file_contents = get_file_contents(req_target_path)

                if req_method not in ["POST", "GET"]:
                    response_body = ""
                    response_segment += make_response_status_line(405)
                elif file_contents is None:
                    response_body = get_file_contents("not_found.html")
                    response_segment += make_response_status_line(404)
                else:
                    response_body = file_contents
                    response_segment += make_response_status_line(200)

                response_body_length = len(response_body)
                response_headers = [
                    "Server: custom_server",
                    f"Content-Length: {response_body_length}",
                ]
                response_segment += make_response_headers(response_headers)
                payload = f"HTTP/1.1 {response_segment}\r\n{response_body}".encode(
                    "utf-8"
                )

                print(f"Headers: {response_headers}")
                print(
                    f"\nBody: {f"\n{response_body}" if len(response_body) > 0 else "No response body sent."}"
                )
                print(f"\nFull Segment:\n{payload.rstrip()}")
                conn.send(payload)


def sigint_handler():
    sys.exit(1)


if __name__ == "__main__":
    main()
    signal.signal(signal.SIGINT, sigint_handler())
