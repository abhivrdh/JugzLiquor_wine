"""
LiquorKiosk — Flask Backend (Alex AI Sommelier)
"""
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import json, os, urllib.request, urllib.error

app = Flask(__name__)
CORS(app)

PRODUCTS = [
    {"id":1,"name":"Blanton's Single Barrel","category":"Bourbon","desc":"The original single barrel bourbon. Vanilla, caramel, dried fruit. First commercial single barrel (1984).","tags":["Bourbon","Premium","Allocated"],"icon":"🥃"},
    {"id":2,"name":"Pappy Van Winkle 23yr","category":"Bourbon","desc":"Holy grail of bourbon. Wheated mash — vanilla, caramel, butterscotch. Ultra rare allocated.","tags":["Bourbon","Ultra-Rare"],"icon":"🥃"},
    {"id":3,"name":"Buffalo Trace","category":"Bourbon","desc":"Best everyday bourbon. Vanilla, caramel, mint, oak. Exceptional value.","tags":["Bourbon","Value"],"icon":"🥃"},
    {"id":4,"name":"Woodford Reserve","category":"Bourbon","desc":"Triple distilled. Dried fruit, vanilla, chocolate. Official bourbon of the Kentucky Derby.","tags":["Bourbon","Premium"],"icon":"🥃"},
    {"id":5,"name":"Eagle Rare 10yr","category":"Bourbon","desc":"Single barrel. Dark fruit, herbs, honey, toffee.","tags":["Bourbon","Allocated"],"icon":"🥃"},
    {"id":6,"name":"Macallan 12yr Sherry Oak","category":"Scotch","desc":"100% sherry-seasoned casks. Dried fruits, chocolate, spice, ginger.","tags":["Scotch","Speyside"],"icon":"🥃"},
    {"id":7,"name":"Laphroaig 10yr","category":"Scotch","desc":"Iconic Islay Scotch. Intense peat, seaweed, iodine, smoke with surprising sweetness.","tags":["Scotch","Islay","Peated"],"icon":"🥃"},
    {"id":8,"name":"Lagavulin 16yr","category":"Scotch","desc":"Islay legend. Rich peat smoke, dried fruit, seaweed. Sip slowly.","tags":["Scotch","Premium"],"icon":"🥃"},
    {"id":9,"name":"Don Julio 1942","category":"Tequila","desc":"Aged 2.5 years. Silky caramel, vanilla, dark chocolate. The celebratory tequila.","tags":["Tequila","Añejo","Premium"],"icon":"🌵"},
    {"id":10,"name":"Clase Azul Reposado","category":"Tequila","desc":"Handmade ceramic bottle. Vanilla, caramel, ultra-premium agave.","tags":["Tequila","Ultra-Premium"],"icon":"🌵"},
    {"id":11,"name":"Fortaleza Blanco","category":"Tequila","desc":"Tahona stone-ground. Earthy agave, citrus, pepper. Best for margaritas.","tags":["Tequila","Blanco"],"icon":"🌵"},
    {"id":12,"name":"Hendrick's Gin","category":"Gin","desc":"Bulgarian rose and cucumber infusion. Unique, refreshing, mysterious.","tags":["Gin","Floral"],"icon":"🌿"},
    {"id":13,"name":"Monkey 47","category":"Gin","desc":"47 botanicals from the German Black Forest at 47% ABV. Complex beyond belief.","tags":["Gin","Premium"],"icon":"🌿"},
    {"id":14,"name":"Grey Goose","category":"Vodka","desc":"French soft wheat. Clean, elegant, slightly sweet. The premium benchmark.","tags":["Vodka","Premium"],"icon":"🍸"},
    {"id":15,"name":"Tito's Handmade Vodka","category":"Vodka","desc":"Texas corn, gluten-free, incredibly smooth. Outstanding quality.","tags":["Vodka","Value"],"icon":"🍸"},
    {"id":16,"name":"Diplomatico Reserva","category":"Rum","desc":"Venezuelan rum aged 12 years. Dark toffee, fig, chocolate, butterscotch.","tags":["Rum","Premium"],"icon":"🏝️"},
    {"id":17,"name":"Ron Zacapa 23","category":"Rum","desc":"Guatemalan Solera system. Luscious dried fruit, toffee, chocolate.","tags":["Rum","Premium"],"icon":"🏝️"},
    {"id":18,"name":"Hennessy VSOP","category":"Cognac","desc":"60+ eaux-de-vie aged 4-15 years. Toasted oak, vanilla, cinnamon.","tags":["Cognac","VSOP"],"icon":"🥂"},
    {"id":19,"name":"Caymus Cabernet","category":"Wine","desc":"Napa Valley icon. Dense blackberry, dark cherry, chocolate, vanilla oak.","tags":["Wine","Red","Napa"],"icon":"🍷"},
    {"id":20,"name":"Moët Brut Impérial","category":"Champagne","desc":"World's most celebrated Champagne. Apple, white blossom, fine bubbles.","tags":["Champagne","Sparkling"],"icon":"🍾"},
    {"id":21,"name":"Whiskey Lover's Gift Set","category":"Gift","desc":"Blanton's + crystal glass + whiskey stones, gorgeously gift boxed.","tags":["Gift","Premium"],"icon":"🎁"},
    {"id":22,"name":"WhistlePig 10yr Rye","category":"Rye","desc":"Vermont-aged Canadian rye. Boldly spicy — cinnamon, mint, dried fruit.","tags":["Rye","Premium"],"icon":"🥃"},
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/products')
def get_products():
    category = request.args.get('category','').lower()
    query    = request.args.get('q','').lower()
    results  = PRODUCTS
    if category:
        results = [p for p in results if p['category'].lower()==category]
    if query:
        results = [p for p in results if query in p['name'].lower() or
                   query in p['desc'].lower() or
                   any(query in t.lower() for t in p['tags'])]
    return jsonify(results)

@app.route('/api/recipes')
def get_recipes():
    return jsonify(RECIPES)

@app.route('/api/chat', methods=['POST'])
def chat():
    data     = request.get_json()
    messages = data.get('messages', [])
    system   = data.get('system', '')

    # ✅ Reads API key from Vercel Environment Variable
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 400,
        "system": system,
        "messages": messages
    }).encode()

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01',
            'x-api-key': api_key,
            'anthropic-dangerous-direct-browser-access': 'true'
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return jsonify({'reply': result['content'][0]['text']})
    except urllib.error.HTTPError as e:
        return jsonify({'error': e.read().decode()}), e.code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search')
