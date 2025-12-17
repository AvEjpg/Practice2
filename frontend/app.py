from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import requests as http
import io
from functools import wraps
import logging
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey123!@#"
app.config['BOOTSTRAP_SERVE_LOCAL'] = True

API_URL = "http://127.0.0.1:8000"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "token" not in session or "role" not in session:
            flash("Для доступа к этой странице необходимо войти в систему", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "token" not in session or "role" not in session:
                flash("Для доступа к этой странице необходимо войти в систему", "warning")
                return redirect(url_for('login'))
            if session.get("role") not in roles:
                flash("У вас недостаточно прав для доступа к этой странице", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_headers():
    token = session.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}

def make_api_request(method, endpoint, **kwargs):
    try:
        url = f"{API_URL}{endpoint}"
        headers = kwargs.get('headers', {})
        
        if "token" in session:
            token = session.get("token")
            headers["Authorization"] = f"Bearer {token}"
            kwargs['headers'] = headers
        
        logger.debug(f"Making {method} request to {url}")
        
        if method == 'GET':
            response = http.get(url, **kwargs)
        elif method == 'POST':
            response = http.post(url, **kwargs)
        elif method == 'PUT':
            response = http.put(url, **kwargs)
        elif method == 'DELETE':
            response = http.delete(url, **kwargs)
        else:
            return None, "Неверный метод запроса"
        
        logger.debug(f"API Response: {response.status_code}")
        if response.status_code in [200, 201]:
            return response, None
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", "Неизвестная ошибка")
            except:
                error_msg = f"Ошибка {response.status_code}"
            
            if response.status_code == 401:
                session.clear()
                flash("Сессия истекла. Пожалуйста, войдите снова.", "warning")
            
            return response, error_msg
    except Exception as e:
        logger.error(f"API request error: {e}")
        return None, f"Ошибка подключения к серверу: {str(e)}"

@app.route("/")
def index():
    """Главная страница"""
    stats = None
    if session.get("token"):
        try:
            if session.get("role") == "Заказчик":
                # Для заказчиков - получаем список заявок и считаем вручную
                response, error = make_api_request('GET', '/client/my-requests', headers=api_headers())
                if error is None and response:
                    requests = response.json()
                    total = len(requests)
                    completed = sum(1 for r in requests if r.get('completion_date') is not None)
                    
                    # Подсчет по типам оборудования
                    tech_counts = {}
                    for r in requests:
                        tech_type = r.get('climate_tech_type', 'Неизвестно')
                        tech_counts[tech_type] = tech_counts.get(tech_type, 0) + 1
                    
                    by_tech = [{"tech_type": k, "count": v} for k, v in tech_counts.items()]
                    
                    count_stats = {
                        "total_requests": total,
                        "completed_requests": completed
                    }
                    
                    # Простое среднее время (если есть завершенные заявки)
                    completed_requests = [r for r in requests if r.get('completion_date')]
                    if completed_requests:
                        total_days = 0
                        count = 0
                        for r in completed_requests:
                            if r.get('start_date') and r.get('completion_date'):
                                try:
                                    start = datetime.strptime(r['start_date'], '%Y-%m-%d')
                                    end = datetime.strptime(r['completion_date'], '%Y-%m-%d')
                                    days = (end - start).days
                                    total_days += days
                                    count += 1
                                except:
                                    pass
                        avg_days = total_days / count if count > 0 else 0
                    else:
                        avg_days = 0
                    
                    avg_time = {"avg_repair_days": round(avg_days, 1)}
                    by_problem = []
                    
                else:
                    count_stats = {"total_requests": 0, "completed_requests": 0}
                    avg_time = {"avg_repair_days": 0}
                    by_tech = []
                    by_problem = []
            
            else:
                # Для сотрудников - стандартные эндпоинты
                response, error = make_api_request('GET', '/requests/stats/count', headers=api_headers())
                if error is None and response:
                    count_stats = response.json()
                else:
                    count_stats = {"total_requests": 0, "completed_requests": 0}
                
                response, error = make_api_request('GET', '/requests/stats/avg-time', headers=api_headers())
                if error is None and response:
                    avg_time = response.json()
                else:
                    avg_time = {"avg_repair_days": 0}
                
                response, error = make_api_request('GET', '/requests/stats/by-tech', headers=api_headers())
                if error is None and response:
                    by_tech = response.json()
                else:
                    by_tech = []
                
                response, error = make_api_request('GET', '/requests/stats/by-problem-type', headers=api_headers())
                if error is None and response:
                    by_problem = response.json()
                else:
                    by_problem = []
            
            stats = {
                'count': count_stats,
                'avg': avg_time,
                'by_tech': by_tech,
                'by_problem': by_problem
            }
            
        except Exception as e:
            logger.error(f"Error loading stats: {e}")
            stats = {
                'count': {"total_requests": 0, "completed_requests": 0},
                'avg': {"avg_repair_days": 0},
                'by_tech': [],
                'by_problem': []
            }
    
    return render_template("index.html", 
                         role=session.get("role"), 
                         stats=stats,
                         title="Главная - Система учета заявок")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = {
            "login": request.form["login"],
            "password": request.form["password"]
        }
        
        response, error = make_api_request('POST', '/auth/login', json=data)
        
        if error is None and response:
            payload = response.json()
            session["token"] = payload.get("access_token")
            session["role"] = payload.get("role", "Оператор")
            
            # Получаем user_id из токена
            token = payload.get("access_token")
            if token:
                try:
                    # Декодируем JWT токен чтобы получить user_id
                    import jwt
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    session["user_id"] = decoded.get("sub")
                    print(f"User ID from token: {session['user_id']}")  # Для отладки
                except Exception as e:
                    print(f"Error decoding token: {e}")
                    # Если не получается декодировать, пробуем получить user_id другим способом
                    session["user_id"] = payload.get("user_id", "unknown")
            
            flash("Вход выполнен успешно!", "success")
            return redirect(url_for("index"))
        else:
            flash(error or "Неверный логин или пароль", "danger")
    
    return render_template("auth/login.html", title="Вход в систему")

@app.route("/logout")
def logout():
    session.clear()
    flash("Вы успешно вышли из системы", "info")
    return redirect(url_for("index"))

@app.route("/users")
@login_required
@role_required("Менеджер", "Менеджер по качеству")
def users_list():
    response, error = make_api_request('GET', '/users/', headers=api_headers())
    
    if error is None and response:
        users = response.json()
    else:
        users = []
        flash(error or "Ошибка загрузки пользователей", "danger")
    
    return render_template("users/list.html", 
                         users=users, 
                         role=session.get("role"),
                         title="Управление пользователями")

@app.route("/users/create", methods=["GET", "POST"])
@login_required
@role_required("Менеджер")
def create_user():
    if request.method == "POST":
        user_data = {
            "fio": request.form["fio"],
            "phone": request.form["phone"],
            "login": request.form["login"],
            "password": request.form["password"],
            "user_type": request.form["user_type"],
        }
        
        response, error = make_api_request('POST', '/users/', json=user_data, headers=api_headers())
        
        if error is None and response:
            flash("Пользователь успешно создан!", "success")
            return redirect(url_for("users_list"))
        else:
            flash(error or "Ошибка создания пользователя", "danger")
    
    return render_template("users/create.html", 
                         role=session.get("role"),
                         title="Создание пользователя")

@app.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
@role_required("Менеджер")
def delete_user(user_id):
    if request.form.get("confirm") != "yes":
        flash("Удаление отменено", "warning")
        return redirect(url_for("users_list"))
    
    response, error = make_api_request('DELETE', f'/users/{user_id}', headers=api_headers())
    
    if error is None and response:
        flash("Пользователь успешно удалён", "success")
    else:
        flash(error or "Ошибка удаления пользователя", "danger")
    
    return redirect(url_for("users_list"))

@app.route("/requests")
@login_required
@role_required("Оператор", "Специалист", "Менеджер", "Менеджер по качеству")
def requests_list():
    response, error = make_api_request('GET', '/requests/', headers=api_headers())
    
    if error is None and response:
        requests_data = response.json()
    else:
        requests_data = []
        if error:
            flash(error, "danger")
    
    return render_template("requests/list.html", 
                         requests=requests_data, 
                         role=session.get("role"),
                         title="Список заявок")

@app.route("/requests/search")
@login_required
@role_required("Оператор", "Специалист", "Менеджер", "Менеджер по качеству")
def search_requests():
    params = {k: v for k, v in request.args.items() if v}
    response, error = make_api_request('GET', '/requests/search', params=params, headers=api_headers())
    
    if error is None and response:
        requests_data = response.json()
        if not requests_data:
            flash("Поиск не дал результатов", "info")
    else:
        requests_data = []
        if error and "404" not in error:
            flash(error, "warning")
    
    return render_template("requests/list.html", 
                         requests=requests_data, 
                         role=session.get("role"),
                         search_params=params,
                         title="Результаты поиска")

@app.route("/requests/new", methods=["GET", "POST"])
@login_required
@role_required("Оператор", "Специалист", "Менеджер")
def new_request():
    if request.method == "POST":
        data = {
            "start_date": request.form["start_date"],
            "climate_tech_type": request.form["climate_tech_type"],
            "climate_tech_model": request.form["climate_tech_model"],
            "problem_description": request.form["problem_description"],
            "request_status": "Новая заявка",
            "client_id": int(request.form["client_id"]),
        }
        
        response, error = make_api_request('POST', '/requests/', json=data, headers=api_headers())
        
        if error is None and response:
            flash("Заявка успешно создана!", "success")
            return redirect(url_for("requests_list"))
        else:
            flash(error or "Ошибка создания заявки", "danger")
    
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("requests/create.html", 
                         role=session.get("role"),
                         today=today,
                         title="Создание новой заявки")

@app.route("/requests/<int:request_id>")
@login_required
@role_required("Оператор", "Специалист", "Менеджер", "Менеджер по качеству")
def request_detail(request_id):
    response, error = make_api_request('GET', f'/requests/{request_id}', headers=api_headers())
    
    if error is None and response:
        request_data = response.json()
        
        comments_response, comments_error = make_api_request('GET', '/comments/', headers=api_headers())
        if comments_error is None and comments_response:
            all_comments = comments_response.json()
            request_comments = [c for c in all_comments if c.get('request_id') == request_id]
        else:
            request_comments = []
        
        return render_template("requests/detail.html", 
                             r=request_data, 
                             comments=request_comments,
                             role=session.get("role"),
                             title=f"Заявка #{request_id}")
    else:
        flash(error or "Заявка не найдена", "danger")
        return redirect(url_for("requests_list"))

@app.route("/requests/<int:request_id>/edit", methods=["POST"])
@login_required
@role_required("Оператор", "Специалист", "Менеджер", "Менеджер по качеству")
def edit_request(request_id):
    update_data = {}
    if request.form.get("request_status"):
        update_data["request_status"] = request.form["request_status"]
    if request.form.get("completion_date"):
        update_data["completion_date"] = request.form["completion_date"]
    if request.form.get("repair_parts"):
        update_data["repair_parts"] = request.form["repair_parts"]
    if request.form.get("master_id"):
        update_data["master_id"] = int(request.form["master_id"])
    
    if update_data:
        response, error = make_api_request('PUT', f'/requests/{request_id}', json=update_data, headers=api_headers())
        
        if error is None and response:
            flash("Заявка успешно обновлена!", "success")
        else:
            flash(error or "Ошибка обновления заявки", "danger")
    
    return redirect(url_for("request_detail", request_id=request_id))

@app.route("/requests/<int:request_id>/assign", methods=["POST"])
@login_required
@role_required("Менеджер", "Менеджер по качеству")
def assign_specialist(request_id):
    data = {"master_id": int(request.form["master_id"])}
    
    response, error = make_api_request('POST', f'/requests/{request_id}/assign', json=data, headers=api_headers())
    
    if error is None and response:
        flash("Специалист успешно назначен!", "success")
    else:
        flash(error or "Ошибка назначения специалиста", "danger")
    
    return redirect(url_for("request_detail", request_id=request_id))

@app.route("/requests/<int:request_id>/extend", methods=["POST"])
@login_required
@role_required("Менеджер", "Менеджер по качеству")
def extend_deadline(request_id):
    data = {
        "new_completion_date": request.form["new_completion_date"],
        "reason": request.form.get("reason", "")
    }
    
    response, error = make_api_request('POST', f'/requests/{request_id}/extend', json=data, headers=api_headers())
    
    if error is None and response:
        flash("Срок выполнения успешно продлён!", "success")
    else:
        flash(error or "Ошибка продления срока", "danger")
    
    return redirect(url_for("request_detail", request_id=request_id))

@app.route("/requests/<int:request_id>/delete", methods=["POST"])
@login_required
@role_required("Менеджер")
def delete_request(request_id):
    if request.form.get("confirm") != "yes":
        flash("Удаление отменено", "warning")
        return redirect(url_for("request_detail", request_id=request_id))
    
    response, error = make_api_request('DELETE', f'/requests/{request_id}', headers=api_headers())
    
    if error is None and response:
        flash("Заявка успешно удалена!", "success")
        return redirect(url_for("requests_list"))
    else:
        flash(error or "Ошибка удаления заявки", "danger")
        return redirect(url_for("request_detail", request_id=request_id))

@app.route("/comments")
@login_required
@role_required("Оператор", "Специалист", "Менеджер", "Менеджер по качеству")
def comments_list():
    response, error = make_api_request('GET', '/comments/', headers=api_headers())
    
    if error is None and response:
        comments = response.json()
    else:
        comments = []
        flash(error or "Ошибка загрузки комментариев", "danger")
    
    return render_template("comments/list.html", 
                         comments=comments, 
                         role=session.get("role"),
                         title="Комментарии")

@app.route("/comments/new", methods=["GET", "POST"])
@login_required
@role_required("Специалист", "Менеджер", "Менеджер по качеству")
def new_comment():
    if request.method == "POST":
        data = {
            "message": request.form["message"],
            "master_id": int(request.form["master_id"]),
            "request_id": int(request.form["request_id"]),
        }
        
        response, error = make_api_request('POST', '/comments/', json=data, headers=api_headers())
        
        if error is None and response:
            flash("Комментарий успешно добавлен!", "success")
            return redirect(url_for("comments_list"))
        else:
            flash(error or "Ошибка добавления комментария", "danger")
    
    return render_template("comments/create.html", 
                         role=session.get("role"),
                         title="Новый комментарий")

@app.route("/qr/feedback.png")
@login_required
def qr_feedback():
    try:
        response = http.get(f"{API_URL}/qr/feedback", headers=api_headers())
        if response.status_code == 200:
            return send_file(io.BytesIO(response.content), mimetype="image/png")
    except Exception as e:
        logger.error(f"QR generation error: {e}")
    
    try:
        import qrcode
        FEEDBACK_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdhZcExx6LSIXxk0ub55mSu-WIh23WYdGG9HY5EZhLDo7P8eA/viewform?usp=sf_link"
        img = qrcode.make(FEEDBACK_URL)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return send_file(buf, mimetype="image/png")
    except ImportError:
        flash("Для генерации QR-кода установите библиотеку qrcode: pip install qrcode[pil]", "warning")
        return redirect(url_for("index"))

@app.route("/statistics")
@login_required
def statistics():
    """Страница статистики"""
    # Для заказчиков показываем сообщение
    if session.get("role") == "Заказчик":
        return render_template("statistics.html",
                             stats={},
                             role=session.get("role"),
                             title="Статистика")
    
    stats_data = {}
    
    endpoints = {
        'count': '/requests/stats/count',
        'avg_time': '/requests/stats/avg-time',
        'by_tech': '/requests/stats/by-tech',
        'by_problem': '/requests/stats/by-problem-type'
    }
    
    for key, endpoint in endpoints.items():
        response, error = make_api_request('GET', endpoint, headers=api_headers())
        if error is None and response:
            stats_data[key] = response.json()
        else:
            stats_data[key] = None if key == 'avg_time' else []
    
    return render_template("statistics.html",
                         stats=stats_data,
                         role=session.get("role"),
                         title="Статистика")

# ---------- Маршруты для заказчиков ----------
@app.route("/my-requests")
@login_required
def my_requests():
    """Список заявок текущего пользователя (для заказчиков)"""
    if session.get("role") != "Заказчик":
        flash("Эта страница только для заказчиков", "warning")
        return redirect(url_for("index"))
    
    params = {k: v for k, v in request.args.items() if v}
    response, error = make_api_request('GET', '/client/my-requests', params=params, headers=api_headers())
    
    if error is None and response:
        requests_data = response.json()
    else:
        requests_data = []
        if error:
            flash(error, "danger")
    
    return render_template("client/my_requests.html", 
                         requests=requests_data, 
                         role=session.get("role"),
                         title="Мои заявки")

@app.route("/my-requests/new", methods=["GET", "POST"])
@login_required
def new_my_request():
    """Создание новой заявки (для заказчиков)"""
    if session.get("role") != "Заказчик":
        flash("Эта страница только для заказчиков", "warning")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        # Получаем user_id из сессии
        user_id = session.get("user_id")
        
        # Если user_id не в сессии, пробуем получить его из API
        if not user_id:
            # Делаем запрос к API для получения информации о текущем пользователе
            response, error = make_api_request('GET', '/auth/me', headers=api_headers())
            if error is None and response:
                user_info = response.json()
                user_id = user_info.get("user_id")
                if user_id:
                    session["user_id"] = user_id
        
        # Если все еще нет user_id, используем тестовый
        if not user_id:
            # Тестовые user_id для демонстрации (в реальном приложении этого быть не должно)
            test_ids = {
                "login6": 6,  # Заказчик
                "login7": 7,  # Заказчик
                "login8": 8,  # Заказчик
                "login9": 9,  # Заказчик
            }
            user_login = session.get("login")
            user_id = test_ids.get(user_login, 7)  # По умолчанию ID 7
        
        try:
            client_id = int(user_id)
        except (ValueError, TypeError):
            flash("Ошибка: Некорректный ID пользователя", "danger")
            return redirect(url_for("my_requests"))
        
        data = {
            "start_date": request.form["start_date"],
            "climate_tech_type": request.form["climate_tech_type"],
            "climate_tech_model": request.form["climate_tech_model"],
            "problem_description": request.form["problem_description"],
            "request_status": "Новая заявка",
            "client_id": client_id,
        }
        
        print(f"Отправляемые данные: {data}")
        
        response, error = make_api_request('POST', '/client/my-requests', json=data, headers=api_headers())
        
        if error is None and response:
            flash("Заявка успешно создана!", "success")
            return redirect(url_for("my_requests"))
        else:
            flash(error or "Ошибка создания заявки", "danger")
    
    today = datetime.now().strftime("%Y-%m-%d")
    user_id = session.get("user_id", "")
    return render_template("client/new_request.html", 
                         role=session.get("role"),
                         today=today,
                         user_id=user_id,
                         title="Создание новой заявки")

@app.route("/my-requests/<int:request_id>")
@login_required
def my_request_detail(request_id):
    """Детальная информация о заявке (для заказчиков)"""
    if session.get("role") != "Заказчик":
        flash("Эта страница только для заказчиков", "warning")
        return redirect(url_for("index"))
    
    response, error = make_api_request('GET', f'/client/my-requests/{request_id}', headers=api_headers())
    
    if error is None and response:
        request_data = response.json()
        
        comments_response, comments_error = make_api_request('GET', f'/client/my-requests/{request_id}/comments', headers=api_headers())
        if comments_error is None and comments_response:
            request_comments = comments_response.json()
        else:
            request_comments = []
        
        return render_template("client/request_detail.html", 
                             r=request_data, 
                             comments=request_comments,
                             role=session.get("role"),
                             title=f"Моя заявка #{request_id}")
    else:
        flash(error or "Заявка не найдена", "danger")
        return redirect(url_for("my_requests"))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html', title="Страница не найдена"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html', title="Внутренняя ошибка сервера"), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)