from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, abort
)
from zeep import Client, Settings, Transport
from zeep.exceptions import Fault, TransportError
import requests 
import os
from datetime import datetime 


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "default_secret_key_for_dev") 


@app.context_processor
def inject_now():
    """Injecta a função datetime.utcnow no contexto do template."""
    return {'now': datetime.utcnow}



WSDL_WS1 = os.environ.get('WSDL_WS1_URL', 'http://localhost:5001/ws1?wsdl') 
WSDL_WS2 = os.environ.get('WSDL_WS2_URL', 'http://localhost:5002/ws2?wsdl')

# --- Configuração do Cliente SOAP (Zeep) ---

http_session = requests.Session()
settings = Settings(strict=False, xml_huge_tree=True)
transport = Transport(session=http_session, timeout=10) 

client_ws1 = None
client_ws2 = None

try:
    client_ws1 = Client(WSDL_WS1, settings=settings, transport=transport)
    print("Cliente WS1 conectado.")
except Exception as e:
    print(f"ERRO ao conectar ao WSDL WS1 ({WSDL_WS1}): {e}")

try:
    client_ws2 = Client(WSDL_WS2, settings=settings, transport=transport)
    print("Cliente WS2 conectado.")
except Exception as e:
    print(f"ERRO ao conectar ao WSDL WS2 ({WSDL_WS2}): {e}")


# --- Decorador para verificar login ---
from functools import wraps

