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
    mean_hydrodynamic_diameter = Column(Float(precision=2), nullable=False)
    zeta_potential = Column(Float(precision=2))
    pdi = Column(Float(precision=2))
    biological_effect = Column(String(64))
    experiment_type = Column(String(32))
    article_doi = Column(String(32), ForeignKey('articles.doi'), nullable=False)
    protein_identification_method_id = Column(Integer, ForeignKey('experiments.id'))

class Protein(BaseModel):
    __tablename__ = 'proteins'
    id = Column(Integer, primary_key=True, autoincrement=True)
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

class ProteinContentSchema(Schema):
    protein = fields.String()
    rpa = fields.String()

class NanoparticleInfoSchema(NanoparticleSchema):
    article_title = fields.String()
    protein_identification_method_name = fields.String()

# Create instahces of schemas
article_schema = ArticleSchema()
experiment_schema = ExperimentSchema()
nanoparticle_schema = NanoparticleSchema()
protein_schema = ProteinSchema()
content_schema = ContentSchema()
protein_content = ProteinContentSchema()
nanoparticle_info_schema = NanoparticleInfoSchema()


# Flask routes
# Articles
@app.route('/articles/add', methods=['POST'])
def create_article():
    new_article = Article(
        doi=request.json['doi'], 
        title=request.json['title'])
    new_article.save()
    article=article_schema.dump(new_article)
    return jsonify(article), 201

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

# main table
@app.route('/main/nanoparticles/get', methods=['GET'])
def get_protein_content(id):
    query = db.session.query(Nanoparticle.type.label('nanoparticle_type'),
                              Nanoparticle.mean_hydrodynamic_diameter,
                              Nanoparticle.zeta_potential,
                              Nanoparticle.pdi,
                              Nanoparticle.biological_effect,
                              Nanoparticle.experiment_type,
                              Article.title.label('article_title'),
                              Experiment.name.label('protein_identification_method_name'))\
                        .join(Article, Nanoparticle.article_doi == Article.doi)\
                        .join(Experiment, Nanoparticle.protein_identification_method_id == Experiment.id)\
                        .all()
    response = nanoparticle_info_schema.dump(query)
    return jsonify(response), 200





if __name__ == '__main__':
    if not database_exists(engine.url):
        create_database(engine.url)
    db.create_all()
    app.run(debug=True, host="0.0.0.0")