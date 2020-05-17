from app import app
from flask import render_template, redirect, request, session
from bson.objectid import ObjectId
from flask_pymongo import PyMongo

# Connect to mongo database
app.config['MONGO_DBNAME'] = 'database'
app.config['MONGO_URI'] = 'mongodb+srv://admin:O6KsXSod8NVZLCPb@cluster0-udhtk.mongodb.net/database?retryWrites=true&w=majority'
mongo = PyMongo(app)

# Set the session secret
app.secret_key = b'\xdb\x83\xd8\xd77\xcf\xf89\x8b\xb9\xb4\x855}\xe0;'

@app.route('/')
@app.route('/featured')
def featured():
    # Find the featured articles
    article_collection = mongo.db.articles
    articles = list(article_collection.find({'featured': True}))
    articles.sort(key = lambda article : article['featured_position'])
    return render_template('featured.html', articles=list(articles))

@app.route('/articles/<topic>/<publication>')
def articles(topic, publication):
    
    # Find the relevant articles
    article_collection = mongo.db.articles
    if topic == 'any' and publication == 'any':
        articles = list(article_collection.find({}))
        viewing = False
    if topic != 'any':
        articles = list(article_collection.find({'topic': topic}))
        viewing = topic
    if publication != 'any':
        articles = list(article_collection.find({'publication': publication}))
        viewing = publication
    articles.sort(key = lambda article : article['all_position'])
    
    # Find the topics
    topic_collection = mongo.db.topics
    topics = topic_collection.find({})
    
    # Find the publications
    publication_collection = mongo.db.publications
    publications = publication_collection.find({})
    
    return render_template('articles.html', articles=articles, topics=topics, publications=publications, viewing=viewing)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login')
def login():
    if 'username' in session:
        return redirect('/admin/all')
    return render_template('login.html', error='')

@app.route('/login/submit', methods=['POST'])
def loginsubmit():
    username = request.form['username']
    password = request.form['password']
    if username == 'fred' and password == '1231':
        session['username'] = username
        return redirect('/admin/all')
    return render_template('login.html', error='Incorrect username or password')

@app.route('/admin/<article_type>')
def admin(article_type):
    if 'username' not in session:
        return redirect('/login')
    article_collection = mongo.db.articles
    if article_type == 'all':
        articles = list(article_collection.find({}))
        articles.sort(key = lambda article : article['all_position'])
    else:
        articles = list(article_collection.find({'featured': True}))
        articles.sort(key = lambda article : article['featured_position'])
    if 'checked_position' in session:
        checked_position = session.pop('checked_position')
        return render_template('admin.html', articles=articles, article_type=article_type, checked_position=checked_position)
    return render_template('admin.html', articles=articles, article_type=article_type)

@app.route('/admin/addarticle')
def adminaddarticle():
    if 'username' not in session:
        return redirect('/login')
    
    topic_collection = mongo.db.topics
    topics = topic_collection.find({})
    publication_collection = mongo.db.publications
    publications = publication_collection.find({})
    return render_template('addarticle.html', topics=topics, publications=publications)

@app.route('/admin/addarticle/submit', methods=['POST'])
def adminaddarticlesubmit():
    if 'username' not in session:
        return redirect('/login')
    
    # Collect form data
    title = request.form['title']
    subtitle = request.form['subtitle']
    publication = request.form.get('publication')
    date = request.form['date']
    topic = request.form.get('topic')
    featured = 'featured' in request.form
    url = request.form['url']
    text = request.form['text']
    
    # Split text into paragraphs
    paragraphs = []
    if text != '':
        paragraphs = text.split('\r\n\r\n')
    
    # Move older articles down
    article_collection = mongo.db.articles
    articles = list(article_collection.find({}))
    for article in articles:
        article_collection.update({'_id': article['_id']}, {'$inc': {'all_position': 1}})
        if featured and article['featured']:
            article_collection.update({'_id': article['_id']}, {'$inc': {'featured_position': 1}})

    # Add the new article to the database
    if featured:
        article_collection.insert({'title': title, 'subtitle': subtitle, 'publication': publication, 'date': date, 'url': url, 'topic': topic, 'featured': True, 'paragraphs': paragraphs, 'all_position': 0, 'featured_position': 0})
    else:
        article_collection.insert({'title': title, 'subtitle': subtitle, 'publication': publication, 'date': date, 'url': url, 'topic': topic, 'featured': False, 'paragraphs': paragraphs, 'all_position': 0})
    
    # Change url to point to article text page
    if url == '':
        new_article = article_collection.find_one({'all_position': 0})
        new_url = '/articletext/' + str(new_article['_id'])
        article_collection.update({'all_position': 0}, {'$set': {'url': new_url}})
    
    if featured:
        return redirect('/admin/featured')
    return redirect('/admin/all')

@app.route('/admin/editarticle/<article_id>')
def admineditarticle(article_id):
    if 'username' not in session:
        return redirect('/login')
    
    article_collection = mongo.db.articles
    article = article_collection.find_one({'_id': ObjectId(article_id)})
    topic_collection = mongo.db.topics
    topics = topic_collection.find({})
    publication_collection = mongo.db.publications
    publications = publication_collection.find({})
    return render_template('editarticle.html', article=article, topics=topics, publications=publications)