def search():
    q = request.args.get('q','').lower()
    if not q: return jsonify([])
    results = [p for p in PRODUCTS if q in p['name'].lower() or
               q in p['desc'].lower() or any(q in t.lower() for t in p['tags'])]
    return jsonify(results[:8])

@app.route('/static/assets/avatar.glb')
def serve_glb():
    p = os.path.join(os.path.dirname(__file__),'static','assets','avatar.glb')
    return send_file(p, mimetype='model/gltf-binary', conditional=True, etag=True, max_age=86400)

@app.route('/static/js/vendor/three.min.js')
def serve_three():
    p = os.path.join(os.path.dirname(__file__),'static','js','vendor','three.min.js')
    return send_file(p, mimetype='application/javascript', max_age=86400)

@app.route('/static/js/vendor/GLTFLoader.js')
def serve_gltf():
    p = os.path.join(os.path.dirname(__file__),'static','js','vendor','GLTFLoader.js')
    return send_file(p, mimetype='application/javascript', max_age=86400)

@app.route('/static/assets/logo.jpeg')
def serve_logo():
    p = os.path.join(os.path.dirname(__file__), 'static', 'assets', 'logo.jpeg')
    return send_file(p, mimetype='image/jpeg', max_age=86400)

@app.route('/static/assets/bg/<path:filename>')
def serve_bg(filename):
    p = os.path.join(os.path.dirname(__file__), 'static', 'assets', 'bg', filename)
    if not os.path.exists(p):
        return '', 404
    mime = 'image/jpeg' if filename.lower().endswith(('.jpg','.jpeg')) else 'image/png'
    return send_file(p, mimetype=mime, max_age=86400)

if __name__ == '__main__':
    print("\n🍾 Jugz Liquor and Wine — Alex AI Sommelier")
    print("   http://localhost:5000\n")
    app.run(debug=True, port=5000, host='0.0.0.0')