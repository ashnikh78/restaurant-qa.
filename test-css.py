
from flask import Flask

app = Flask(__name__, static_folder='static')  # Point to the static folder

@app.route('/')
def index():
    return app.send_static_file('index.html')  # Serve index.html from static/

if __name__ == '__main__':
    app.run(debug=True)