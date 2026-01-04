from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
import logging
import hashlib
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')
DATA_DIR = os.path.join(BASE_DIR, 'data')


# Configuração do logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=None)  # HTML puro em /public (sem conflito de rotas)
CORS(app, supports_credentials=True)

# Configurações de SESSÃO
app.config['SECRET_KEY'] = 'contrato-mais-secret-key-2024'
app.config['SESSION_COOKIE_NAME'] = 'contrato_mais_session'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

# Inicializar Session

# Configurações do Email
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'contratomais.suporte1@gmail.com',
    'sender_password': 'hsri smmy tyea sgac',
    'use_tls': True
}

# Configurações do banco de dados
DATABASE = os.path.join(DATA_DIR, 'contratos.db')

def get_db_connection():
    """Conecta ao banco de dados SQLite"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def verificar_banco_dados():
    """
    Verifica se o banco de dados existe e cria as tabelas se necessário
    """
    print("=" * 60)
    print("VERIFICAÇÃO DO BANCO DE DADOS - CONTRATO+")
    print("=" * 60)
    
    if not os.path.exists(DATABASE):
        print(f"📦 Criando banco de dados: {DATABASE}")
        criar_tabelas()
    else:
        print(f"✅ Banco de dados encontrado: {DATABASE}")
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tabelas = cursor.fetchall()
            
            if tabelas:
                print("📋 Tabelas encontradas:")
                for tabela in tabelas:
                    tabela_nome = tabela[0]
                    try:
                        cursor.execute(f"SELECT COUNT(*) as total FROM [{tabela_nome}]")
                        total = cursor.fetchone()[0]
                        print(f"   • {tabela_nome}: {total} registros")
                    except Exception as e:
                        print(f"   • {tabela_nome}: erro ao acessar - {str(e)}")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Erro ao verificar tabelas: {str(e)}")
    
    print("=" * 60)

def criar_tabelas():
    """Cria as tabelas no banco de dados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome_completo TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de contratos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contrato (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                descricao TEXT,
                data_inicio TIMESTAMP NOT NULL,
                data_fim TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'ativo',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usuario_id INTEGER NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuario (id)
            )
        ''')
        
        # Tabela de notificações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notificacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contrato_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                assunto TEXT NOT NULL,
                mensagem TEXT,
                email_destino TEXT NOT NULL,
                status TEXT DEFAULT 'pendente',
                data_envio TIMESTAMP,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contrato_id) REFERENCES contrato (id)
            )
        ''')
        
        # Verificar se existe usuário admin
        cursor.execute("SELECT COUNT(*) as total FROM usuario WHERE email = 'admin@contratomais.com'")
        total = cursor.fetchone()[0]
        
        if total == 0:
            senha_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute(
                'INSERT INTO usuario (nome_completo, email, senha_hash) VALUES (?, ?, ?)',
                ('Administrador', 'admin@contratomais.com', senha_hash)
            )
            print("✅ Usuário admin criado: admin@contratomais.com / admin123")
        
        conn.commit()
        conn.close()
        
        print("✅ Tabelas criadas com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {str(e)}")

def hash_senha(senha):
    """Gera hash da senha usando SHA-256"""
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_senha(senha, senha_hash):
    """Verifica se a senha corresponde ao hash"""
    return hash_senha(senha) == senha_hash

# ========== DECORATORS E HELPERS ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return jsonify({'authenticated': False, 'message': 'Não autenticado'}), 401
        return f(*args, **kwargs)
    return decorated_function

require_login = login_required  # alias compatível

def get_usuario_atual():
    if 'usuario_id' in session:
        conn = get_db_connection()
        usuario = conn.execute('SELECT * FROM usuario WHERE id = ?', (session['usuario_id'],)).fetchone()
        conn.close()
        return usuario
    return None

