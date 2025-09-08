from flask import Flask, flash, render_template, request, redirect, url_for, make_response
from models import Empresa, Servico, Usuario, db, Cliente, Produto, OrdemServico, ItemOS
from xhtml2pdf import pisa
from io import BytesIO

app = Flask(__name__)
##app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orcamento.db'##
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://sistema_de_orcamentos_user:wOZ7KITrJfv5F0ZEAVk7jIZW0lUcoOX9@dpg-d2ni5ae3jp1c73cn2f30-a/sistema_de_orcamentos'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

from flask import session
app.secret_key = 'sua_chave_secreta_aqui'  # Use uma chave segura e única
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 🏠 Home
@app.route('/')
@login_required
def index():
    return redirect(url_for('home'))

@app.route('/home')
@login_required
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        senha = request.form.get('senha')

        usuario = Usuario.query.filter_by(username=username).first()
        if usuario and usuario.senha == senha:  # Em produção, use hash
            session['usuario_id'] = usuario.id
            return redirect(url_for('home'))
        else:
            return "Usuário ou senha inválidos", 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/cadastrar_usuario', methods=['GET', 'POST'])
def cadastrar_usuario():
    if request.method == 'POST':
        username = request.form.get('username')
        senha = request.form.get('senha')
        confirmar = request.form.get('confirmar_senha')

        if not username or not senha:
            return "Usuário e senha são obrigatórios", 400
        if senha != confirmar:
            return "As senhas não coincidem", 400

        novo_usuario = Usuario(username=username, senha=senha)  # Use hash em produção
        db.session.add(novo_usuario)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('cadastrar_usuario.html')

@app.route('/usuarios')
@login_required
def listar_usuarios():
    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuario/editar/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    if request.method == 'POST':
        usuario.username = request.form.get('username')
        nova_senha = request.form.get('senha')
        if nova_senha:
            usuario.senha = nova_senha  # Use hash em produção
        db.session.commit()
        return redirect(url_for('listar_usuarios'))
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/usuario/excluir/<int:usuario_id>')
@login_required
def excluir_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    db.session.delete(usuario)
    db.session.commit()
    return redirect(url_for('listar_usuarios'))

# 👤 Cadastro de Cliente
@app.route('/cadastrar_cliente', methods=['GET', 'POST'])
@login_required
def cadastrar_cliente():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf_cnpj = request.form.get('cpf_cnpj')
        telefone = request.form.get('telefone')
        email = request.form.get('email')

        if not nome or not cpf_cnpj:
            flash("Nome e CPF/CNPJ são obrigatórios.", "danger")
            return redirect(url_for('cadastrar_cliente'))

        # Verifica se já existe cliente com mesmo CPF/CNPJ
        cliente_existente = Cliente.query.filter_by(cpf_cnpj=cpf_cnpj).first()
        if cliente_existente:
            flash("Cliente já cadastrado com este CPF/CNPJ.", "warning")
            return redirect(url_for('cadastrar_cliente'))

        novo_cliente = Cliente(
            nome=nome,
            cpf_cnpj=cpf_cnpj,
            telefone=telefone,
            email=email
        )
        db.session.add(novo_cliente)
        db.session.commit()
        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for('nova_os'))

    return render_template('cadastrar_cliente.html')

