# Skeleton program
import signal
import socket
import sys

from status_codes import status_codes

HOST = None               # Symbolic name meaning all available interfaces
PORT = 50000              # Arbitrary non-privileged port

def get_socket() -> socket.socket: 
    s = None

    for res in socket.getaddrinfo(HOST, PORT, socket.AF_INET,
                                socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
        af, socktype, proto, canonname, sa = res
        try:
            s = socket.socket(af, socktype, proto)
        except OSError as msg:
            s = None
            continue
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(sa)
            s.listen(1)
            print('Server is running. Waiting for connection...')
        except OSError as msg:
            s.close()
            s = None
            continue
        break
    if s is None:
        print('could not open socket')
        sys.exit(1)

    return s

def get_request_headers(raw: str) -> list[str]:
    """ Returns a list of headers before the last carriage return. """
    return raw.split("\r\n")[:-2]

def get_request_body(raw: str) -> list[str]:
    """ Returns the entire body after the carriage return. """
    return raw.split("\r\n")[-2:][1]

def get_request_method(headers: list[str]) -> str:
    return headers[0].split(" ")[0].strip().upper()

def make_response_status_line(code: int):
    if status_codes[code] is None:
        return f"418 {status_codes.get(418)}\r\n"

    return f"{code} {status_codes.get(code)}\r\n"

def make_response_headers(headers: list[str]) -> str:
    res = ""
    for _,v in enumerate(headers):
        res += f"{v}\r\n"

    return res



HTTP_BUFFER_SIZE = pow(10,9) # 1 gb

def main():
    s = get_socket()
    while s.fileno() != -1:
        conn, addr = s.accept()

        with conn:
            print('Connected by', addr)
            while conn.fileno() != -1:
                http_request = conn.recv(HTTP_BUFFER_SIZE).decode('utf-8', errors='ignore')
                if not http_request: break

                print("===== Raw HTTP Request =====")               
                headers = get_request_headers(http_request)
                body = get_request_body(http_request)
                req_method = get_request_method(headers)
                response_segment = ""

                print(headers)
                print(body)
                
                if req_method not in ["POST", "GET"]:
                    response_segment += make_response_status_line(405)
                    response_body = ""
                else:
                    response_segment += make_response_status_line(200)
                    response_body = "Insert thy response here..."
                    
                response_body_length = len(response_body.encode("utf-8"))
                response_segment += make_response_headers(["Server: custom_server", f"Content-Length: {response_body_length}"])

                conn.send(
                    f"HTTP/1.1 {response_segment}\r\n{response_body}".encode('utf-8')
                )

def sigint_handler():
    sys.exit(1)


if __name__ == "__main__":
    main()
    signal.signal(signal.SIGINT, sigint_handler())