def criar_template_email(assunto, titulo, mensagem, tipo_notificacao=None, contrato=None):
    """Cria um template de email bonito com design moderno"""
    
    if contrato:
        data_inicio = formatar_data_brasil(contrato['data_inicio'])
        data_fim = formatar_data_brasil(contrato['data_fim'])
        
        # Calcular dias restantes
        hoje = datetime.utcnow()
        data_fim_obj = datetime.fromisoformat(contrato['data_fim'].replace('Z', '+00:00'))
        dias_restantes = (data_fim_obj - hoje).days
        
        # Determinar cor baseada no tipo
        if tipo_notificacao == 'urgente':
            cor_primaria = '#dc2626'  # Vermelho
            icone = '⚠️'
        elif tipo_notificacao == 'aviso':
            cor_primaria = '#f59e0b'  # Amarelo
            icone = '📅'
        else:
            cor_primaria = '#10b981'  # Verde
            icone = '📋'
        
        detalhes_contrato = f"""
        <div style="background: #f8fafc; border-radius: 8px; padding: 20px; margin: 20px 0; border-left: 4px solid {cor_primaria};">
            <h3 style="margin-top: 0; color: #1e293b;">📄 Detalhes do Contrato</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;"><strong>Nome:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;">{contrato['nome']}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;"><strong>Descrição:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;">{contrato['descricao'] or 'Não informada'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;"><strong>Data Início:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;">{data_inicio}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;"><strong>Data Término:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e2e8f0;">{data_fim}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Dias Restantes:</strong></td>
                    <td style="padding: 8px 0;">
                        <span style="background: {'#fee2e2' if dias_restantes < 7 else '#fef3c7' if dias_restantes < 30 else '#d1fae5'}; 
                              color: {'#991b1b' if dias_restantes < 7 else '#92400e' if dias_restantes < 30 else '#065f46'}; 
                              padding: 4px 12px; border-radius: 20px; font-weight: bold;">
                            {dias_restantes} dias
                        </span>
                    </td>
                </tr>
            </table>
        </div>
        """
    else:
        detalhes_contrato = ""
        cor_primaria = "#2563eb"
        icone = "📧"
    
    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{assunto}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #334155;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background: white;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
            }}
            
            .header {{
                background: linear-gradient(135deg, {cor_primaria} 0%, {cor_primaria}99 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }}
            
            .header::before {{
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
                background-size: 20px 20px;
                opacity: 0.3;
            }}
            
            .logo {{
                font-size: 32px;
                font-weight: 700;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
            }}
            
            .icon {{
                font-size: 36px;
                animation: float 3s ease-in-out infinite;
            }}
            
            @keyframes float {{
                0%, 100% {{ transform: translateY(0); }}
                50% {{ transform: translateY(-10px); }}
            }}
            
            .content {{
                padding: 40px 30px;
                background: #f8fafc;
            }}
            
            .card {{
                background: white;
                border-radius: 16px;
                padding: 30px;
                margin: 20px 0;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
                border: 1px solid #e2e8f0;
            }}
            
            .title {{
                color: #1e293b;
                font-size: 24px;
                font-weight: 700;
                margin: 0 0 20px 0;
            }}
            
            .message {{
                font-size: 16px;
                line-height: 1.7;
                color: #475569;
                margin-bottom: 25px;
            }}
            
            .divider {{
                height: 1px;
                background: linear-gradient(to right, transparent, #e2e8f0, transparent);
                margin: 30px 0;
            }}
            
            .footer {{
                text-align: center;
                padding: 25px 30px;
                background: #1e293b;
                color: #cbd5e1;
                font-size: 14px;
            }}
            
            .badge {{
                display: inline-block;
                background: linear-gradient(135deg, {cor_primaria}22, {cor_primaria}44);
                color: {cor_primaria};
                padding: 8px 20px;
                border-radius: 50px;
                font-weight: 600;
                font-size: 14px;
                margin: 10px 0;
                border: 1px solid {cor_primaria}33;
            }}
            
            .action-button {{
                display: inline-block;
                background: linear-gradient(135deg, {cor_primaria}, {cor_primaria}dd);
                color: white;
                text-decoration: none;
                padding: 14px 32px;
                border-radius: 50px;
                font-weight: 600;
                font-size: 15px;
                margin: 20px 0;
                border: none;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            
            .action-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 25px {cor_primaria}40;
            }}
            
            .status-indicator {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                margin: 20px 0;
                font-weight: 600;
            }}
            
            .dot {{
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: {cor_primaria};
                animation: pulse 2s infinite;
            }}
            
            @keyframes pulse {{
                0% {{ opacity: 1; transform: scale(1); }}
                50% {{ opacity: 0.5; transform: scale(1.1); }}
                100% {{ opacity: 1; transform: scale(1); }}
            }}
            
            @media (max-width: 600px) {{
                .container {{
                    margin: 20px;
                    border-radius: 16px;
                }}
                
                .header {{
                    padding: 30px 20px;
                }}
                
                .content {{
                    padding: 30px 20px;
                }}
                
                .card {{
                    padding: 20px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 class="logo">
                    <span class="icon">{icone}</span>
                    CONTRATO<span style="color: #fbbf24;">+</span>
                </h1>
                <p style="opacity: 0.9; font-size: 14px; margin-top: 10px;">Sistema Inteligente de Gerenciamento</p>
            </div>
            
            <div class="content">
                <div class="card">
                    <h2 class="title">{titulo}</h2>
                    
                    <div class="badge">
                        {tipo_notificacao.upper() if tipo_notificacao else 'NOTIFICAÇÃO'}
                    </div>
                    
                    <div class="message">
                        {mensagem}
                    </div>
                    
                    {detalhes_contrato}
                    
                    <div class="divider"></div>
                    
                    <div class="status-indicator">
                        <div class="dot"></div>
                        <span>Esta é uma notificação automática do sistema CONTRATO+</span>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="http://localhost:5000" class="action-button">
                            📊 Acessar Dashboard
                        </a>
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p style="margin: 0 0 10px 0;">
                    © 2026 CONTRATO+ · Todos os direitos reservados
                </p>
                <p style="margin: 0; font-size: 13px; opacity: 0.8;">
                    Esta é uma mensagem automática. Por favor, não responda este e-mail.
                </p>
                <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.7;">
                    <a href="mailto:contratomais.suporte1@gmail.com" style="color: #94a3b8; text-decoration: none;">
                        ✉️ Suporte: contratomais.suporte1@gmail.com
                    </a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def enviar_email(destinatarios, assunto, corpo_html, corpo_texto=None):
    """Envia email usando Gmail SMTP com design moderno"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = f'CONTRATO+ <{EMAIL_CONFIG["sender_email"]}>'
        
        if isinstance(destinatarios, list):
            msg['To'] = ', '.join(destinatarios)
            to_list = destinatarios
        else:
            msg['To'] = destinatarios
            to_list = [destinatarios]
        
        if corpo_texto:
            part1 = MIMEText(corpo_texto, 'plain')
            msg.attach(part1)
        
        part2 = MIMEText(corpo_html, 'html')
        msg.attach(part2)
        
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.ehlo()
        
        if EMAIL_CONFIG['use_tls']:
            server.starttls()
        
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email enviado para {destinatarios}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar email: {str(e)}")
        return False

def formatar_data_brasil(data):
    """Formata data para padrão brasileiro"""
    if isinstance(data, str):
        data = datetime.fromisoformat(data.replace('Z', '+00:00'))
    return data.strftime('%d/%m/%Y %H:%M')

# ========== ROTAS DE ARQUIVOS ESTÁTICOS ==========




# =========================
# SERVIR PÁGINAS (HTML PURO)
# =========================
PAGINAS_PROTEGIDAS = {
    'dashboard.html',
    'contratos.html',
    'notificacoes.html',
    'configuracoes.html',
}

def _serve_public(filename: str):
    """Serve arquivos da pasta /public. Se a página for protegida, exige sessão."""
    if filename in PAGINAS_PROTEGIDAS and 'usuario_id' not in session:
        filename = 'index.html'
    return send_from_directory(PUBLIC_DIR, filename)

@app.route('/')
def serve_index():
    if 'usuario_id' in session:
        return send_from_directory(PUBLIC_DIR, 'dashboard.html')
    return send_from_directory(PUBLIC_DIR, 'index.html')

# Rotas explícitas (.html) – evita 404 mesmo se o catch-all falhar
@app.route('/dashboard.html')
def dashboard_html():
    return _serve_public('dashboard.html')

@app.route('/contratos.html')
def contratos_html():
    return _serve_public('contratos.html')

@app.route('/configuracoes.html')
def configuracoes_html():
    return _serve_public('configuracoes.html')

@app.route('/notificacoes.html')
def notificacoes_html():
    return _serve_public('notificacoes.html')

# Rotas amigáveis (sem .html)
@app.route('/dashboard')
def dashboard_route():
    return _serve_public('dashboard.html')

@app.route('/contratos')
def contratos_route():
    return _serve_public('contratos.html')

@app.route('/configuracoes')
def configuracoes_route():
    return _serve_public('configuracoes.html')

@app.route('/notificacoes')
def notificacoes_route():
    return _serve_public('notificacoes.html')

# Arquivos JS/CSS (mantém seus paths atuais)
@app.route('/api.js')
def api_js():
    return send_from_directory(PUBLIC_DIR, 'api.js')

@app.route('/auth.js')
def auth_js():
    return send_from_directory(PUBLIC_DIR, 'auth.js')

# Fallback para qualquer outro arquivo em /public (ex: imagens, fonts, etc.)
@app.route('/<path:filename>')
def serve_static(filename):
    return _serve_public(filename)

# ========== ROTAS DE AUTENTICAÇÃO ==========
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        nome_completo = data.get('nome_completo')
        email = data.get('email')
        senha = data.get('senha')
        
        if not all([nome_completo, email, senha]):
            return jsonify({'success': False, 'message': 'Todos os campos são obrigatórios'}), 400
        
        conn = get_db_connection()
        
        usuario_existente = conn.execute(
            'SELECT id FROM usuario WHERE email = ?', (email,)
        ).fetchone()
        
        if usuario_existente:
            conn.close()
            return jsonify({'success': False, 'message': 'Email já cadastrado'}), 400
        
        senha_hash = hash_senha(senha)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO usuario (nome_completo, email, senha_hash) VALUES (?, ?, ?)',
            (nome_completo, email, senha_hash)
        )
        usuario_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        session.permanent = True
        session['usuario_id'] = usuario_id
        session['usuario_nome'] = nome_completo
        session['usuario_email'] = email
        
        return jsonify({
            'success': True,
            'message': 'Usuário criado com sucesso',
            'user': {
                'id': usuario_id,
                'nome_completo': nome_completo,
                'email': email
            }
        })
        
    except Exception as e:
        logger.error(f"Erro no registro: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao criar usuário'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        senha = data.get('senha')
        
        if not email or not senha:
            return jsonify({'success': False, 'message': 'Email e senha são obrigatórios'}), 400
        
        conn = get_db_connection()
        usuario = conn.execute(
            'SELECT * FROM usuario WHERE email = ?', (email,)
        ).fetchone()
        conn.close()
        
        if not usuario or not verificar_senha(senha, usuario['senha_hash']):
            return jsonify({'success': False, 'message': 'Credenciais inválidas'}), 401
        
        session.permanent = True
        session['usuario_id'] = usuario['id']
        session['usuario_nome'] = usuario['nome_completo']
        session['usuario_email'] = usuario['email']
        
        return jsonify({
            'success': True,
            'message': 'Login realizado com sucesso',
            'user': {
                'id': usuario['id'],
                'nome_completo': usuario['nome_completo'],
                'email': usuario['email']
            }
        })
        
    except Exception as e:
        logger.error(f"Erro no login: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro no login'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logout realizado com sucesso'})

@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    usuario = get_usuario_atual()
    if usuario:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': usuario['id'],
                'nome_completo': usuario['nome_completo'],
                'email': usuario['email']
            }
        })
    return jsonify({'authenticated': False})

# ========== ROTAS DE CONTRATOS ==========
@app.route('/api/contratos', methods=['GET'])
@login_required
def listar_contratos():
    try:
        usuario_id = session['usuario_id']
        conn = get_db_connection()
        
        contratos = conn.execute('''
            SELECT * FROM contrato 
            WHERE usuario_id = ? 
            ORDER BY data_fim
        ''', (usuario_id,)).fetchall()
        
        conn.close()
        
        contratos_json = []
        for contrato in contratos:
            contratos_json.append({
                'id': contrato['id'],
                'nome': contrato['nome'],
                'descricao': contrato['descricao'],
                'data_inicio': contrato['data_inicio'],
                'data_fim': contrato['data_fim'],
                'status': contrato['status'],
                'criado_em': contrato['criado_em'],
                'atualizado_em': contrato['atualizado_em'],
                'dias_restantes': calcular_dias_restantes(contrato['data_fim'])
            })
        
        return jsonify({
            'success': True,
            'contratos': contratos_json
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar contratos: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao listar contratos'}), 500

@app.route('/api/contratos/<int:id>', methods=['GET'])
@login_required
def obter_contrato(id):
    try:
        usuario_id = session['usuario_id']
        conn = get_db_connection()
        
        contrato = conn.execute(
            'SELECT * FROM contrato WHERE id = ? AND usuario_id = ?',
            (id, usuario_id)
        ).fetchone()
        
        conn.close()
        
        if not contrato:
            return jsonify({'success': False, 'message': 'Contrato não encontrado'}), 404
        
        return jsonify({
            'success': True,
            'contrato': {
                'id': contrato['id'],
                'nome': contrato['nome'],
                'descricao': contrato['descricao'],
                'data_inicio': contrato['data_inicio'],
                'data_fim': contrato['data_fim'],
                'status': contrato['status'],
                'criado_em': contrato['criado_em'],
                'atualizado_em': contrato['atualizado_em'],
                'dias_restantes': calcular_dias_restantes(contrato['data_fim'])
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter contrato: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao obter contrato'}), 500

@app.route('/api/contratos', methods=['POST'])
@login_required
def criar_contrato():
    try:
        usuario_id = session['usuario_id']
        data = request.json
        
        required_fields = ['nome', 'data_inicio', 'data_fim']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'Campo {field} é obrigatório'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO contrato (nome, descricao, data_inicio, data_fim, status, usuario_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['nome'],
            data.get('descricao', ''),
            data['data_inicio'],
            data['data_fim'],
            data.get('status', 'ativo'),
            usuario_id
        ))
        
        contrato_id = cursor.lastrowid
        conn.commit()
        
        contrato = conn.execute(
            'SELECT * FROM contrato WHERE id = ?', (contrato_id,)
        ).fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Contrato criado com sucesso',
            'contrato': {
                'id': contrato['id'],
                'nome': contrato['nome'],
                'descricao': contrato['descricao'],
                'data_inicio': contrato['data_inicio'],
                'data_fim': contrato['data_fim'],
                'status': contrato['status'],
                'dias_restantes': calcular_dias_restantes(contrato['data_fim'])
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar contrato: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao criar contrato'}), 500

@app.route('/api/contratos/<int:id>', methods=['PUT'])
@login_required
def atualizar_contrato(id):
    try:
        usuario_id = session['usuario_id']
        data = request.json
        
        conn = get_db_connection()
        
        contrato = conn.execute(
            'SELECT * FROM contrato WHERE id = ? AND usuario_id = ?',
            (id, usuario_id)
        ).fetchone()
        
        if not contrato:
            conn.close()
            return jsonify({'success': False, 'message': 'Contrato não encontrado'}), 404
        
        updates = []
        params = []
        
        campos = ['nome', 'descricao', 'data_inicio', 'data_fim', 'status']
        for campo in campos:
            if campo in data:
                updates.append(f'{campo} = ?')
                params.append(data[campo])
        
        updates.append('atualizado_em = CURRENT_TIMESTAMP')
        
        if updates:
            query = f'UPDATE contrato SET {", ".join(updates)} WHERE id = ? AND usuario_id = ?'
            params.extend([id, usuario_id])
            
            conn.execute(query, params)
            conn.commit()
        
        contrato = conn.execute(
            'SELECT * FROM contrato WHERE id = ?', (id,)
        ).fetchone()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Contrato atualizado com sucesso',
            'contrato': {
                'id': contrato['id'],
                'nome': contrato['nome'],
                'descricao': contrato['descricao'],
                'data_inicio': contrato['data_inicio'],
                'data_fim': contrato['data_fim'],
                'status': contrato['status'],
                'dias_restantes': calcular_dias_restantes(contrato['data_fim'])
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao atualizar contrato: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao atualizar contrato'}), 500

@app.route('/api/contratos/<int:id>', methods=['DELETE'])
@login_required
def excluir_contrato(id):
    try:
        usuario_id = session['usuario_id']
        
        conn = get_db_connection()
        
        contrato = conn.execute(
            'SELECT * FROM contrato WHERE id = ? AND usuario_id = ?',
            (id, usuario_id)
        ).fetchone()
        
        if not contrato:
            conn.close()
            return jsonify({'success': False, 'message': 'Contrato não encontrado'}), 404
        
        conn.execute('DELETE FROM notificacao WHERE contrato_id = ?', (id,))
        conn.execute('DELETE FROM contrato WHERE id = ? AND usuario_id = ?', (id, usuario_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Contrato excluído com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao excluir contrato: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao excluir contrato'}), 500

# ========== ROTAS DE NOTIFICAÇÕES ==========
@app.route('/api/notificacoes', methods=['GET'])
@login_required
def listar_notificacoes():
    try:
        usuario_id = session['usuario_id']
        conn = get_db_connection()
        
        notificacoes = conn.execute('''
            SELECT n.*, c.nome as contrato_nome
            FROM notificacao n
            JOIN contrato c ON n.contrato_id = c.id
            WHERE c.usuario_id = ?
            ORDER BY n.criado_em DESC
        ''', (usuario_id,)).fetchall()
        
        conn.close()
        
        notificacoes_json = []
        for notif in notificacoes:
            notificacoes_json.append({
                'id': notif['id'],
                'contrato_id': notif['contrato_id'],
                'contrato_nome': notif['contrato_nome'],
                'tipo': notif['tipo'],
                'assunto': notif['assunto'],
                'mensagem': notif['mensagem'],
                'email_destino': notif['email_destino'],
                'status': notif['status'],
                'data_envio': notif['data_envio'],
                'criado_em': notif['criado_em']
            })
        
        return jsonify({
            'success': True,
            'notificacoes': notificacoes_json
        })
        
    except Exception as e:
        logger.error(f"Erro ao listar notificações: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao listar notificações'}), 500

@app.route('/api/contratos/<int:contrato_id>/notificar', methods=['POST'])
@login_required
def enviar_notificacao(contrato_id):
    try:
        usuario_id = session['usuario_id']
        data = request.json
        
        conn = get_db_connection()
        
        contrato = conn.execute('''
            SELECT * FROM contrato 
            WHERE id = ? AND usuario_id = ?
        ''', (contrato_id, usuario_id)).fetchone()
        
        if not contrato:
            conn.close()
            return jsonify({'success': False, 'message': 'Contrato não encontrado'}), 404
        
        emails = data.get('emails')
        tipo = data.get('tipo')
        assunto = data.get('assunto', 'Notificação de Contrato - CONTRATO+')
        mensagem_customizada = data.get('mensagem_customizada')
        
        if not emails or not tipo:
            conn.close()
            return jsonify({'success': False, 'message': 'Emails e tipo são obrigatórios'}), 400
        
        if isinstance(emails, str):
            emails_list = [email.strip() for email in emails.split(',')]
        elif isinstance(emails, list):
            emails_list = emails
        else:
            conn.close()
            return jsonify({'success': False, 'message': 'Formato de emails inválido'}), 400
        
        # Validar emails
        for email in emails_list:
            if '@' not in email or '.' not in email:
                conn.close()
                return jsonify({'success': False, 'message': f'Email inválido: {email}'}), 400
        
        # Determinar tipo de notificação para design
        if tipo == 'lembrete_diario':
            tipo_design = 'urgente'
            titulo = '⚠️ CONTRATO VENCE AMANHÃ!'
            mensagem = mensagem_customizada or f"O contrato <strong>{contrato['nome']}</strong> está prestes a vencer! Tome as providências necessárias imediatamente para evitar interrupção dos serviços."
        elif tipo == 'lembrete_semanal':
            tipo_design = 'aviso'
            titulo = '📅 Contrato Próximo do Vencimento'
            mensagem = mensagem_customizada or f"O contrato <strong>{contrato['nome']}</strong> vencerá em 7 dias. Verifique as condições para renovação."
        elif tipo == 'lembrete_mensal':
            tipo_design = 'info'
            titulo = '📋 Lembrete de Contrato'
            mensagem = mensagem_customizada or f"Este é um lembrete automático: o contrato <strong>{contrato['nome']}</strong> vencerá em aproximadamente 30 dias."
        else:
            tipo_design = 'info'
            titulo = assunto
            mensagem = mensagem_customizada or f"Notificação referente ao contrato <strong>{contrato['nome']}</strong>."
        
        # Criar template de email
        html_content = criar_template_email(
            assunto=assunto,
            titulo=titulo,
            mensagem=mensagem,
            tipo_notificacao=tipo_design,
            contrato=contrato
        )
        
        # Texto simples
        data_fim_formatada = formatar_data_brasil(contrato['data_fim'])
        texto_simples = f"""CONTRATO+ - {assunto}

{titulo}

{mensagem}

Contrato: {contrato['nome']}
Data de Término: {data_fim_formatada}
Status: {contrato['status']}

---
Esta é uma notificação automática do sistema CONTRATO+.
Acesse: http://localhost:5000"""
        
        # Enviar email
        enviado = enviar_email(emails_list, assunto, html_content, texto_simples)
        
        # Registrar no banco
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO notificacao (contrato_id, tipo, assunto, mensagem, email_destino, status, data_envio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            contrato_id,
            tipo,
            assunto,
            mensagem,
            ','.join(emails_list),
            'enviado' if enviado else 'erro',
            datetime.utcnow().isoformat() if enviado else None
        ))
        
        conn.commit()
        conn.close()
        
        if enviado:
            return jsonify({
                'success': True,
                'message': f'Notificação enviada para {len(emails_list)} email(s)',
                'enviados': len(emails_list)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao enviar notificação'
            }), 500
        
    except Exception as e:
        logger.error(f"Erro ao enviar notificação: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao enviar notificação: {str(e)}'}), 500

# ========== ROTAS DE DASHBOARD ==========
@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    try:
        usuario_id = session['usuario_id']
        conn = get_db_connection()
        
        # Total de contratos
        total_contratos = conn.execute(
            'SELECT COUNT(*) as total FROM contrato WHERE usuario_id = ?',
            (usuario_id,)
        ).fetchone()['total']
        
        # Contratos ativos
        contratos_ativos = conn.execute(
            'SELECT COUNT(*) as total FROM contrato WHERE usuario_id = ? AND status = "ativo"',
            (usuario_id,)
        ).fetchone()['total']
        
        # Contratos próximos do vencimento (30 dias)
        hoje = datetime.now().strftime('%Y-%m-%d')
        data_limite = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        contratos_proximos = conn.execute('''
            SELECT COUNT(*) as total 
            FROM contrato 
            WHERE usuario_id = ? 
            AND data_fim BETWEEN ? AND ?
            AND status = "ativo"
        ''', (usuario_id, hoje, data_limite)).fetchone()['total']
        
        # Contratos vencidos
        contratos_vencidos = conn.execute('''
            SELECT COUNT(*) as total 
            FROM contrato 
            WHERE usuario_id = ? 
            AND data_fim < ?
            AND status = "ativo"
        ''', (usuario_id, hoje)).fetchone()['total']
        
        # Últimas notificações
        ultimas_notificacoes = conn.execute('''
            SELECT n.*, c.nome as contrato_nome
            FROM notificacao n
            JOIN contrato c ON n.contrato_id = c.id
            WHERE c.usuario_id = ?
            ORDER BY n.criado_em DESC
            LIMIT 5
        ''', (usuario_id,)).fetchall()
        
        # Contratos por status
        status_data = []
        status_rows = conn.execute('''
            SELECT status, COUNT(*) as total 
            FROM contrato 
            WHERE usuario_id = ? 
            GROUP BY status
        ''', (usuario_id,)).fetchall()
        
        for row in status_rows:
            status_data.append({
                'status': row['status'],
                'total': row['total']
            })
        
        # Próximos vencimentos
        proximos_vencimentos = conn.execute('''
            SELECT id, nome, data_fim, status
            FROM contrato
            WHERE usuario_id = ?
            AND status = "ativo"
            AND data_fim >= ?
            ORDER BY data_fim
            LIMIT 5
        ''', (usuario_id, hoje)).fetchall()
        
        conn.close()
        
        # Processar dados
        notificacoes_json = []
        for notif in ultimas_notificacoes:
            notificacoes_json.append({
                'id': notif['id'],
                'contrato_nome': notif['contrato_nome'],
                'tipo': notif['tipo'],
                'assunto': notif['assunto'],
                'status': notif['status'],
                'data_envio': notif['data_envio'],
                'criado_em': notif['criado_em']
            })
        
        vencimentos_json = []
        for contrato in proximos_vencimentos:
            vencimentos_json.append({
                'id': contrato['id'],
                'nome': contrato['nome'],
                'data_fim': contrato['data_fim'],
                'status': contrato['status'],
                'dias_restantes': calcular_dias_restantes(contrato['data_fim'])
            })
        
        return jsonify({
            'success': True,
            'stats': {
                'total_contratos': total_contratos,
                'contratos_ativos': contratos_ativos,
                'contratos_proximos': contratos_proximos,
                'contratos_vencidos': contratos_vencidos,
                'status_distribuicao': status_data,
                'ultimas_notificacoes': notificacoes_json,
                'proximos_vencimentos': vencimentos_json,
                'atualizado_em': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao obter estatísticas'}), 500

# ========== ROTAS DE CONFIGURAÇÕES ==========
@app.route('/api/configuracoes/perfil', methods=['GET'])
@login_required
def get_perfil():
    try:
        usuario = get_usuario_atual()
        if not usuario:
            return jsonify({'success': False, 'message': 'Usuário não encontrado'}), 404
        
        return jsonify({
            'success': True,
            'perfil': {
                'id': usuario['id'],
                'nome_completo': usuario['nome_completo'],
                'email': usuario['email'],
                'criado_em': usuario['criado_em']
            }
        })
    except Exception as e:
        logger.error(f"Erro ao obter perfil: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao obter perfil'}), 500

@app.route('/api/configuracoes/perfil', methods=['PUT'])
@login_required
def atualizar_perfil():
    try:
        data = request.json
        usuario_id = session['usuario_id']
        
        conn = get_db_connection()
        
        updates = []
        params = []
        
        if 'nome_completo' in data:
            updates.append('nome_completo = ?')
            params.append(data['nome_completo'])
        
        if 'email' in data:
            # Verificar se email já existe
            if data['email'] != session['usuario_email']:
                existente = conn.execute(
                    'SELECT id FROM usuario WHERE email = ? AND id != ?',
                    (data['email'], usuario_id)
                ).fetchone()
                
                if existente:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Email já está em uso'}), 400
            
            updates.append('email = ?')
            params.append(data['email'])
        
        if 'senha_atual' in data and 'nova_senha' in data:
            usuario = conn.execute(
                'SELECT senha_hash FROM usuario WHERE id = ?',
                (usuario_id,)
            ).fetchone()
            
            if not verificar_senha(data['senha_atual'], usuario['senha_hash']):
                conn.close()
                return jsonify({'success': False, 'message': 'Senha atual incorreta'}), 400
            
            updates.append('senha_hash = ?')
            params.append(hash_senha(data['nova_senha']))
        
        if updates:
            query = f'UPDATE usuario SET {", ".join(updates)} WHERE id = ?'
            params.append(usuario_id)
            
            conn.execute(query, params)
            conn.commit()
            
            # Atualizar sessão se email mudou
            if 'email' in data:
                session['usuario_email'] = data['email']
            if 'nome_completo' in data:
                session['usuario_nome'] = data['nome_completo']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Perfil atualizado com sucesso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao atualizar perfil'}), 500

# ========== ROTAS DE TESTE DE EMAIL ==========
@app.route('/api/email/test', methods=['POST'])
@login_required
def testar_email():
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email é obrigatório'}), 400
        
        # Criar template de teste
        html_content = criar_template_email(
            assunto='Teste de Email - CONTRATO+',
            titulo='✅ Teste de Conexão Bem-sucedido!',
            mensagem=f'Se você está lendo esta mensagem, o sistema de notificações do <strong>CONTRATO+</strong> está funcionando perfeitamente!<br><br>Este email foi enviado para: <strong>{email}</strong><br>Data/Hora: <strong>{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</strong>',
            tipo_notificacao='teste'
        )
        
        texto_simples = f"""Teste de Email - CONTRATO+

✅ Teste de Conexão Bem-sucedido!

Se você está lendo esta mensagem, o sistema de notificações do CONTRATO+ está funcionando perfeitamente!

Email de teste enviado para: {email}
Data/Hora: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

---
Esta é uma mensagem de teste automática."""
        
        enviado = enviar_email([email], 'Teste de Email - CONTRATO+', html_content, texto_simples)
        
        if enviado:
            return jsonify({
                'success': True,
                'message': 'Email de teste enviado com sucesso!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao enviar email de teste'
            }), 500
        
    except Exception as e:
        logger.error(f"Erro ao testar email: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro ao testar email: {str(e)}'}), 500

# ========== ROTAS DE UTILITÁRIOS ==========
@app.route('/api/utils/calcular-dias/<data_fim>', methods=['GET'])
@login_required
def calcular_dias_api(data_fim):
    try:
        dias = calcular_dias_restantes(data_fim)
        return jsonify({
            'success': True,
            'dias_restantes': dias
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao calcular dias: {str(e)}'
        }), 500

def calcular_dias_restantes(data_fim):
    """Calcula dias restantes até a data de fim"""
    try:
        if isinstance(data_fim, str):
            data_fim_obj = datetime.fromisoformat(data_fim.replace('Z', '+00:00'))
        else:
            data_fim_obj = data_fim
        
        hoje = datetime.utcnow()
        diferenca = data_fim_obj - hoje
        return max(0, diferenca.days)
    except:
        return None

@app.route('/api/utils/verificar-email/<email>', methods=['GET'])
@login_required
def verificar_email_disponivel(email):
    try:
        conn = get_db_connection()
        
        # Verificar se email já está em uso por outro usuário
        usuario = conn.execute(
            'SELECT id FROM usuario WHERE email = ? AND id != ?',
            (email, session['usuario_id'])
        ).fetchone()
        
        conn.close()
        
        disponivel = usuario is None
        return jsonify({
            'success': True,
            'disponivel': disponivel,
            'message': 'Email disponível' if disponivel else 'Email já está em uso'
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar email: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao verificar email'}), 500

# ========== ROTA DE VERIFICAÇÃO DO SISTEMA ==========
@app.route('/api/system/health', methods=['GET'])
def health_check():
    """Verifica a saúde do sistema"""
    try:
        # Verificar banco de dados
        if not os.path.exists(DATABASE):
            return jsonify({
                'status': 'error',
                'database': 'not_found',
                'message': 'Banco de dados não encontrado'
            }), 500
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = [row[0] for row in cursor.fetchall()]
        
        tabelas_esperadas = ['usuario', 'contrato', 'notificacao']
        tabelas_faltando = [t for t in tabelas_esperadas if t not in tabelas]
        
        conn.close()
        
        # Verificar sessão
        sessao_ativa = 'usuario_id' in session
        
        return jsonify({
            'status': 'healthy' if not tabelas_faltando else 'warning',
            'database': {
                'existe': True,
                'tabelas': tabelas,
                'tabelas_faltando': tabelas_faltando
            },
            'session': {
                'ativa': sessao_ativa,
                'usuario_id': session.get('usuario_id'),
                'usuario_nome': session.get('usuario_nome')
            },
            'timestamp': datetime.now().isoformat(),
            'message': 'Sistema operacional' if not tabelas_faltando else 'Algumas tabelas estão faltando'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro na verificação: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }), 500

# ========== MIDDLEWARE PARA LOG ==========
@app.before_request
def log_request_info():
    if request.path.startswith('/api/'):
        logger.info(f"{request.method} {request.path}")

# ========== MAIN ==========

# Garante que o banco e as tabelas existam ao iniciar (não altera design, só faz o sistema funcionar)
try:
    os.makedirs(DATA_DIR, exist_ok=True)
    criar_tabelas()
except Exception as e:
    logger.exception('Falha ao inicializar banco: %s', e)

# =========================
# ALIASES / ROTAS COMPATÍVEIS COM O FRONT (HTML PURO)
# =========================

# Alguns HTMLs usam endpoints alternativos. Estas rotas apenas redirecionam/duplicam respostas
# para manter seu design e JS originais funcionando.

@app.route('/api/logout', methods=['POST','GET'])
def api_logout_alias():
    # Aceita GET/POST (algumas páginas chamam /logout)
    try:
        session.clear()
        return jsonify({'success': True, 'message': 'Logout realizado'})
    except Exception:
        session.clear()
        return jsonify({'success': True})

@app.route('/api/health', methods=['GET'])
def api_health_alias():
    return health_check()

@app.route('/api/notificacoes/count', methods=['GET'])
@login_required
def api_notificacoes_count():
    conn = get_db_connection()
    usuario_id = session['usuario_id']
    
    # Correção: contar notificações dos contratos do usuário
    total = conn.execute('''
        SELECT COUNT(*) as c 
        FROM notificacao n
        JOIN contrato c ON n.contrato_id = c.id
        WHERE c.usuario_id = ?
    ''', (usuario_id,)).fetchone()['c']
    conn.close()
    return jsonify({'success': True, 'count': total})

@app.route('/api/notificacoes/recentes', methods=['GET'])
@login_required
def api_notificacoes_recentes():
    try:
        usuario_id = session['usuario_id']
        conn = get_db_connection()
        rows = conn.execute('''
            SELECT n.*, c.nome as contrato_nome
            FROM notificacao n
            JOIN contrato c ON n.contrato_id = c.id
            WHERE c.usuario_id = ?
            ORDER BY n.criado_em DESC
            LIMIT 5
        ''', (usuario_id,)).fetchall()
        conn.close()
        
        items = []
        for r in rows:
            items.append({
                'id': r['id'],
                'contrato_id': r['contrato_id'],
                'contrato_nome': r['contrato_nome'],
                'tipo': r['tipo'],
                'assunto': r['assunto'],
                'mensagem': r['mensagem'],
                'email_destino': r['email_destino'],
                'status': r['status'],
                'data_envio': r['data_envio'],
                'criado_em': r['criado_em']
            })
        return jsonify({'success': True, 'notificacoes': items})
    except Exception as e:
        logger.error(f"Erro em notificacoes/recentes: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao carregar notificações'}), 500

@app.route('/api/contratos/recentes', methods=['GET'])
@login_required
def api_contratos_recentes():
    try:
        usuario_id = session['usuario_id']
        conn = get_db_connection()
        rows = conn.execute('''
            SELECT * FROM contrato
            WHERE usuario_id = ?
            ORDER BY criado_em DESC
            LIMIT 5
        ''', (usuario_id,)).fetchall()
        conn.close()
        
        contratos = []
        for r in rows:
            contratos.append({
                'id': r['id'],
                'nome': r['nome'],
                'descricao': r['descricao'],
                'data_inicio': r['data_inicio'],
                'data_fim': r['data_fim'],
                'status': r['status'],
                'criado_em': r['criado_em'],
                'atualizado_em': r['atualizado_em']
            })
        return jsonify({'success': True, 'contratos': contratos})
    except Exception as e:
        logger.error(f"Erro em contratos/recentes: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao carregar contratos'}), 500

@app.route('/api/notificacoes/limpar', methods=['POST','DELETE'])
@login_required
def api_notificacoes_limpar():
    try:
        usuario_id = session['usuario_id']
        conn = get_db_connection()
        
        # Deletar notificações dos contratos do usuário
        conn.execute('''
            DELETE FROM notificacao 
            WHERE contrato_id IN (
                SELECT id FROM contrato WHERE usuario_id = ?
            )
        ''', (usuario_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Notificações removidas'})
    except Exception as e:
        logger.error(f"Erro ao limpar notificações: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao limpar notificações'}), 500

@app.route('/api/contratos/limpar', methods=['POST','DELETE'])
@login_required
def api_contratos_limpar():
    try:
        usuario_id = session['usuario_id']
        conn = get_db_connection()
        
        # Primeiro deletar notificações dos contratos do usuário
        conn.execute('''
            DELETE FROM notificacao 
            WHERE contrato_id IN (
                SELECT id FROM contrato WHERE usuario_id = ?
            )
        ''', (usuario_id,))
        
        # Depois deletar os contratos
        conn.execute('DELETE FROM contrato WHERE usuario_id = ?', (usuario_id,))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Contratos removidos'})
    except Exception as e:
        logger.error(f"Erro ao limpar contratos: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao limpar contratos'}), 500

@app.route('/api/sistema/reset', methods=['POST'])
@login_required
def api_sistema_reset():
    # reset leve: limpa contratos/notificações do usuário
    return api_contratos_limpar()

@app.route('/api/test-email', methods=['GET'])
def api_test_email_alias():
    # compatibilidade: retorna instruções simples
    return jsonify({'success': True, 'message': 'Use POST /api/email/test para enviar e-mail de teste'})

@app.route('/api/test-email/send-test', methods=['POST'])
@login_required
def api_test_email_send():
    # compatibilidade: reaproveita /api/email/test
    return testar_email()

# ========== ROTAS ADICIONAIS PARA O DASHBOARD ==========
@app.route('/api/dashboard/contratos-vencendo', methods=['GET'])
@login_required
def get_contratos_vencendo():
    try:
        usuario_id = session['usuario_id']
        hoje = datetime.now().strftime('%Y-%m-%d')
        data_limite = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        total = conn.execute('''
            SELECT COUNT(*) as total 
            FROM contrato 
            WHERE usuario_id = ? 
            AND data_fim BETWEEN ? AND ?
            AND status = "ativo"
        ''', (usuario_id, hoje, data_limite)).fetchone()['total']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total': total
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter contratos vencendo: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao obter contratos vencendo'}), 500

@app.route('/api/dashboard/destinatarios-ativos', methods=['GET'])
@login_required
def get_destinatarios_ativos():
    try:
        usuario_id = session['usuario_id']
        
        conn = get_db_connection()
        
        # Contar emails únicos de notificações dos contratos do usuário
        total = conn.execute('''
            SELECT COUNT(DISTINCT email_destino) as total
            FROM notificacao n
            JOIN contrato c ON n.contrato_id = c.id
            WHERE c.usuario_id = ?
        ''', (usuario_id,)).fetchone()['total']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total': total
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter destinatários ativos: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao obter destinatários ativos'}), 500

@app.route('/api/contratos/<int:id>/status', methods=['PUT'])
@login_required
def atualizar_status_contrato(id):
    try:
        usuario_id = session['usuario_id']
        data = request.json
        novo_status = data.get('status')
        
        if not novo_status:
            return jsonify({'success': False, 'message': 'Status é obrigatório'}), 400
        
        conn = get_db_connection()
        
        # Verificar se o contrato pertence ao usuário
        contrato = conn.execute(
            'SELECT * FROM contrato WHERE id = ? AND usuario_id = ?',
            (id, usuario_id)
        ).fetchone()
        
        if not contrato:
            conn.close()
            return jsonify({'success': False, 'message': 'Contrato não encontrado'}), 404
        
        # Atualizar status
        conn.execute(
            'UPDATE contrato SET status = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?',
            (novo_status, id)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Status do contrato atualizado para {novo_status}'
        })
        
    except Exception as e:
        logger.error(f"Erro ao atualizar status: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao atualizar status'}), 500

if __name__ == '__main__':
    verificar_banco_dados()
    
    print("=" * 60)
    print("CONTRATO+ - Sistema de Gerenciamento de Contratos")
    print("=" * 60)
    print("🌐 Servidor iniciado em: http://localhost:5000")
    print("📧 Email de teste configurado")
    print("=" * 60)
    print("📊 APIs Disponíveis:")
    print("  🔐 Autenticação:")
    print("    POST   /api/auth/login")
    print("    POST   /api/auth/register")
    print("    POST   /api/auth/logout")
    print("    GET    /api/auth/check")
    print("")
    print("  📄 Contratos:")
    print("    GET    /api/contratos")
    print("    POST   /api/contratos")
    print("    GET    /api/contratos/{id}")
    print("    PUT    /api/contratos/{id}")
    print("    DELETE /api/contratos/{id}")
    print("    PUT    /api/contratos/{id}/status")
    print("")
    print("  🔔 Notificações:")
    print("    GET    /api/notificacoes")
    print("    POST   /api/contratos/{id}/notificar")
    print("    GET    /api/notificacoes/recentes")
    print("    GET    /api/notificacoes/count")
    print("")
    print("  📊 Dashboard:")
    print("    GET    /api/dashboard/stats")
    print("    GET    /api/contratos/recentes")
    print("    GET    /api/dashboard/contratos-vencendo")
    print("    GET    /api/dashboard/destinatarios-ativos")
    print("")
    print("  ⚙️ Configurações:")
    print("    GET    /api/configuracoes/perfil")
    print("    PUT    /api/configuracoes/perfil")
    print("")
    print("  🧪 Testes:")
    print("    POST   /api/email/test")
    print("    GET    /api/system/health")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)