@app.route('/cliente/<int:cliente_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)

    if request.method == 'POST':
        cliente.nome = request.form.get('nome')
        cliente.telefone = request.form.get('telefone')
        cliente.email = request.form.get('email')
        cliente.cpf_cnpj = request.form.get('cpf_cnpj')

        db.session.commit()
        flash("Cliente atualizado com sucesso!")
        return redirect(url_for('listar_clientes'))

    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/clientes')
@login_required
def listar_clientes():
    termo = request.args.get('busca', '').strip()
    if termo:
        clientes = Cliente.query.filter(Cliente.nome.ilike(f'%{termo}%')).order_by(Cliente.nome).all()
    else:
        clientes = Cliente.query.order_by(Cliente.nome).all()
    return render_template('clientes.html', clientes=clientes)

@app.route('/cliente/<int:cliente_id>/ordens')
@login_required
def ordens_por_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    ordens = OrdemServico.query.filter_by(cliente_id=cliente.id).order_by(OrdemServico.data_criacao.desc()).all()

    lista_os = []
    for os in ordens:
        total = sum(item.quantidade * item.produto.preco for item in os.itens_os)
        lista_os.append({'os': os, 'total': total})

    return render_template('ordens_por_cliente.html', cliente=cliente, lista_os=lista_os)

from flask import request, redirect, url_for, render_template
from datetime import datetime

@app.route('/os/<int:os_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_os(os_id):
    os = OrdemServico.query.get_or_404(os_id)
    produtos = Produto.query.all()

    if request.method == 'POST':
        # Atualiza dados principais da OS
        os.data_criacao = datetime.strptime(request.form.get('data_criacao'), '%Y-%m-%d')
        os.status = request.form.get('status')
        os.desconto = float(request.form.get('desconto') or 0)

        # Excluir item
        excluir_id = request.form.get('excluir_item')
        if excluir_id:
            item = ItemOS.query.get(int(excluir_id))
            if item and item.os_id == os.id:
                db.session.delete(item)
                db.session.commit()
                return redirect(url_for('editar_os', os_id=os.id))

        # Atualizar itens existentes
        for item in os.itens_os:
            qtd = request.form.get(f'quantidade_{item.id}')
            preco = request.form.get(f'preco_{item.id}')
            if qtd and preco:
                item.quantidade = int(qtd)
                item.produto.preco = float(preco)

        # Adicionar novo item
        if request.form.get('adicionar_item'):
            produto_id = request.form.get('novo_produto_id')
            quantidade = request.form.get('nova_quantidade')
            if produto_id and quantidade:
                produto = Produto.query.get(int(produto_id))
                if produto:
                    novo_item = ItemOS(
                        os_id=os.id,
                        produto_id=produto.id,
                        quantidade=int(quantidade)
                    )
                    db.session.add(novo_item)

        db.session.commit()

        # 🔁 Redireciona para a lista de ordens do cliente
        return redirect(url_for('ordens_por_cliente', cliente_id=os.cliente_id))

    return render_template('editar_os.html', os=os, produtos=produtos)

@app.route('/nova_os/cliente/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def nova_os_para_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    produtos = Produto.query.all()

    if request.method == 'POST':
        observacoes = request.form.get('observacoes')
        nova_os = OrdemServico(cliente_id=cliente.id, observacoes=observacoes)
        db.session.add(nova_os)
        db.session.commit()

        produtos_ids = request.form.getlist('produto')
        quantidades = request.form.getlist('quantidade')

        for pid, qtd in zip(produtos_ids, quantidades):
            item = ItemOS(
                os_id=nova_os.id,
                produto_id=int(pid),
                quantidade=int(qtd)
            )
            db.session.add(item)

        db.session.commit()
        return redirect(url_for('visualizar_os', os_id=nova_os.id))

    return render_template('nova_os.html', cliente=cliente, produtos=produtos)

# 📦 Cadastro de Produto

@app.route('/produtos')
@login_required
def listar_produtos():
    produtos = Produto.query.order_by(Produto.nome).all()
    return render_template('produtos.html', produtos=produtos)

@app.route('/cadastrar_produto', methods=['GET', 'POST'])
@login_required
def cadastrar_produto():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = request.form.get('preco')

        if not nome or not preco:
            return "Nome e preço são obrigatórios", 400

        novo_produto = Produto(nome=nome, descricao=descricao, preco=float(preco))
        db.session.add(novo_produto)
        db.session.commit()
        return redirect(url_for('nova_os'))

    return render_template('cadastrar_produto.html')

@app.route('/produto/<int:produto_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)

    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = request.form.get('preco')

        if not nome or not preco:
            return "Nome e preço são obrigatórios", 400

        produto.nome = nome
        produto.descricao = descricao
        produto.preco = float(preco)

        db.session.commit()
        flash("Produto atualizado com sucesso!")
        return redirect(url_for('listar_produtos'))  # ou outro destino que preferir

    return render_template('editar_produto.html', produto=produto)


# 🛠️ Cadastro de Serviço (usa mesma tabela de Produto)
@app.route('/servicos')
@login_required
def listar_servicos():
    servicos = Servico.query.order_by(Servico.nome).all()
    return render_template('servicos.html', servicos=servicos)

@app.route('/cadastrar_servico', methods=['GET', 'POST'])
@login_required
def cadastrar_servico():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = request.form.get('preco')

        if not nome or not preco:
            flash("Nome e preço são obrigatórios.", "danger")
            return redirect(url_for('cadastrar_servico'))

        novo_servico = Servico(nome=nome, descricao=descricao, preco=float(preco))
        db.session.add(novo_servico)
        db.session.commit()
        flash("Serviço cadastrado com sucesso!", "success")
        return redirect(url_for('listar_servicos'))

    return render_template('cadastrar_servico.html')

@app.route('/servico/<int:servico_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_servico(servico_id):
    servico = Servico.query.get_or_404(servico_id)

    if request.method == 'POST':
        servico.nome = request.form.get('nome')
        servico.descricao = request.form.get('descricao')
        servico.preco = float(request.form.get('preco') or 0)

        db.session.commit()
        flash("Serviço atualizado com sucesso!")
        return redirect(url_for('listar_servicos'))

    return render_template('editar_servico.html', servico=servico)


@app.route('/nova_os', methods=['GET', 'POST'])
@login_required
def nova_os():
    clientes = Cliente.query.all()
    produtos = Produto.query.all()

    if request.method == 'POST':
        cliente_id = request.form.get('cliente')
        observacoes = request.form.get('observacoes')
        desconto = request.form.get('desconto') or 0  # ✅ Captura o campo de desconto

        if not cliente_id:
            return "Cliente não selecionado", 400

        nova_os = OrdemServico(
            cliente_id=cliente_id,
            observacoes=observacoes,
            desconto=float(desconto)  # ✅ Salva o desconto
        )
        db.session.add(nova_os)
        db.session.commit()

        produtos_ids = request.form.getlist('produto[]')
        quantidades = request.form.getlist('quantidade[]')

        for pid, qtd in zip(produtos_ids, quantidades):
            if pid and qtd:
                item = ItemOS(
                    os_id=nova_os.id,
                    produto_id=int(pid),
                    quantidade=int(qtd)
                )
                db.session.add(item)

        db.session.commit()
        return redirect(url_for('visualizar_os', os_id=nova_os.id))

    return render_template('nova_os.html', clientes=clientes, produtos=produtos)

# 🔍 Visualizar Ordem de Serviço
@app.route('/os/<int:os_id>')
def visualizar_os(os_id):
    os = OrdemServico.query.get_or_404(os_id)
    subtotal = sum(item.quantidade * item.produto.preco for item in os.itens_os)
    total = max(subtotal - (os.desconto or 0), 0)
    return render_template('visualizar_os.html', os=os, subtotal=subtotal, total=total)

# 🖨️ Gerar PDF da Ordem de Serviço
@app.route('/os/<int:os_id>/pdf')
@login_required
def gerar_pdf(os_id):
    os = OrdemServico.query.get_or_404(os_id)
    empresa = Empresa.query.first()  # ✅ Adiciona os dados da empresa

    subtotal = sum(item.quantidade * item.produto.preco for item in os.itens_os)
    total = max(subtotal - (os.desconto or 0), 0)

    html = render_template('os_pdf.html', os=os, subtotal=subtotal, total=total, empresa=empresa)

    result = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=result)

    if pisa_status.err:
        return "Erro ao gerar PDF", 500

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=os_{os.id}.pdf'
    return response

from datetime import datetime

@app.template_filter('moeda')
def moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

@app.route('/empresa', methods=['GET', 'POST'])
@login_required
def empresa():
    empresa = Empresa.query.first()

    if request.method == 'POST':
        if not empresa:
            empresa = Empresa()
            db.session.add(empresa)

        empresa.nome = request.form.get('nome')
        empresa.endereco = request.form.get('endereco')
        empresa.telefone = request.form.get('telefone')
        empresa.email = request.form.get('email')
        empresa.cnpj = request.form.get('cnpj')
        empresa.observacoes = request.form.get('observacoes')
        empresa.site = request.form.get('site')

        db.session.commit()
        flash("Dados da empresa atualizados com sucesso!")
        return redirect(url_for('empresa'))

    return render_template('empresa.html', empresa=empresa)

@app.route('/empresa/editar', methods=['GET', 'POST'])
@login_required
def editar_empresa():
    empresa = Empresa.query.first()

    if request.method == 'POST':
        if not empresa:
            empresa = Empresa()

        empresa.nome = request.form.get('nome')
        empresa.endereco = request.form.get('endereco')
        empresa.telefone = request.form.get('telefone')
        empresa.email = request.form.get('email')
        empresa.cnpj = request.form.get('cnpj')
        empresa.site = request.form.get('site')
        empresa.observacoes = request.form.get('observacoes')

        db.session.add(empresa)
        db.session.commit()
        return redirect(url_for('empresa'))

    return render_template('editar_empresa.html', empresa=empresa)

from datetime import datetime

@app.route('/dashboard')
@login_required
def dashboard():
    total_os = OrdemServico.query.count()
    total_clientes = Cliente.query.count()

    valor_total = sum(os.total for os in OrdemServico.query.all())
    valor_pago = sum(os.total for os in OrdemServico.query.filter_by(status='Pago').all())
    valor_cancelado = sum(os.total for os in OrdemServico.query.filter_by(status='Cancelado').all())
    valor_aberto = sum(os.total for os in OrdemServico.query.filter_by(status='Aberta').all())

    hoje = datetime.today()
    inicio_mes = datetime(hoje.year, hoje.month, 1)
    ultimas_ordens = OrdemServico.query.filter(
        OrdemServico.data_criacao >= inicio_mes
    ).order_by(OrdemServico.data_criacao.desc()).limit(10).all()

    return render_template(
        'dashboard.html',
        total_os=total_os,
        total_clientes=total_clientes,
        valor_total=valor_total,
        valor_pago=valor_pago,
        valor_cancelado=valor_cancelado,
        valor_aberto=valor_aberto,
        ultimas_ordens=ultimas_ordens
    )


@app.route('/ordens')
@login_required
def buscar_ordens():
    termo = request.args.get('busca', '').strip()
    status = request.args.get('status', '').strip()

    query = OrdemServico.query.join(Cliente)

    if termo:
        query = query.filter(
            db.or_(
                Cliente.nome.ilike(f'%{termo}%'),
                db.cast(OrdemServico.data_criacao, db.String).ilike(f'%{termo}%')
            )
        )

    if status:
        query = query.filter(OrdemServico.status == status)

    ordens = query.order_by(OrdemServico.data_criacao.desc()).all()
    return render_template('buscar_ordens.html', ordens=ordens, termo=termo, status=status)

# 🚀 Executa o servidor
if __name__ == '__main__':
    app.run(debug=True)


