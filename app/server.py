from flask import Flask
from flask_restful import Api
from app.resources import MagicCastle

app = Flask(__name__)
api = Api(app, prefix='/api')

api.add_resource(MagicCastle, '/magic-castle')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
