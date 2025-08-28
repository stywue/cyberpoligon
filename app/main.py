import os
import psycopg2
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, abort
from jinja2 import TemplateNotFound

app = Flask(__name__)

DB_CONFIG = {
    'dbname': os.environ.get('DB_NAME', 'mydb'),
    'user': os.environ.get('DB_USER', 'myuser'),
    'password': os.environ.get('DB_PASSWORD', 'mypass'),
    'host': os.environ.get('DB_HOST', 'db'),
    'port': os.environ.get('DB_PORT', 5432)
}

WEATHER_API_KEY = os.environ.get('WEATHER_API_KEY', 'your_openweathermap_api_key')
WEATHER_CITY = 'Saint Petersburg'
WEATHER_UNITS = 'metric'
WEATHER_LANG = 'ru'

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    pages = collect_pages_from_templates()

    conn = get_connection()
    cursor = conn.cursor()
    for p in pages:
        cursor.execute("""
        INSERT INTO pages (page_name, title, content, snippet)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (snippet) DO UPDATE 
        SET title = EXCLUDED.title,
            content = EXCLUDED.content,
            search_vector = to_tsvector('russian', EXCLUDED.title || ' ' || EXCLUDED.content)
        """, (p['page_name'], p['title'], p['content'], p['snippet']))
    conn.commit()
    conn.close()

    print("✅ База данных инициализирована.")

def search_pages(query):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Parse Google Dorks operators
    if ':' in query:
        if query.startswith('inurl:'):
            # Search in page_name field
            search_term = query[6:]  # Remove 'inurl:' prefix
            cursor.execute("""
                SELECT page_name, title, snippet
                FROM pages
                WHERE page_name ILIKE %s
                ORDER BY page_name;
            """, (f'%{search_term}%',))
        elif query.startswith('intitle:'):
            # Search in title field
            search_term = query[8:]  # Remove 'intitle:' prefix
            cursor.execute("""
                SELECT page_name, title, snippet
                FROM pages
                WHERE title ILIKE %s
                ORDER BY title;
            """, (f'%{search_term}%',))
        elif query.startswith('intext:'):
            # Search in content field
            search_term = query[7:]  # Remove 'intext:' prefix
            cursor.execute("""
                SELECT page_name, title, snippet
                FROM pages
                WHERE content ILIKE %s
                ORDER BY title;
            """, (f'%{search_term}%',))
        elif query.startswith('filetype:'):
            # Search by file extension in page_name
            file_type = query[9:]  # Remove 'filetype:' prefix
            cursor.execute("""
                SELECT page_name, title, snippet
                FROM pages
                WHERE page_name ILIKE %s
                ORDER BY page_name;
            """, (f'%.{file_type}%',))
        else:
            # Default search using full-text search
            cursor.execute("""
                SELECT page_name, title, snippet
                FROM pages
                WHERE search_vector @@ plainto_tsquery('russian', %s)
                ORDER BY ts_rank(search_vector, plainto_tsquery('russian', %s)) DESC;
            """, (query, query))
    else:
        # Default search using full-text search
        cursor.execute("""
            SELECT page_name, title, snippet
            FROM pages
            WHERE search_vector @@ plainto_tsquery('russian', %s)
            ORDER BY ts_rank(search_vector, plainto_tsquery('russian', %s)) DESC;
        """, (query, query))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_page_by_id(page_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM pages WHERE id = %s', (page_id,))
    page = cursor.fetchone()
    conn.close()
    return page

def fetch_weather():
    # Removed dynamic weather fetching, replaced with static data
    return {
        'temp': 17,
        'description': 'Облачно',
        'icon': 'http://openweathermap.org/img/wn/03d@2x.png'
    }

@app.route('/')
def index():
    weather = {
        'temp': 17,
        'description': 'Облачно',
        'icon': 'http://openweathermap.org/img/wn/03d@2x.png'
    }
    return render_template('index.html', weather=weather)

@app.route('/search')
def search():
    query = request.args.get('query')
    weather = {
        'temp': 17,
        'description': 'Облачно',
        'icon': 'http://openweathermap.org/img/wn/03d@2x.png'
    }
    if query:
        results = search_pages(query)
        return render_template('results.html', results=results, query=query, weather=weather)
    return "Введите поисковый запрос", 400

@app.route('/page/<int:page_id>')
def show_page(page_id):
    weather = {
        'temp': 17,
        'description': 'Облачно',
        'icon': 'http://openweathermap.org/img/wn/03d@2x.png'
    }
    page = get_page_by_id(page_id)
    if page:
        return render_template('page.html', title=page[1], content=page[2], weather=weather)
    return "Страница не найдена", 404

@app.route('/pages/<page_name>')
def show_custom_page(page_name):
    weather = {
        'temp': 17,
        'description': 'Облачно',
        'icon': 'http://openweathermap.org/img/wn/03d@2x.png'
    }
    try:
        return render_template(f'pages/{page_name}.html', weather=weather)
    except TemplateNotFound:
        abort(404)

def collect_pages_from_templates():
    pages_dir = os.path.join(app.root_path, 'templates', 'pages')
    page_files = [
        f for f in os.listdir(pages_dir)
        if f.endswith('.html')  
    ]
    pages = []
    for filename in page_files:
        path = os.path.join(pages_dir, filename)
        with open(path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
            title_tag = soup.title or soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else filename[:-5]

            content = soup.get_text(separator=' ', strip=True)

            snippet = title
            page_name = filename[:-5]
            pages.append({
                'page_name': page_name,
                'title': title,
                'content': content,
                'snippet': snippet
            })
    return pages

if __name__ == '__main__':
    try:
        init_db()
    except Exception as e:
        print(f"Ошибка при инициализации БД: {e}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
