from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    cpf_cnpj = db.Column(db.String(20))

    ordens = db.relationship('OrdemServico', backref='cliente', cascade='all, delete-orphan')


class Produto(db.Model):
    __tablename__ = 'produtos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(200))
    preco = db.Column(db.Float, nullable=False)


class OrdemServico(db.Model):
    __tablename__ = 'ordens_servico'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    observacoes = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    desconto = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='Aberta')
    status = db.Column(db.String(50), default='Aberta')

    itens_os = db.relationship('ItemOS', backref='ordem', cascade='all, delete-orphan')  # ✅ nome ajustado


class ItemOS(db.Model):
    __tablename__ = 'itens_os'
    id = db.Column(db.Integer, primary_key=True)
    os_id = db.Column(db.Integer, db.ForeignKey('ordens_servico.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produtos.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)

    produto = db.relationship('Produto')


class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)  # Armazenar como hash

class Empresa(db.Model):
    __tablename__ = 'empresa'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    endereco = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    cnpj = db.Column(db.String(20))
    observacoes = db.Column(db.Text)
    site = db.Column(db.String(100))

class Servico(db.Model):
    __tablename__ = 'servicos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(200))
    preco = db.Column(db.Float, nullable=False)
