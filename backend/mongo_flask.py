from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from bson import ObjectId
import json
import pandas as pd
import loguru 
app = Flask(__name__)

logger = loguru.logger
# Load json schema for db
with open('schema.json', 'r') as file:
    schema = file.read()
schema = json.loads(schema)

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["nanoparticles_database"]
collection_name = "nanoparticles"

if collection_name not in db.list_collection_names():
    # Create the collection with the schema validation
    db.command("create", collection_name, validator=schema)
else:
    # Update the existing collection with the schema validation
    db.command("collMod", collection_name, validator=schema, validationLevel="strict", validationAction="error")

collection = db[collection_name]

def is_duplicate(data):
    search_criteria = {
        "type": data["type"],
    }
    if "mean_hydrodynamic_diameter" in data:
        search_criteria["mean_hydrodynamic_diameter"] = data["mean_hydrodynamic_diameter"]
    if "zeta_potential" in data:
        search_criteria["zeta_potential"] = data["zeta_potential"]
    if "pdi" in data:
        search_criteria["pdi"] = data["pdi"]

    for corona in data["coronas"]:
        corona_criteria = {}
        
        if "mean_hydrodynamic_diameter" in corona:
            corona_criteria["coronas.mean_hydrodynamic_diameter"] = corona["mean_hydrodynamic_diameter"]
        if "zeta_potential" in corona:
            corona_criteria["coronas.zeta_potential"] = corona["zeta_potential"]
        if "pdi" in corona:
            corona_criteria["coronas.pdi"] = corona["pdi"]

        search_criteria.update(corona_criteria)
        existing_item = collection.find_one(search_criteria)
        if existing_item is not None:
            return True

@app.route("/health", methods=["GET"])
def healthcheck():
    return jsonify({"message":"ok"})

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        logger.info(f"Given data: {name} {email} {message}")
        # Add code here to process the form data and store it in a database, send an email, etc.
        return f"Form submitted successfully {name} {email} {message}!"
    return render_template("index.html")

@app.route("/protein", methods=["GET"])
def get_proteins():
    nanoparticles = list(collection.find())
    proteins_data = []
    for item in nanoparticles:
        for corona in item['coronas']:
            for protein in corona['proteins']:
                proteins_data.append({
                    'nanoparticle_type': item['type'],
                    'exposure_time': corona['exposure_time'],
                    'experiment_type': corona['experiment_type'],
                    'protein_name': protein['name'],
                    'rpa': protein['rpa'],
                    'np_id': item["_id"]
                })
    return render_template("proteins.html", proteins=proteins_data)

@app.route("/np/add", methods=["POST"])
def add_nanoparticles():
    data = request.get_json()
    results = []
    
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
    else:
        # Invalid input
        return jsonify({"error": "Invalid input"}), 400

    return jsonify({"results": results}), 201

# Update a nanoparticle
@app.route("/np/update/<id>", methods=["PUT"])
def update_nanoparticle(id):
    data = request.get_json()
    if is_duplicate(data):
        return jsonify({"message": "Duplicate nanoparticle, not updated"}), 409
    if collection.count_documents({"_id": ObjectId(id)}) == 0:
        return jsonify({'message': 'Nanoparticle id not found'}), 404
    collection.update_one({"_id": ObjectId(id)}, {"$set": data})
    return jsonify({"message": "Nanoparticle updated successfully"}), 200

# Get all nanoparticles
@app.route("/np/get", methods=["GET"])
def get_nanoparticles():
    nanoparticles = list(collection.find())
    if not nanoparticles:
        return jsonify({"message": "Database is empty"}), 404
    for nanoparticle in nanoparticles:
        nanoparticle["_id"] = str(nanoparticle["_id"])
    return jsonify(nanoparticles)

# Get a nanoparticle by ID
@app.route("/np/get/<id>", methods=["GET"])
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

# Get data for a 'nanoparticles' table
@app.route('/np/export/nanoparticles', methods=['GET'])
def export_nanoparticles():
    nanoparticles = list(collection.find())
    nanoparticles_data = []
    for item in nanoparticles:
        nanoparticles_data.append({
            'nanoparticle_type': item['type'],
            'mean_hydrodynamic_diameter': item.get('mean_hydrodynamic_diameter'),
            'zeta_potential': item.get('zeta_potential'),
            'pdi': item.get('pdi'),
            'article_doi': item['article']['article_doi'],
            'article_title': item['article']['title']
        })
    return jsonify(nanoparticles_data)

# Get data for the 'corona' table
@app.route('/np/export/coronas', methods=['GET'])
def export_nanoparticles_corona():
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
                'proteins': [protein['name'] for protein in corona['proteins']]
            })
    return jsonify(nanoparticles_corona_data)

# Endpoint to get data for the 'Proteins' table
@app.route('/export/proteins', methods=['GET'])
def export_proteins():
    nanoparticles = list(collection.find())
    proteins_data = []
    for item in nanoparticles:
        for corona in item['coronas']:
            for protein in corona['proteins']:
                proteins_data.append({
                    'nanoparticle_type': item['type'],
                    'exposure_time': corona['exposure_time'],
                    'experiment_type': corona['experiment_type'],
                    'protein_name': protein['name'],
                    'rpa': protein['rpa']
                })
    return jsonify(proteins_data)

# get all data as table
@app.route('/full_table', methods=['GET'])
def export_all():
    nanoparticles = list(collection.find())
    proteins_data = []
    for item in nanoparticles:
        for corona in item['coronas']:
            for protein in corona['proteins']:
                proteins_data.append({
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
                    'rpa': protein['rpa']
                })
    return jsonify(proteins_data)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
