"""Application entry point for local Flask use and Vercel deployment."""

import os

from app import create_app

app = create_app()


if __name__ == '__main__':
    app.run(
        debug=os.environ.get('FLASK_DEBUG') == '1',
        host=os.environ.get('HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', '8080')),
    )
