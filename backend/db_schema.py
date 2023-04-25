import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Float
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import database_exists, create_database
from marshmallow import Schema, fields
# Load environment variables from .env file
load_dotenv()

# Get environment variables
db_user = os.getenv("MYSQLDB_USER")
db_password = os.getenv("MYSQLDB_PASSWORD")
db_hostname = os.getenv("MYSQLDB_HOSTNAME")
db_name = os.getenv("MYSQLDB_DATABASE")

# Construct the connection URL
DB_URI = 'mysql+pymysql://{db_username}:{db_password}@{db_host}/{database}'\
    .format(db_username=db_user, 
            db_password=db_password,
            db_host=db_hostname, 
            database=db_name)

engine = create_engine(DB_URI, echo=True)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Tables
class Article(db.Model):
    __tablename__ = 'articles'
    doi = Column(String(32), primary_key=True)
    title = Column(String(255), nullable=False)

class Experiment(db.Model):
    __tablename__ = 'experiments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)

class Nanoparticle(db.Model):
    __tablename__ = 'nanoparticles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(255), nullable=False)
    mean_hydrodynamic_diameter = Column(Float(precision=2), nullable=False)
    zeta_potential = Column(Float(precision=2))
    pdi = Column(Float(precision=2))
    biological_effect = Column(String(255))
    experiment_type = Column(String(255))
    article_doi = Column(String(32), ForeignKey('articles.doi'), nullable=False)

class Protein(db.Model):
    __tablename__ = 'proteins'
    id = Column(Integer, primary_key=True, autoincrement=True)
    protein = Column(String(255), nullable=False)
    identification_method_id = Column(Integer, ForeignKey('experiments.id'))

class Content(db.Model):
    __tablename__ = 'content'
    id = Column(Integer, primary_key=True, autoincrement=True)
    protein_id = Column(Integer, ForeignKey('proteins.id'), nullable=False)
    rpa = Column(String(255))
    nanoparticle_id = Column(Integer, ForeignKey('nanoparticles.id'), nullable=False)


# Marshmallow schema
class ArticleSchema(Schema):
    doi = fields.String()
    title = fields.String()

class ExperimentSchema(Schema):
    id = fields.Integer()
    name = fields.String()

class NanoparticleSchema(Schema):
    id = fields.Integer()
    type = fields.String()
    mean_hydrodynamic_diameter = fields.Float()
    zeta_potential = fields.Float()
    pdi = fields.Float()
    biological_effect = fields.String()
    experiment_type = fields.String()
    article_doi = fields.String()

class ProteinSchema(Schema):
    id = fields.Integer()
    protein = fields.String()
    identification_method_id = fields.Integer()

class ContentSchema(Schema):
    id = fields.Integer()
    protein_id = fields.Integer()
    rpa = fields.String()
    nanoparticle_id = fields.Integer()