def login_required(role="client"):
    """Verifica se o utilizador está logado e tem o role correto."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Login necessário para aceder a esta página.', 'warning')
                return redirect(url_for('login', next=request.url))
            if session.get('role') != role and role != "any": 
                 flash(f'Acesso não autorizado. Role necessário: {role}.', 'danger')
                 return redirect(url_for('index')) 
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Rotas ---
@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('client_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: return redirect(url_for('index')) 

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not client_ws1:
             flash('Erro crítico: Serviço de autenticação indisponível.', 'danger')
             return render_template('login.html')
        if not username or not password:
             flash('Utilizador e password são obrigatórios.', 'warning')
             return render_template('login.html')

        try:
            user_info = client_ws1.service.login(username=username, password=password)

            if user_info and user_info.user_id:
                 session['user_id'] = user_info.user_id
                 session['username'] = user_info.username 
                 session['role'] = user_info.role
                 flash(f'Login bem sucedido como {user_info.role}!', 'success')

                 next_page = request.args.get('next')
                 return redirect(next_page or url_for('index'))
            else:
                 flash('Resposta inesperada do serviço de login.', 'danger')

        except Fault as f: 
            flash(f"Erro: {f.message}", 'danger')
        except TransportError as te:
             print(f"Erro de transporte ao contactar WS1: {te}")
             flash('Erro de comunicação com o serviço de autenticação.', 'danger')
        except Exception as e:
            print(f"Erro inesperado no login: {type(e).__name__} - {e}")
            flash('Ocorreu um erro inesperado durante o login.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session: return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        email = request.form.get('email')

        if not client_ws1:
             flash('Erro crítico: Serviço de registo indisponível.', 'danger')
             return render_template('register.html')

        error = None
        if not username: error = 'Username é obrigatório.'
        elif not password: error = 'Password é obrigatória.'
        elif password != confirm_password: error = 'Passwords não coincidem.'
        elif not email: error = 'Email é obrigatório.'

        if error:
             flash(error, 'warning')
        else:
            try:
                success = client_ws1.service.register(username=username, password=password, email=email)
                if success:
                    flash('Registo bem sucedido! Pode agora fazer login.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash('Erro desconhecido no registo.', 'danger')
            except Fault as f:
                flash(f"Erro no registo: {f.message}", 'danger')
            except TransportError as te:
                 print(f"Erro de transporte ao contactar WS1: {te}")
                 flash('Erro de comunicação com o serviço de registo.', 'danger')
            except Exception as e:
                print(f"Erro inesperado no registo: {type(e).__name__} - {e}")
                flash('Ocorreu um erro inesperado durante o registo.', 'danger')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    flash('Logout bem sucedido.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard/client')
@login_required(role="client")
def client_dashboard():
    packages = []
    if not client_ws1:
        flash('Erro crítico: Serviço de pacotes indisponível.', 'danger')
    else:
        try:
            user_id = session['user_id']
            search_term = request.args.get('search', '') 

            if search_term:
                 packages_data = client_ws1.service.searchPackages(user_id=user_id, search_term=search_term)
                 flash(f'Mostrando resultados para "{search_term}".', 'info')
            else:
                 packages_data = client_ws1.service.listPackages(user_id=user_id)

            packages = packages_data if packages_data else []

        except Fault as f:
            flash(f"Erro ao buscar pacotes: {f.message}", 'danger')
        except TransportError as te:
             print(f"Erro de transporte ao contactar WS1: {te}")
             flash('Erro de comunicação com o serviço de pacotes.', 'danger')
        except Exception as e:
            print(f"Erro inesperado no client dashboard: {type(e).__name__} - {e}")
            flash('Ocorreu um erro inesperado ao carregar os seus pacotes.', 'danger')

    return render_template('client_dashboard.html', packages=packages)


@app.route('/package/<int:package_id>')
@login_required(role="any")
def package_details(package_id):
    package_info = None
    tracking_history = []
    error_msg = None

    if not client_ws1:
         error_msg = 'Erro crítico: Serviço de pacotes indisponível.'
    else:
        try:
            user_id = session['user_id']
            all_packages = client_ws1.service.listPackages(user_id=user_id) or []
            found = False
            for pkg in all_packages:
                 if pkg.id == package_id:
                      package_info = pkg
                      found = True
                      break
            if not found:
                 abort(404, description="Pacote não encontrado ou não pertence a si.")

            if package_info and package_info.is_tracked:
                tracking_history = client_ws1.service.checkStatus(package_id=package_id) or []

        except Fault as f:
            error_msg = f"Erro ao buscar detalhes do pacote: {f.message}"
        except TransportError as te:
             error_msg = 'Erro de comunicação com o serviço de pacotes.'
             print(f"Erro de transporte ao contactar WS1: {te}")
        except Exception as e:
            error_msg = 'Ocorreu um erro inesperado.'
            print(f"Erro inesperado em package_details: {type(e).__name__} - {e}")

    if error_msg: flash(error_msg, 'danger')

    return render_template('package_details.html', 
                            package=package_info,
                            tracking_history=tracking_history)


@app.route('/dashboard/admin')
@login_required(role="admin")
def admin_dashboard():
    packages = []
    if not client_ws2:
         flash('Erro crítico: Serviço de administração indisponível.', 'danger')
    else:
        try:
             packages_data = client_ws2.service.getAllPackages()
             packages = packages_data if packages_data else []
        except Fault as f:
            flash(f"Erro ao buscar pacotes: {f.message}", 'danger')
        except TransportError as te:
             print(f"Erro de transporte ao contactar WS2: {te}")
             flash('Erro de comunicação com o serviço de administração.', 'danger')
        except Exception as e:
            print(f"Erro inesperado no admin dashboard: {type(e).__name__} - {e}")
            flash('Ocorreu um erro inesperado ao carregar os pacotes.', 'danger')

    return render_template('admin_dashboard.html', packages=packages)

@app.route('/admin/package/add', methods=['GET', 'POST'])
@login_required(role="admin")
def add_package():
    users = []
    if client_ws2:
        try:
             users_data = client_ws2.service.getAllUsers()
             users = users_data if users_data else []
        except Exception as e:
             flash('Erro ao carregar lista de utilizadores.', 'warning')
             print(f"Erro getAllUsers: {e}")

    if request.method == 'POST':
        if not client_ws2:
             flash('Erro crítico: Serviço de administração indisponível.', 'danger')
             return render_template('add_package.html', users=users)

        try:
            sender_id = int(request.form.get('sender_id'))
            receiver_id = int(request.form.get('receiver_id'))
            name = request.form.get('name')
            description = request.form.get('description')
            sender_city = request.form.get('sender_city')
            destination_city = request.form.get('destination_city')

            if not all([sender_id, receiver_id, name, sender_city, destination_city]):
                 flash('Todos os campos obrigatórios devem ser preenchidos.', 'warning')
            else:
                new_id = client_ws2.service.addPackage(
                    sender_id=sender_id, receiver_id=receiver_id, name=name,
                    description=description, sender_city=sender_city, destination_city=destination_city
                )
                if new_id:
                    flash(f'Pacote "{name}" adicionado com sucesso (ID: {new_id}).', 'success')
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash('Falha ao adicionar pacote (resposta inesperada do serviço).', 'danger')

        except ValueError:
             flash('IDs de remetente/destinatário inválidos.', 'warning')
        except Fault as f:
            flash(f"Erro ao adicionar pacote: {f.message}", 'danger')
        except TransportError as te:
             print(f"Erro de transporte ao contactar WS2: {te}")
             flash('Erro de comunicação com o serviço de administração.', 'danger')
        except Exception as e:
            print(f"Erro inesperado em add_package: {type(e).__name__} - {e}")
            flash('Ocorreu um erro inesperado ao adicionar o pacote.', 'danger')

    return render_template('add_package.html', users=users) # Criar este template

@app.route('/admin/package/delete/<int:package_id>', methods=['POST'])
@login_required(role="admin")
def delete_package(package_id):
    if not client_ws2:
        flash('Erro crítico: Serviço de administração indisponível.', 'danger')
    else:
        try:
             success = client_ws2.service.removePackage(package_id=package_id)
             if success:
                  flash(f'Pacote {package_id} removido com sucesso.', 'success')
             else:
                  flash(f'Falha ao remover pacote {package_id} (resposta inesperada).', 'warning')
        except Fault as f:
             flash(f"Erro ao remover pacote: {f.message}", 'danger')
        except TransportError as te:
             print(f"Erro de transporte ao contactar WS2: {te}")
             flash('Erro de comunicação com o serviço de administração.', 'danger')
        except Exception as e:
            print(f"Erro inesperado em delete_package: {type(e).__name__} - {e}")
            flash('Ocorreu um erro inesperado ao remover o pacote.', 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/package/register_track/<int:package_id>', methods=['POST'])
@login_required(role="admin")
def register_track(package_id):
     if not client_ws2:
        flash('Erro crítico: Serviço de administração indisponível.', 'danger')
     else:
        try:
            city = request.form.get('initial_city')
            timestamp = datetime.utcnow() 

            if not city:
                 flash('Cidade inicial é obrigatória para registar rastreio.', 'warning')
            else:
                success = client_ws2.service.registerPackageTracking(
                    package_id=package_id,
                    initial_city=city,
                    initial_time=timestamp 
                )
                if success:
                    flash(f'Rastreio registado para pacote {package_id} a partir de {city}.', 'success')
                else:
                    flash('Falha ao registar rastreio (resposta inesperada).', 'warning')
        except Fault as f:
             flash(f"Erro ao registar rastreio: {f.message}", 'danger')
        except TransportError as te:
             flash('Erro de comunicação com o serviço de administração.', 'danger')
        except Exception as e:
            flash('Ocorreu um erro inesperado.', 'danger')

     return redirect(url_for('admin_dashboard')) 

@app.route('/admin/package/update_status/<int:package_id>', methods=['POST'])
@login_required(role="admin")
def update_status(package_id):
    if not client_ws2:
        flash('Erro crítico: Serviço de administração indisponível.', 'danger')
    else:
        try:
            city = request.form.get('city')
            timestamp = datetime.utcnow() 

            if not city:
                 flash('Cidade é obrigatória para atualizar estado.', 'warning')
            else:
                success = client_ws2.service.updatePackageStatus(
                    package_id=package_id,
                    city=city,
                    time=timestamp
                )
                if success:
                    flash(f'Estado do pacote {package_id} atualizado: Chegou a {city}.', 'success')
                else:
                    flash('Falha ao atualizar estado (resposta inesperada).', 'warning')
        except Fault as f:
             flash(f"Erro ao atualizar estado: {f.message}", 'danger')
        except TransportError as te:
             flash('Erro de comunicação com o serviço de administração.', 'danger')
        except Exception as e:
            flash('Ocorreu um erro inesperado.', 'danger')

  
    return redirect(url_for('admin_dashboard'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404 

@app.errorhandler(500)
def internal_server_error(e):
    print(f"Internal Server Error: {e}") 
    return render_template('500.html'), 500 

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
    