from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    app.run(
        debug=os.environ.get('FLASK_DEBUG') == '1',
        host=os.environ.get('HOST', '127.0.0.1'),
        port=int(os.environ.get('PORT', '8080'))
    )
