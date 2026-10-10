# Very Compliant Web Server

Very Compliant Web Server is a project web-server that handles limited web server cases.
It was built in Python using the socket standard library, no HTTP helpers/libraries were
used.

## Features

- GET
- HEAD
- Conditional GET (Modified-Since, If-Modified-Since)
- Directory traversal protection for files served from `public/`
