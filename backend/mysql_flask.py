import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Float
from sqlalchemy.exc import IntegrityError, DataError, OperationalError
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

class BaseModel(db.Model):
    __abstract__ = True

    def save(self):
        retries = 5
        while retries > 0:
            try:
                db.session.add(self)
                db.session.commit()
                break
            except IntegrityError:
                db.session.rollback()
                raise Exception("Could not save model instance: IntegrityError")
            except DataError:
                db.session.rollback()
                raise Exception("Could not save model instance: DataError")
            except OperationalError:
                db.session.rollback()
                retries -= 1
        else:
            raise Exception("Could not save model instance: OperationalError")

    def delete(self):
        retries = 5
        while retries > 0:
            try:
                db.session.delete(self)
                db.session.commit()
                break
            except OperationalError:
                db.session.rollback()
                retries -= 1
        else:
            raise Exception("Could not delete model instance: OperationalError")

# Tables
class Article(BaseModel):
    __tablename__ = 'articles'
    doi = Column(String(32), primary_key=True)
    title = Column(String(255), nullable=False)

    @classmethod
    def get_all(cls):
        return cls.query.all()

    @classmethod
    def get_by_doi(cls, doi):
        article = cls.query.get(doi)
        if article == None:
            return None
        else:
            return article

    @classmethod
    def remove_by_doi(cls, doi):
        article = cls.query.get(doi)
        if article == None:
            return None
        else:
            db.session.delete(article)
            db.session.commit()
            return article

class Experiment(BaseModel):
    __tablename__ = 'experiments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    
class Nanoparticle(BaseModel):
    __tablename__ = 'nanoparticles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(255), nullable=False)
    initial_mean_hydrodynamic_diameter = Column(Float(precision=2), nullable=False)
    mean_hydrodynamic_diameter = Column(Float(precision=2), nullable=False)
    initial_zeta_potential = Column(Float(precision=2), nullable=False)
    zeta_potential = Column(Float(precision=2), nullable=False)
    exposure_time = Column(Integer, nullable=False)
    initial_pdi = Column(Float(precision=3), nullable=False)
    pdi = Column(Float(precision=3), nullable=False)
    experiment_type = Column(String(31), nullable=False)
    article_doi = Column(String(63), ForeignKey('articles.doi'), nullable=False)
    protein_identification_method_id = Column(Integer, ForeignKey('experiments.id'))

class Protein(BaseModel):
    __tablename__ = 'proteins'
    protein_id = Column(String(15), primary_key=True, autoincrement=True)
    protein = Column(String(255), nullable=False)

class Content(BaseModel):
    __tablename__ = 'content'
    id = Column(Integer, primary_key=True, autoincrement=True)
    protein_id = Column(Integer, ForeignKey('proteins.id'), nullable=False)
    rpa = Column(String(255))
    nanoparticle_id = Column(Integer, ForeignKey('nanoparticles.id'), nullable=False)


# Marshmallow schemas
class ArticleSchema(Schema):
    doi = fields.String()
    title = fields.String()

class ExperimentSchema(Schema):
    id = fields.Integer()
    name = fields.String()

class ProteinDbSchema(Schema):
    protein_id = fields.Float()
    protein = fields.String()
    identification_method_id = fields.Integer()

class ProteinJSONSchema(Schema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)
    pdi = fields.Float(required=True)

class NanoparticleDbSchema(Schema):
    id = fields.Integer()
    type = fields.String()
    initial_mean_hydrodynamic_diameter = fields.Float()
    mean_hydrodynamic_diameter = fields.Float()
    initial_zeta_potential = fields.Float()
    zeta_potential = fields.Float()
    exposure_time = fields.Integer()
    initial_pdi = fields.Float()
    pdi = fields.Float()
    experiment_type = fields.String()
    article_doi = fields.String()

class NanoparticleJSONSchema(Schema):
    type = fields.String(required=True)
    initial_mean_hydrodynamic_diameter = fields.Float(required=True)
    mean_hydrodynamic_diameter = fields.Float(required=True)
    initial_zeta_potential = fields.Float()
    zeta_potential = fields.Float(required=True)
    initial_pdi = fields.Float(required=True)
    pdi = fields.Float(required=True)
    exposure_time = fields.Integer(required=True)
    experiment_type = fields.String(required=True)
    article = fields.Nested(ArticleSchema, required=True)
    protein_identification_method = fields.String(required=True)
    proteins = fields.List(fields.Nested(ProteinJSONSchema), required=True)
    
