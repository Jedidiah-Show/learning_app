"""Shared HTTP response conventions and response-level hooks."""

import gzip

from flask import jsonify, request


def json_error(message, status=400, headers=None):
    """Return the application's standard JSON error envelope.

    ``jsonify`` output plus an explicit status keeps API errors consistent
    without making every route repeat the envelope shape.
    """
    response = jsonify({'error': message})
    response.status_code = status
    if headers:
        response.headers.extend(headers)
    return response


def register_response_hooks(app):
    """Install response compression (SSE is deliberately never compressed)."""

    @app.after_request
    def compress_response(response):
        if (
            response.is_streamed
            or response.status_code not in range(200, 300)
            or 'Content-Encoding' in response.headers
        ):
            return response
        content_type = response.headers.get('Content-Type', '')
        if content_type.startswith('text/event-stream'):
            return response
        if not any(
            text in content_type for text in (
                'text/', 'application/json', 'application/javascript', 'image/svg+xml'
            )
        ):
            return response
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if 'gzip' not in accept_encoding.lower():
            return response
        data = response.get_data()
        if len(data) < 500:
            return response
        compressed = gzip.compress(data, compresslevel=6)
        if len(compressed) < len(data):
            response.set_data(compressed)
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Length'] = str(len(compressed))
            response.headers['Vary'] = (
                f"{response.headers.get('Vary')}, Accept-Encoding"
                if response.headers.get('Vary') else 'Accept-Encoding'
            )
        return response
