"""Guard the actual Streamlit middleware/Starlette response-order contract."""
import asyncio

import pytest
from streamlit.web.server.starlette.starlette_gzip_middleware import MediaAwareGZipMiddleware


@pytest.mark.parametrize('encoding', ['identity', 'gzip'])
@pytest.mark.parametrize('preencoded', [False, True])
def test_image_response_headers_precede_body(encoding, preencoded):
    messages = []

    async def image(scope, receive, send):
        headers = [(b'content-type', b'image/png')]
        if preencoded:
            headers.append((b'content-encoding', b'identity'))
        await send({'type': 'http.response.start', 'status': 200, 'headers': headers})
        await send({'type': 'http.response.body', 'body': b'test image bytes'})

    async def receive():
        return {'type': 'http.request', 'body': b'', 'more_body': False}

    async def send(message):
        messages.append(message)

    async def exercise():
        scope = {'type': 'http', 'method': 'GET', 'path': '/favicon.png', 'headers': [(b'accept-encoding', encoding.encode())]}
        await MediaAwareGZipMiddleware(image)(scope, receive, send)

    asyncio.run(exercise())
    assert [item['type'] for item in messages] == ['http.response.start', 'http.response.body']
    assert messages[0]['status'] == 200