class ContentSchema(Schema):
    id = fields.Integer()
    protein_id = fields.Integer()
    rpa = fields.String()
    nanoparticle_id = fields.Integer()

class ProteinContentSchema(Schema):
    protein = fields.String()
    rpa = fields.String()

class NanoparticleInfoSchema(NanoparticleDbSchema):
    article_title = fields.String()
    protein_identification_method_name = fields.String()

# Create instahces of schemas
article_schema = ArticleSchema()
experiment_schema = ExperimentSchema()
nanoparticle_db_schema = NanoparticleDbSchema()
protein_schema = ProteinDbSchema()
content_schema = ContentSchema()
protein_content = ProteinContentSchema()
nanoparticle_info_schema = NanoparticleInfoSchema()


# Flask routes
# Articles
# @app.route('/articles/add', methods=['POST'])
# def create_article():
#     new_article = Article(
#         doi=request.json['doi'], 
#         title=request.json['title'])
#     new_article.save()
#     article=article_schema.dump(new_article)
#     return jsonify(article), 201

def add_article(article_data):
    article = Article.get_by_doi(article_data['article_doi'])
    if article is None:
        article = Article(doi=article_data['article_doi'], title=article_data['title'])
        article.save()
    return article

# Get protein content by nanoparticle
@app.route('main/proteins/get/<int:id>', methods=['GET'])
def get_protein_content(id):
    query = db.session.query(Protein.protein, Content.rpa)\
                            .join(Content)\
                            .join(Nanoparticle)\
                            .filter(Nanoparticle.id == id)\
                            .all()
    response = protein_content.dump(query)
    return jsonify(response), 200

# Nanoparticles
def add_nanoparticle(data, article, experiment):
    nanoparticle = Nanoparticle(
        type=data['type'],
        initial_mean_hydrodynamic_diameter=data['initial_mean_hydrodynamic_diameter'],
        mean_hydrodynamic_diameter=data['mean_hydrodynamic_diameter'],
        initial_zeta_potential=data["initial_zeta_potential"],
        zeta_potential=data['zeta_potential'],
        initial_pdi=data['initial_pdi'],
        pdi=data['pdi'],
        exposure_time=data['exposure_time'],
        experiment_type=data['experiment_type'],
        article_doi=article.doi,
        protein_identification_method_id=experiment.id
    )
    nanoparticle.save()
    return nanoparticle

# Experiments
def add_experiment(protein_identification_method):
    experiment = Experiment.query.filter_by(name=protein_identification_method).first()
    if experiment is None:
        experiment = Experiment(name=protein_identification_method)
        experiment.save()
    return experiment

# Proteins + content
def add_protein_and_content(protein_data, nanoparticle):
    protein = Protein.query.get(protein_data['id'])
    if protein is None:
        protein = Protein(protein_id=protein_data['id'], protein=protein_data['name'])
        protein.save()

    content = Content(protein_id=protein.protein_id, rpa=protein_data['pdi'], nanoparticle_id=nanoparticle.id)
    content.save()

# main table
@app.route('/main/nanoparticles/get', methods=['GET'])
def get_protein_content(id):
    query = db.session.query(Nanoparticle.type.label('nanoparticle_type'),
                            Nanoparticle.initial_mean_hydrodynamic_diameter,
                            Nanoparticle.mean_hydrodynamic_diameter,
                            Nanoparticle.zeta_potential,
                            Nanoparticle.pdi,
                            Nanoparticle.exposure_time,
                            Nanoparticle.experiment_type,
                            Article.title.label('article_title'),
                            Experiment.name.label('protein_identification_method_name'))\
                        .join(Article, Nanoparticle.article_doi == Article.doi)\
                        .join(Experiment, Nanoparticle.protein_identification_method_id == Experiment.id)\
                        .all()
    response = nanoparticle_info_schema.dump(query)
    return jsonify(response), 200


@app.route('/main/nanoparticles/add', methods=['post'])
def add_all_info():
    data = request.json['nanoparticle']

    schema = NanoparticleJSONSchema()
    nanoparticle_data = schema.load(data)

    article = add_article(nanoparticle_data['article'])
    experiment = add_experiment(nanoparticle_data['protein_identification_method'])
    nanoparticle = add_nanoparticle(nanoparticle_data, article, experiment)

    for protein_data in nanoparticle_data['proteins']:
        add_protein_and_content(protein_data, nanoparticle)

    return jsonify({"message": "Data added successfully"}), 201


if __name__ == '__main__':
    if not database_exists(engine.url):
        create_database(engine.url)
    db.create_all()
    app.run(debug=True, host="0.0.0.0")