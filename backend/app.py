from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from bson import ObjectId
import json
import loguru

app = Flask(__name__)

logger = loguru.logger
# Load json schema for db
with open('schema.json', 'r') as file:
    schema = file.read()
schema = json.loads(schema)

# Connect to MongoDB
client = MongoClient("mongodb://mongodb:27017/")
db = client["nanoparticles_database"]
collection_name = "nanoparticles"


if collection_name not in db.list_collection_names():
    db.command("create", collection_name, validator=schema)
else:
    db.command("collMod", collection_name, validator=schema, validationLevel="strict", validationAction="error")

collection = db[collection_name]


def is_duplicate(data):
        existing_item = collection.find_one(data)
        return existing_item is not None


@app.route("/health", methods=["GET"])
def healthcheck():
    return jsonify({"message":"ok"})


@app.route("/api/np/add", methods=["POST"])
def add_nanoparticles():
    try:
        data = request.get_json()
        results = []
        logger.info(data)
        # Check if data is a list of dictionaries or a single dictionary
        if isinstance(data, list):
            for np in data:
                if is_duplicate(np):
                    results.append({"np #": data.index(np)+1, "message": "Duplicate nanoparticle, not added"})
                    continue
                collection.insert_one(np)
                results.append({"np #": data.index(np)+1, "message": "Nanoparticle added successfully"})
        elif isinstance(data, dict):
            if is_duplicate(data):
                return jsonify({"message": "Duplicate nanoparticle, not added"}), 409
            else:
                collection.insert_one(data)
                return jsonify({"message": "Nanoparticle added successfully"}), 201
        return jsonify({"results": results}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Update a nanoparticle
@app.route("/api/np/update/<id>", methods=["PUT"])
def update_nanoparticle(id):
    data = request.get_json()
    if is_duplicate(data):
        return jsonify({"message": "Duplicate nanoparticle, not updated"}), 409
    if collection.count_documents({"_id": ObjectId(id)}) == 0:
        return jsonify({'message': 'Nanoparticle id not found'}), 404
    collection.update_one({"_id": ObjectId(id)}, {"$set": data})
    return jsonify({"message": "Nanoparticle updated successfully"}), 200


# Get all nanoparticles
@app.route("/api/np/get", methods=["GET"])
def get_nanoparticles():
    nanoparticles = list(collection.find())
    if not nanoparticles:
        return jsonify({"message": "Database is empty"}), 404
    for nanoparticle in nanoparticles:
        nanoparticle["_id"] = str(nanoparticle["_id"])
    return jsonify(nanoparticles)


# Get a nanoparticle by ID
@app.route("/api/np/get/<id>", methods=["GET"])
def get_nanoparticle(id):
    nanoparticle = collection.find_one({"_id": ObjectId(id)})
    if nanoparticle:
        nanoparticle["_id"] = str(nanoparticle["_id"])
        return jsonify(nanoparticle)
    else:
        return jsonify({"message": "Nanoparticle not found"}), 404


# Delete a nanoparticle by ID
@app.route('/np/delete/<id>', methods=['DELETE'])
def delete_nanoparticle(id):
    result = collection.delete_one({"_id": ObjectId(id)})
    if result.deleted_count == 1:
        return jsonify({"message": f"Nanoparticle with ID {id} deleted successfully"}), 200
    else:
        return jsonify({"message": f"Nanoparticle with ID {id} not found"}), 404


###########################
##  WEB PAGES
###########################

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        logger.info(f"Given data: {name} {email} {message}")
        return f"Form submitted successfully {name} {email} {message}!"
    return render_template("index.html")


@app.route('/database', methods=['GET'])
def get_database_page():
    nanoparticles = list(collection.find())
    all_data = []
    for item in nanoparticles:
        for corona in item['coronas']:
            for protein in corona['proteins']:
                all_data.append({
                    'nanoparticle_type': item['type'],
                    'mean_hydrodynamic_diameter': item.get('mean_hydrodynamic_diameter'),
                    'zeta_potential': item.get('zeta_potential'),
                    'pdi': item.get('pdi'),
                    'article_doi': item['article']['article_doi'],
                    'article_title': item['article']['title'],
                    'protein_identification_method': item['protein_identification_method'],
                    'corona_mean_hydrodynamic_diameter': corona.get('mean_hydrodynamic_diameter'),
                    'corona_zeta_potential': corona.get('zeta_potential'),
                    'corona_pdi': corona.get('pdi'),
                    'exposure_time': corona['exposure_time'],
                    'experiment_type': corona['experiment_type'],
                    'protein_name': protein['name'],
                    'rpa': protein['rpa'],
                    'np_id': item["_id"]
                })
    return render_template("database.html", table=all_data)



@app.route('/coronas', methods=['GET'])
def get_np_corona_page():
    nanoparticles = list(collection.find())
    nanoparticles_corona_data = []
    for item in nanoparticles:
        for corona in item['coronas']:
            nanoparticles_corona_data.append({
                'nanoparticle_type': item['type'],
                'mean_hydrodynamic_diameter': corona.get('mean_hydrodynamic_diameter'),
                'protein_identification_method': item['protein_identification_method'],
                'zeta_potential': corona.get('zeta_potential'),
                'pdi': corona.get('pdi'),
                'exposure_time': corona['exposure_time'],
                'experiment_type': corona['experiment_type'],
                'proteins': [protein['name'] for protein in corona['proteins']],
                'np_id': item["_id"]
            })
    return render_template("coronas.html", table=nanoparticles_corona_data)


# @app.route("/proteins", methods=["GET"])
# def get_proteins_page():
#     nanoparticles = list(collection.find())
#     proteins_data = []
#     for item in nanoparticles:
#         for corona in item['coronas']:
#             for protein in corona['proteins']:
#                 proteins_data.append({
#                     'nanoparticle_type': item['type'],
#                     'exposure_time': corona['exposure_time'],
#                     'experiment_type': corona['experiment_type'],
#                     'protein_name': protein['name'],
#                     'rpa': protein['rpa'],
#                     'np_id': item["_id"],
#                     'doi': item['article']['article_doi']
#                 })
#     return render_template("proteins.html", proteins=proteins_data)


@app.route('/nanoparticles', methods=['GET'])
def get_nanoparticles_page():
    nanoparticles = list(collection.find())
    nanoparticles_info = []
    for item in nanoparticles:
        nanoparticles_info.append({
            'nanoparticle_type': item['type'],
            'mean_hydrodynamic_diameter': item['mean_hydrodynamic_diameter'],
            'zeta_potential': item['zeta_potential'],
            'pdi': item['pdi'],
            'protein_identification_method': item['protein_identification_method'],
            'number_of_identified_coronas': len(item['coronas']),
            'doi': item['article']['article_doi'],
            'np_id': item["_id"]
        })
    return render_template("nanoparticles.html", table=nanoparticles_info)


@app.route('/nanoparticle/<id>', methods=['GET'])
def get_nanoparticle_page(id):
    nanoparticle = collection.find_one({"_id": ObjectId(id)})
    if nanoparticle:
        return render_template("nanoparticle.html", nanoparticle=nanoparticle)
    else:
        return "Nanoparticle not found", 404


@app.route("/add_nanoparticle", methods=["GET"])
def get_np_adding_page():
    return render_template("add_nanoparticle.html")


@app.route("/api_documentation", methods=["GET"])
def get_api_doc_page():
    return render_template("api_documentation.html", domain="http://domain.com")


@app.route("/schema", methods=["GET"])
def get_db_schema_page():
    return render_template("schema.html", domain="http://localhost")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
