from flask import Flask
from flask import request
import requests
import psycopg2


app = Flask(__name__, static_url_path='')

@app.route('/missed')
def render_missed():
    return app.send_static_file('html/missed.html')

@app.route('/')
def render_index():
    return app.send_static_file('html/index.html')

@app.route('/raw_db')
def render_db():
    DATABASE_URL='postgres://pkszoedlaykwsk:2ff4fae6161d29c22cf40f349faaa1e48d8524aab1caf6eed72f773a31f0a91b@ec2-54-83-0-158.compute-1.amazonaws.com:5432/d42mu98rpmdqbj'
    conn = psycopg2.connect(DATABASE_URL, sslmode='require', user='pkszoedlaykwsk', password='2ff4fae6161d29c22cf40f349faaa1e48d8524aab1caf6eed72f773a31f0a91b' )
    cursor = conn.cursor()
    query =  "SELECT * FROM posts_scraped;"
    print(DATABASE_URL)
    posts = cursor.execute(query)
    print("Retrieved Posts")
    print(posts)

    return app.send_static_file('data/db.json')

if __name__ == '__main__':
    app.run()
