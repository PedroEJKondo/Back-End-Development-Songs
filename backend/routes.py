from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys
from flask import Response

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "ok", "message": "Service is healthy"}, 200

@app.route("/count", methods=["GET"])
def count():
    count_val = db.songs.count_documents({})
    return {"count": count_val}, 200

@app.route("/song", methods=["GET"])
def get_songs():
    songs_list = list(db.songs.find({}))
    for song in songs_list:
        song["_id"] = str(song["_id"])  # Convert MongoDB ObjectId to string
    return {"songs": songs_list}, 200

@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    song = db.songs.find_one({"id": id})

    if not song:
        return {"message": "música com id não encontrada"}, 404

    # Converte o documento BSON/MongoDB (incluindo o _id) para JSON válido
    return Response(json_util.dumps(song), status=200, mimetype="application/json")

    from flask import request


@app.route("/song", methods=["POST"])
def create_song():
    song_data = request.get_json()

    # 1. Valida se o corpo da requisição é um JSON válido
    if not song_data:
        return {"Message": "Dados inválidos ou corpo da requisição vazio"}, 400

    # 2. Valida se o campo 'id' está presente
    song_id = song_data.get("id")
    if song_id is None:
        return {"Message": "O campo 'id' é obrigatório"}, 400

    # 3. Verifica se a música já existe
    existing_song = db.songs.find_one({"id": song_id})
    if existing_song:
        return {"Message": f"música com id {song_id} já presente"}, 302

    # 4. Insere no banco e remove o _id do MongoDB para retorno seguro
    db.songs.insert_one(song_data)
    song_data.pop("_id", None)

    return song_data, 201

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    # Extrai os dados do corpo da requisição em formato JSON
    song_data = request.get_json()

    # Procura a música no banco de dados pelo id
    song = db.songs.find_one({"id": id})

    if not song:
        return {"message": "música não encontrada"}, 404

    # Atualiza os dados da música no banco de dados
    db.songs.update_one({"id": id}, {"$set": song_data})

    # Retorna a mensagem de sucesso e os dados atualizados com o status 200 OK
    return {"message": "música atualizada com sucesso", "song": song_data}, 200

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    # Executa a exclusão da música no banco de dados pelo 'id'
    result = db.songs.delete_one({"id": id})

    # Se nenhum documento foi deletado, a música não existia
    if result.deleted_count == 0:
        return {"message": "música não encontrada"}, 404

    # Se deleted_count for 1, retorna corpo vazio e status 204 (No Content)
    return "", 204