@app.route('/admin/editarticle/<article_id>/submit', methods=['POST'])
def admineditarticlesubmit(article_id):
    if 'username' not in session:
        return redirect('/login')
    
    article_collection = mongo.db.articles
    old_article = article_collection.find_one({'_id': ObjectId(article_id)})
    
    # Collect form data
    title = request.form['title']
    subtitle = request.form['subtitle']
    publication = request.form.get('publication')
    date = request.form['date']
    topic = request.form.get('topic')
    featured = 'featured' in request.form
    url = request.form['url']
    text = request.form['text']
    all_position = old_article['all_position']
    
    # Separate the paragraphs
    if text != '':
        paragraphs = text.split('\r\n\r\n')
    
    # Remove the old version of the article
    article_collection.remove({'_id': ObjectId(article_id)})
    
    if featured == old_article['featured']:
        # Add the new article to the database
        if featured:
            article_collection.insert({'_id': ObjectId(article_id), 'title': title, 'subtitle': subtitle, 'publication': publication, 'date': date, 'url': url, 'topic': topic, 'featured': True, 'paragraphs': paragraphs, 'all_position': all_position, 'featured_position': old_article['featured_position']})
        else:
            article_collection.insert({'_id': ObjectId(article_id), 'title': title, 'subtitle': subtitle, 'publication': publication, 'date': date, 'url': url, 'topic': topic, 'featured': False, 'paragraphs': paragraphs, 'all_position': all_position})
    elif featured:
        articles = article_collection.find({'featured': True})
        for article in articles:
            article_collection.update({'_id': article['_id']}, {'$inc': {'featured_position': 1}})
        article_collection.insert({'_id': ObjectId(article_id), 'title': title, 'subtitle': subtitle, 'publication': publication, 'date': date, 'url': url, 'topic': topic, 'featured': True, 'paragraphs': paragraphs, 'all_position': all_position, 'featured_position': 0})
    else:
        old_featured_position = old_article['featured_position']
        articles = article_collection.find({'featured': True})
        for article in articles:
            if article['featured_position'] > old_featured_position:
                article_collection.update({'_id': article['_id']}, {'$inc': {'featured_position': -1}})
        article_collection.insert({'_id': ObjectId(article_id), 'title': title, 'subtitle': subtitle, 'publication': publication, 'date': date, 'url': url, 'topic': topic, 'featured': False, 'paragraphs': paragraphs, 'all_position': all_position})
    
    if featured:
        return redirect('/admin/featured')
    return redirect('/admin/all')

@app.route('/admin/deletearticle/<article_id>')
def admindeletearticle(article_id):
    article_collection = mongo.db.articles
    old_article = article_collection.find_one({'_id': ObjectId(article_id)})
    old_position = old_article['all_position']
    
    articles = article_collection.find({})
    for article in articles:
        if article['all_position'] > old_position:
            article_collection.update({'_id': article['_id']}, {'$inc': {'all_position': -1}})
        if old_article['featured'] and article['featured']:
            old_featured_position = old_article['featured_position']
            if article['featured_position'] > old_featured_position:
                article_collection.update({'_id': article['_id']}, {'$inc': {'featured_position': -1}})
    
    article_collection.remove({'_id': ObjectId(article_id)})
    return redirect('/admin/all')

@app.route('/admin/addpublication')
def adminaddpublication():
    if 'username' not in session:
        return redirect('/login')
    return render_template('addpublication.html')
    
@app.route('/admin/addpublication/submit', methods=['POST'])
def adminaddpublicationsubmit():
    if 'username' not in session:
        return redirect('/login')
    publication = request.form['publication']
    publication_collection = mongo.db.publications
    publication_collection.insert({'name': publication})
    return redirect('/admin/all')

@app.route('/admin/addtopic')
def adminaddtopic():
    if 'username' not in session:
        return redirect('/login')
    return render_template('addtopic.html')
    
@app.route('/admin/addtopic/submit', methods=['POST'])
def adminaddtopicsubmit():
    if 'username' not in session:
        return redirect('/login')
    topic = request.form['topic']
    topic_collection = mongo.db.topics
    topic_collection.insert({'name': topic})
    return redirect('/admin/all')

@app.route('/admin/moveup/<article_id>/<article_type>')
def adminmoveup(article_id, article_type):
    if 'username' not in session:
        return redirect('/login')
    
    article_collection = mongo.db.articles
    article = article_collection.find_one({'_id': ObjectId(article_id)})
    if article_type == 'all':
        old_position = article['all_position']
    else:
        old_position = article['featured_position']
    if old_position > 0:
        article_collection.update({article_type + '_position': old_position - 1}, {'$inc': {article_type + '_position': 1}})
        article_collection.update({'_id': ObjectId(article_id)}, {'$inc': {article_type + '_position': -1}})
        session['checked_position'] = old_position - 1
    return redirect('/admin/' + article_type)

@app.route('/admin/movedown/<article_id>/<article_type>')
def adminmovedown(article_id, article_type):
    if 'username' not in session:
        return redirect('/login')
    
    article_collection = mongo.db.articles
    article = article_collection.find_one({'_id': ObjectId(article_id)})
    if article_type == 'all':
        old_position = article['all_position']
    else:
        old_position = article['featured_position']
    if old_position < article_collection.count() - 1:
        article_collection.update({article_type + '_position': old_position + 1}, {'$inc': {article_type + '_position': -1}})
        article_collection.update({'_id': ObjectId(article_id)}, {'$inc': {article_type + '_position': 1}})
        session['checked_position'] = old_position + 1
    return redirect('/admin/' + article_type)

@app.route('/articletext/<article_id>')
def articletext(article_id):
    article_collection = mongo.db.articles
    article = article_collection.find_one({'_id': ObjectId(article_id)})
    print(article)
    return render_template('articletext.html', article=article)

@app.route('/creativewriting')
def creativewriting():
    return render_template('creative.html')

@app.route('/designprojects')
def designprojects():
    return render_template('design.html')