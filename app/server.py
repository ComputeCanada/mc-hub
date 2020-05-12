from flask import Flask
from flask_restful import Api
from resources.magic_castle import MagicCastle
from resources.magic_castle_status import MagicCastleStatus

magic_castle_status = 'idle'

app = Flask(__name__)
api = Api(app, prefix='/api')

api.add_resource(MagicCastle, '/magic-castle')
api.add_resource(MagicCastleStatus, '/magic-castle/<string:cluster_name>/status')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
