"""
Jugz Liquor and Wine — Flask Backend (Alex AI Sommelier)
With Upstash Redis auth, single-session enforcement, admin panel.
"""
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_cors import CORS
from functools import wraps
import json, os, urllib.request, urllib.error, hashlib, secrets, time

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('APP_SECRET_KEY', 'dev-fallback-key-change-me')

# ── Upstash Redis via REST API ──
KV_URL   = os.environ.get('KV_REST_API_URL', '')
KV_TOKEN = os.environ.get('KV_REST_API_TOKEN', '')

def redis_cmd(*args):
    if not KV_URL or not KV_TOKEN:
        return None
    payload = json.dumps(list(args)).encode()
    req = urllib.request.Request(KV_URL, data=payload,
        headers={'Authorization': f'Bearer {KV_TOKEN}', 'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode()).get('result')
    except Exception as e:
        print(f"Redis error: {e}")
        return None

def hash_password(password):
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password, stored):
    if ':' not in stored: return False
    salt, hashed = stored.split(':', 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == hashed

def has_users():
    return redis_cmd('GET', 'jugz:has_users') == '1'

def get_user(username):
    data = redis_cmd('GET', f'jugz:user:{username}')
    if data: return json.loads(data) if isinstance(data, str) else data
    return None

def create_user(username, password, role='staff'):
    user_data = json.dumps({'username': username, 'password': hash_password(password), 'role': role, 'created': int(time.time())})
    redis_cmd('SET', f'jugz:user:{username}', user_data)
    redis_cmd('SADD', 'jugz:users', username)
    redis_cmd('SET', 'jugz:has_users', '1')

def get_all_users():
    users = redis_cmd('SMEMBERS', 'jugz:users')
    return users if users else []

def delete_user(username):
    redis_cmd('DEL', f'jugz:user:{username}')
    redis_cmd('SREM', 'jugz:users', username)
    redis_cmd('DEL', f'jugz:active_session:{username}')
    remaining = redis_cmd('SMEMBERS', 'jugz:users')
    if not remaining: redis_cmd('SET', 'jugz:has_users', '0')

def create_session(username):
    token = secrets.token_hex(32)
    session_data = json.dumps({'username': username, 'created': int(time.time()), 'token': token})
    old_token = redis_cmd('GET', f'jugz:active_session:{username}')
    if old_token: redis_cmd('DEL', f'jugz:session:{old_token}')
    redis_cmd('SET', f'jugz:session:{token}', session_data, 'EX', '28800')
    redis_cmd('SET', f'jugz:active_session:{username}', token, 'EX', '28800')
    return token

def validate_session(token):
    if not token: return None
    data = redis_cmd('GET', f'jugz:session:{token}')
    if not data: return None
    session = json.loads(data) if isinstance(data, str) else data
    username = session.get('username')
    active_token = redis_cmd('GET', f'jugz:active_session:{username}')
    if active_token != token:
        redis_cmd('DEL', f'jugz:session:{token}')
        return None
    return username

def destroy_session(token):
    data = redis_cmd('GET', f'jugz:session:{token}')
    if data:
        session = json.loads(data) if isinstance(data, str) else data
        redis_cmd('DEL', f'jugz:active_session:{session.get("username")}')
    redis_cmd('DEL', f'jugz:session:{token}')

def get_current_user():
    token = request.cookies.get('jugz_session')
    return validate_session(token)

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not has_users(): return redirect(url_for('setup_page'))
        user = get_current_user()
        if not user: return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def require_auth_api(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user: return jsonify({'error': 'Session expired', 'kicked': True}), 401
        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user: return redirect(url_for('login_page'))
        user_data = get_user(user)
        if not user_data or user_data.get('role') != 'admin': return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ── Products & Recipes ──
PRODUCTS = [
    {"id":1,"name":"Blanton's Single Barrel","category":"Bourbon","desc":"The original single barrel bourbon. Vanilla, caramel, dried fruit.","tags":["Bourbon","Premium","Allocated"],"icon":"🥃"},
    {"id":2,"name":"Pappy Van Winkle 23yr","category":"Bourbon","desc":"Holy grail of bourbon. Wheated mash — vanilla, caramel, butterscotch.","tags":["Bourbon","Ultra-Rare"],"icon":"🥃"},
    {"id":3,"name":"Buffalo Trace","category":"Bourbon","desc":"Best everyday bourbon. Vanilla, caramel, mint, oak.","tags":["Bourbon","Value"],"icon":"🥃"},
    {"id":4,"name":"Woodford Reserve","category":"Bourbon","desc":"Triple distilled. Dried fruit, vanilla, chocolate.","tags":["Bourbon","Premium"],"icon":"🥃"},
    {"id":5,"name":"Eagle Rare 10yr","category":"Bourbon","desc":"Single barrel. Dark fruit, herbs, honey, toffee.","tags":["Bourbon","Allocated"],"icon":"🥃"},
    {"id":6,"name":"Macallan 12yr Sherry Oak","category":"Scotch","desc":"100% sherry-seasoned casks. Dried fruits, chocolate, spice.","tags":["Scotch","Speyside"],"icon":"🥃"},
    {"id":7,"name":"Laphroaig 10yr","category":"Scotch","desc":"Iconic Islay Scotch. Intense peat, seaweed, iodine, smoke.","tags":["Scotch","Islay","Peated"],"icon":"🥃"},
    {"id":8,"name":"Lagavulin 16yr","category":"Scotch","desc":"Islay legend. Rich peat smoke, dried fruit, seaweed.","tags":["Scotch","Premium"],"icon":"🥃"},
    {"id":9,"name":"Don Julio 1942","category":"Tequila","desc":"Aged 2.5 years. Silky caramel, vanilla, dark chocolate.","tags":["Tequila","Añejo","Premium"],"icon":"🌵"},
    {"id":10,"name":"Clase Azul Reposado","category":"Tequila","desc":"Handmade ceramic bottle. Vanilla, caramel, ultra-premium agave.","tags":["Tequila","Ultra-Premium"],"icon":"🌵"},
    {"id":11,"name":"Fortaleza Blanco","category":"Tequila","desc":"Tahona stone-ground. Earthy agave, citrus, pepper.","tags":["Tequila","Blanco"],"icon":"🌵"},
    {"id":12,"name":"Hendrick's Gin","category":"Gin","desc":"Bulgarian rose and cucumber infusion. Unique, refreshing.","tags":["Gin","Floral"],"icon":"🌿"},
    {"id":13,"name":"Monkey 47","category":"Gin","desc":"47 botanicals from the German Black Forest at 47% ABV.","tags":["Gin","Premium"],"icon":"🌿"},
    {"id":14,"name":"Grey Goose","category":"Vodka","desc":"French soft wheat. Clean, elegant, slightly sweet.","tags":["Vodka","Premium"],"icon":"🍸"},
    {"id":15,"name":"Tito's Handmade Vodka","category":"Vodka","desc":"Texas corn, gluten-free, incredibly smooth.","tags":["Vodka","Value"],"icon":"🍸"},
    {"id":16,"name":"Diplomatico Reserva","category":"Rum","desc":"Venezuelan rum aged 12 years. Dark toffee, fig, chocolate.","tags":["Rum","Premium"],"icon":"🏝️"},
    {"id":17,"name":"Ron Zacapa 23","category":"Rum","desc":"Guatemalan Solera system. Dried fruit, toffee, chocolate.","tags":["Rum","Premium"],"icon":"🏝️"},
    {"id":18,"name":"Hennessy VSOP","category":"Cognac","desc":"60+ eaux-de-vie aged 4-15 years. Oak, vanilla, cinnamon.","tags":["Cognac","VSOP"],"icon":"🥂"},
    {"id":19,"name":"Caymus Cabernet","category":"Wine","desc":"Napa Valley icon. Dense blackberry, dark cherry, chocolate.","tags":["Wine","Red","Napa"],"icon":"🍷"},
    {"id":20,"name":"Moët Brut Impérial","category":"Champagne","desc":"World's most celebrated Champagne. Apple, white blossom.","tags":["Champagne","Sparkling"],"icon":"🍾"},
    {"id":21,"name":"Whiskey Lover's Gift Set","category":"Gift","desc":"Blanton's + crystal glass + whiskey stones, gift boxed.","tags":["Gift","Premium"],"icon":"🎁"},
    {"id":22,"name":"WhistlePig 10yr Rye","category":"Rye","desc":"Vermont-aged Canadian rye. Cinnamon, mint, dried fruit.","tags":["Rye","Premium"],"icon":"🥃"},
]
RECIPES = [
    {"name":"Old Fashioned","difficulty":"Easy","ingredients":["2oz Bourbon","1 Sugar cube","2 dashes Angostura bitters","Orange peel"],"steps":["Muddle sugar and bitters in glass","Add large ice cube","Pour bourbon over ice","Stir 30 seconds","Express orange peel over glass"]},
    {"name":"Classic Margarita","difficulty":"Easy","ingredients":["2oz Blanco tequila","1oz Fresh lime juice","¾oz Cointreau","Salt rim"],"steps":["Salt rim of coupe glass","Combine tequila, lime, Cointreau in shaker","Shake hard with ice","Strain into glass","Garnish with lime wheel"]},
    {"name":"Negroni","difficulty":"Easy","ingredients":["1oz Gin","1oz Campari","1oz Sweet vermouth","Orange peel"],"steps":["Combine all in mixing glass with ice","Stir 20 seconds","Strain into rocks glass over ice","Express orange peel over glass"]},
    {"name":"Whiskey Sour","difficulty":"Medium","ingredients":["2oz Bourbon","¾oz Lemon juice","¾oz Simple syrup","1 Egg white"],"steps":["Dry shake all ingredients vigorously","Add ice and shake again hard","Double strain into chilled coupe","Optional Angostura float on top"]},
    {"name":"Espresso Martini","difficulty":"Medium","ingredients":["2oz Vodka","1oz Kahlúa","1oz Hot espresso","3 Coffee beans"],"steps":["Combine vodka, Kahlúa and espresso in shaker","Shake very hard with ice","Strain into chilled martini glass","Garnish with 3 coffee beans"]},
    {"name":"Aperol Spritz","difficulty":"Easy","ingredients":["3oz Prosecco","2oz Aperol","1oz Soda water","Orange slice"],"steps":["Fill wine glass with ice","Add Aperol then Prosecco","Top with soda water gently","Garnish with orange slice"]},
    {"name":"Paper Plane","difficulty":"Medium","ingredients":["¾oz Bourbon","¾oz Aperol","¾oz Amaro Nonino","¾oz Lemon juice"],"steps":["Combine equal parts in shaker with ice","Shake hard","Strain into chilled coupe","No garnish needed"]},
    {"name":"Penicillin","difficulty":"Advanced","ingredients":["2oz Blended Scotch","¾oz Lemon juice","¾oz Honey-ginger syrup","¼oz Islay Scotch (float)"],"steps":["Shake blended Scotch, lemon, honey-ginger syrup with ice","Strain into rocks glass over large ice","Float Islay Scotch on top gently","Garnish with candied ginger"]},
]

# ── Auth Pages ──
@app.route('/setup')
def setup_page():
    if has_users():
        user = get_current_user()
        if user: return redirect(url_for('index'))
        return redirect(url_for('login_page'))
    return render_template('setup.html')

@app.route('/api/setup', methods=['POST'])
def setup_action():
    if has_users(): return jsonify({'error': 'Setup already completed'}), 403
    data = request.get_json()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    if not username or not password: return jsonify({'error': 'Username and password required'}), 400
    if len(username) < 3: return jsonify({'error': 'Username must be at least 3 characters'}), 400
    if len(password) < 6: return jsonify({'error': 'Password must be at least 6 characters'}), 400
    create_user(username, password, role='admin')
    token = create_session(username)
    resp = jsonify({'success': True, 'redirect': '/'})
    is_secure = request.headers.get('X-Forwarded-Proto') == 'https' or request.is_secure
    resp.set_cookie('jugz_session', token, httponly=True, secure=is_secure, samesite='Lax', max_age=28800)
    return resp

@app.route('/login')
def login_page():
    if not has_users(): return redirect(url_for('setup_page'))
    user = get_current_user()
    if user: return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login_action():
    data = request.get_json()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    user_data = get_user(username)
    if not user_data or not verify_password(password, user_data.get('password', '')):
        return jsonify({'error': 'Invalid username or password'}), 401
    token = create_session(username)
    resp = jsonify({'success': True, 'redirect': '/'})
    is_secure = request.headers.get('X-Forwarded-Proto') == 'https' or request.is_secure
    resp.set_cookie('jugz_session', token, httponly=True, secure=is_secure, samesite='Lax', max_age=28800)
    return resp

@app.route('/logout')
def logout():
    token = request.cookies.get('jugz_session')
    if token: destroy_session(token)
    resp = redirect(url_for('login_page'))
    resp.delete_cookie('jugz_session')
    return resp

@app.route('/api/session-check')
def session_check():
    user = get_current_user()
    if user: return jsonify({'valid': True, 'username': user})
    return jsonify({'valid': False}), 401

# ── Admin ──
@app.route('/admin')
@require_admin
def admin_page(): return render_template('admin.html')

@app.route('/api/admin/users')
@require_admin
def admin_list_users():
    usernames = get_all_users()
    users = []
    for u in usernames:
        data = get_user(u)
        if data: users.append({'username': data.get('username', u), 'role': data.get('role', 'staff'), 'created': data.get('created', 0)})
    return jsonify(users)

@app.route('/api/admin/users', methods=['POST'])
@require_admin
def admin_add_user():
    data = request.get_json()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'staff')
    if not username or not password: return jsonify({'error': 'Username and password required'}), 400
    if len(username) < 3: return jsonify({'error': 'Username must be at least 3 characters'}), 400
    if len(password) < 6: return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if get_user(username): return jsonify({'error': 'Username already exists'}), 409
    if role not in ('admin', 'staff'): role = 'staff'
    create_user(username, password, role)
    return jsonify({'success': True})

@app.route('/api/admin/users/<username>', methods=['DELETE'])
@require_admin
def admin_delete_user(username):
    current = get_current_user()
    if username == current: return jsonify({'error': 'Cannot delete your own account'}), 400
    if not get_user(username): return jsonify({'error': 'User not found'}), 404
    delete_user(username)
    return jsonify({'success': True})

# ── App Routes (Protected) ──
@app.route('/')
@require_auth
def index():
    user = get_current_user()
    user_data = get_user(user) if user else {}
    return render_template('index.html', current_user=user, user_role=user_data.get('role', 'staff') if user_data else 'staff')

@app.route('/api/products')
@require_auth_api
def get_products():
    category = request.args.get('category','').lower()
    query = request.args.get('q','').lower()
    results = PRODUCTS
    if category: results = [p for p in results if p['category'].lower()==category]
    if query: results = [p for p in results if query in p['name'].lower() or query in p['desc'].lower() or any(query in t.lower() for t in p['tags'])]
    return jsonify(results)

@app.route('/api/recipes')
@require_auth_api
def get_recipes(): return jsonify(RECIPES)

@app.route('/api/chat', methods=['POST'])
@require_auth_api
def chat():
    data = request.get_json()
    messages = data.get('messages', [])
    system = data.get('system', '')
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    payload = json.dumps({"model": "claude-sonnet-4-20250514", "max_tokens": 400, "system": system, "messages": messages}).encode()
    req = urllib.request.Request('https://api.anthropic.com/v1/messages', data=payload,
        headers={'Content-Type': 'application/json', 'anthropic-version': '2023-06-01', 'x-api-key': api_key, 'anthropic-dangerous-direct-browser-access': 'true'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return jsonify({'reply': result['content'][0]['text']})
    except urllib.error.HTTPError as e: return jsonify({'error': e.read().decode()}), e.code
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/search')
@require_auth_api
def search():
    q = request.args.get('q','').lower()
    if not q: return jsonify([])
    results = [p for p in PRODUCTS if q in p['name'].lower() or q in p['desc'].lower() or any(q in t.lower() for t in p['tags'])]
    return jsonify(results[:8])

# ── Static Assets ──
@app.route('/static/assets/avatar.glb')
def serve_glb():
    p = os.path.join(os.path.dirname(__file__),'static','assets','avatar.glb')
    return send_file(p, mimetype='model/gltf-binary', conditional=True, etag=True, max_age=86400)

@app.route('/static/js/vendor/three.min.js')
def serve_three():
    return send_file(os.path.join(os.path.dirname(__file__),'static','js','vendor','three.min.js'), mimetype='application/javascript', max_age=86400)

@app.route('/static/js/vendor/GLTFLoader.js')
def serve_gltf():
    return send_file(os.path.join(os.path.dirname(__file__),'static','js','vendor','GLTFLoader.js'), mimetype='application/javascript', max_age=86400)

@app.route('/static/assets/logo.jpeg')
def serve_logo():
    return send_file(os.path.join(os.path.dirname(__file__), 'static', 'assets', 'logo.jpeg'), mimetype='image/jpeg', max_age=86400)

@app.route('/static/assets/bg/<path:filename>')
def serve_bg(filename):
    p = os.path.join(os.path.dirname(__file__), 'static', 'assets', 'bg', filename)
    if not os.path.exists(p): return '', 404
    mime = 'image/jpeg' if filename.lower().endswith(('.jpg','.jpeg')) else 'image/png'
    return send_file(p, mimetype=mime, max_age=86400)

if __name__ == '__main__':
    print("\n🍾 Jugz Liquor and Wine — Alex AI Sommelier")
    print("   http://localhost:5000\n")
    app.run(debug=True, port=5000, host='0.0.0.0')
