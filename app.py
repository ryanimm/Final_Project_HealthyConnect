from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps
from bson import ObjectId
import os
import pytz
from os.path import join, dirname
from dotenv import load_dotenv

app = Flask(__name__)
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

SECRET_KEY = os.environ.get("SECRET_KEY")
ADMIN_KEY = os.environ.get("ADMIN_KEY")

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token_receive = request.cookies.get('mytoken')
        if token_receive is not None:
            try:
                payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
                if payload["role"] == "admin":
                    return f(*args, **kwargs)
                else:
                    return redirect(url_for('home', msg='Only admin can access this page'))
            except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
                return redirect(url_for('login', msg='Your token is invalid or has expired'))
        else:
            return redirect(url_for('login', msg='Please login to view this page'))
    return decorated_function



@app.route('/')
def home():
    token_receive = request.cookies.get("mytoken")
    try:
        if token_receive:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.user.find_one({'username': payload['id']})
        else:
            user_info = None
        
        articles = db.articles.find().sort("tanggal", -1).limit(3)
        
        return render_template('index.html', user_info=user_info, articles=articles)
    
    except jwt.ExpiredSignatureError:
        return render_template("index.html")
    
    except jwt.exceptions.DecodeError:
        return render_template("index.html")

    

@app.route("/login")
def login():
    token_receive = request.cookies.get("mytoken")
    try:
        if token_receive:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.user.find_one({'username': payload['id']})
            if user_info:
                return redirect(url_for('home'))
        
        return render_template("login.html")
    
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return render_template("login.html")


@app.route("/hubungi_kami", methods=['GET', 'POST'])
def hubungi():
    token_receive = request.cookies.get("mytoken")
    try:
        if token_receive:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.user.find_one({'username': payload['id']})
        else:
            user_info = None

        if request.method == 'POST':
            nama_lengkap = request.form['nama_lengkap']
            email = request.form['email']
            pesan = request.form['message']
            timezone = pytz.timezone('Asia/Jakarta')
            current_datetime = datetime.now(timezone)
            tanggal_kirim = current_datetime.strftime('%d/%m/%y - %H:%M')
            timestamp = current_datetime.timestamp()
            doc = {
                "nama_lengkap":nama_lengkap,
                "email" : email,
                "pesan" : pesan,
                "tanggal_kirim" : tanggal_kirim,
                "timestamp": timestamp,
            }
            db.hubungi.insert_one(doc)
            return jsonify({'msg':'Pesan Anda Berhasil Dikirim'})
        else:
            return render_template("hubungi.html",user_info=user_info)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))



@app.route("/artikel")
def artikel():
    token_receive = request.cookies.get("mytoken")
    try:
        if token_receive:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.user.find_one({'username': payload['id']})
        else:
            user_info = None
        articles= db.articles.find().sort("tanggal", -1)
        return render_template("artikel.html",user_info=user_info,articles=articles)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/artikel/<id>')
def isi_artikel(id):
    token_receive = request.cookies.get("mytoken")
    try:
        if token_receive:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
            user_info = db.user.find_one({"username": payload["id"]})
        else:
            user_info = None
        article = db.articles.find_one({'_id': ObjectId(id)})
        return render_template("isi_artikel.html",user_info=user_info,article=article)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    


@app.route("/forum" , methods=['GET', 'POST'])
def forum():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({'username': payload['id']})
        if request.method == 'POST':
            judul = request.form['judul']
            konten = request.form['konten']
            timezone = pytz.timezone('Asia/Jakarta')
            current_datetime = datetime.now(timezone)
            post_date = current_datetime.strftime('%d/%m/%y - %H:%M')
            timestamp = current_datetime.timestamp()
            doc = {
                "username":user_info['username'],
                "nama_lengkap":user_info['name'],
                "foto_profil": user_info['profile_pic_real'],
                "role":user_info['role'],
                "judul":judul,
                "konten":konten,
                "post_data":post_date,
                "isCompleted":"false",
                "timestamp": timestamp,
            }
            db.forums.insert_one(doc)
            return redirect(url_for('forum'))
        forums = list(db.forums.find().sort("timestamp", -1))
        return render_template("forum.html",user_info=user_info,forums=forums)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))
    
@app.route('/forum/<id>')
def isi_forum(id):
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user.find_one({"username": payload["id"]})
        forum = db.forums.find_one({'_id': ObjectId(id)})
        user = db.user.find_one({"username": forum["username"]})
        forum['nama_lengkap'] = user['name']
        forum['foto_profil'] = user['profile_pic_real']
        comments = list(db.comments.find({"thread_id": id}))
        for comment in comments:
            user = db.user.find_one({"username": comment["username"]})
            comment['nama_lengkap'] = user['name']
            comment['foto_profil'] = user['profile_pic_real']
        return render_template("isi_forum.html",user_info=user_info,forum=forum,comments=comments)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))
    
@app.route('/user_forum_komen', methods=['POST'])
def user_forum_komen():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user.find_one({"username": payload["id"]})
        id = request.form['id']
        komen = request.form['komen']
        timezone = pytz.timezone('Asia/Jakarta')
        current_datetime = datetime.now(timezone)
        post_date = current_datetime.strftime('%d/%m/%y - %H:%M')
        timestamp = current_datetime.timestamp()
        doc = {
                "username":user_info['username'],
                "nama_lengkap":user_info['name'],
                "foto_profil": user_info['profile_pic_real'],
                "role":user_info['role'],
                "thread_id": id,
                "komen":komen,
                "post_data":post_date,
                "timestamp": timestamp,
            }
        db.comments.insert_one(doc)
        return redirect(url_for("isi_forum", id=id))
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))
    
@app.route('/edit_forum_post', methods=['POST'])
def edit_forum_post():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user.find_one({"username": payload["id"]})
        id = request.form['id']
        judul = request.form['judul']
        print(judul)
        konten = request.form['konten']
        db.forums.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"judul": judul, "konten": konten}}
        )
        return redirect(url_for("isi_forum", id=id))
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))
    
@app.route('/delete_forum_post', methods=['POST'])
def delete_forum_post():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user.find_one({"username": payload["id"]})
        id = request.form['id']
        db.forums.delete_one({'_id': ObjectId(id)})
        db.comments.delete_many({"thread_id": id})
        return redirect(url_for("forum"))
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))
    
@app.route('/close_forum_post', methods=['POST'])
def close_forum_post():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user.find_one({"username": payload["id"]})
        id = request.form['id']
        db.forums.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"isCompleted": "true"}}
        )
        return redirect(url_for("isi_forum", id=id))
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))

    

@app.route('/edit_komen', methods=['POST'])
def edit_komen():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user.find_one({"username": payload["id"]})
        id = request.form['id']
        url_id = request.form['url_id']
        komen = request.form['komen']
        db.comments.update_one(
            {"_id": ObjectId(id)},
            {"$set": { "komen": komen}}
        )
        return redirect(url_for("isi_forum", id=url_id))
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))
    
@app.route('/delete_komen', methods=['POST'])
def delete_komen():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_info = db.user.find_one({"username": payload["id"]})
        id = request.form['id']
        url_id = request.form['url_id']
        db.comments.delete_one({'_id': ObjectId(id)})
        return redirect(url_for("isi_forum", id=url_id))
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))
    
@app.route("/riwayat_forum")
def riwayat_forum():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({'username': payload['id']})
        forums = list(db.forums.find({'username': user_info['username']}).sort('timestamp', -1)) 
        for forum in forums:
            forum['jumlah_komen'] = db.comments.count_documents({'thread_id': str(forum['_id'])})
        return render_template("riwayat_forum.html", user_info=user_info,forums=forums)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))
    

    
@app.route("/produk")
def produk():
    token_receive = request.cookies.get("mytoken")
    try:
        if token_receive:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.user.find_one({'username': payload['id']})
        else:
            user_info = None

        query = request.args.get('query', '')
        if query:
            products = db.products.find({'nama_produk': {'$regex': query, '$options': 'i'}})
        else:
            products= db.products.find().sort("tanggal", -1)
        return render_template("produk.html",user_info=user_info,products=products)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    
@app.route("/riwayat_pesanan")
def riwayat_pesanan():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({'username': payload['id']})
        transactions = list(db.transaksi.find({'username': user_info['username']}).sort('tanggal', -1)) 
        total_transactions = len(transactions) + 1
        for transaction in transactions:
            tanggal_asli = datetime.fromisoformat(transaction['tanggal']).date()
            transaction['tanggal'] = tanggal_asli.strftime('%d/%m/%Y')
            transaction['nama_produk'] = db.products.find_one({'_id': ObjectId(transaction['product_id'])})['nama_produk']
            testimonial = db.testimoni.find_one({'transaction_id': str(transaction['_id'])})
            transaction['ulasan_produk'] = testimonial['ulasan'] if testimonial else None
        return render_template("riwayat_pesanan.html",user_info=user_info,transactions=transactions,total_transactions=total_transactions)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))
    

@app.route('/kirim_testimoni', methods=['POST'])
def kirim_testimoni():
    token_receive = request.cookies.get("mytoken")
    try:
        jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        id = request.form['id']
        ulasan_produk = request.form['ulasan_produk']
        transaction =  db.transaksi.find_one({'_id': ObjectId(id)})
        product = db.products.find_one({'_id': ObjectId(transaction['product_id'])})['nama_produk']
        current_date = datetime.now().isoformat()
        doc = {
                "transaction_id" : str(transaction['_id']),
                "username" : transaction['username'],
                "nama_pembeli" : transaction['nama_pembeli'],
                "alamat_pembeli" : transaction['alamat_pembeli'],
                "no_pembeli" : transaction['nomor_telepon'],
                "produk_yang_dibeli" : product,
                "ulasan":ulasan_produk,
                "tanggal": current_date,
            }
        
        db.testimoni.insert_one(doc)
        db.transaksi.update_one({'_id': ObjectId(id)}, {'$set': {'status': 'selesai'}})
        return redirect(url_for('riwayat_pesanan'))
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))
    

@app.route("/bayar", methods=['GET', 'POST'])
def bayar():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({'username': payload['id']})
        if request.method == 'GET':
            quantity = request.args.get('quantity', default=1, type=int)
            product_id = request.args.get('product_id')
            product = db.products.find_one({'_id': ObjectId(product_id)})
            price = int(product['harga_produk'])
            print(price)
            return render_template("bayar.html", user_info=user_info, product=product, quantity=quantity, product_id=product_id, price=price)
        elif request.method == 'POST':
           today = datetime.now()
           mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
           username = db.user.find_one({'username': payload['id']})['username']
           quantity = int(request.form['quantity'])
           product_id = request.form['product_id']
           nama_pembeli = request.form['nama_pembeli']
           alamat_pembeli = request.form['alamat_pembeli']
           nomor_telepon = request.form['nomor_telepon']
           catatan_pembelian = request.form['catatan_pembelian']
           product = db.products.find_one({'_id': ObjectId(product_id)})
           harga_per_produk = int(product['harga_produk'])
           total_harga = quantity * harga_per_produk
           file = request.files['bukti_pembayaran']
           filename = secure_filename(file.filename)
           extension = filename.split(".")[-1]
           file_path = f"administrator/assets/image/bukti-{username}-{mytime}.{extension}"
           file.save("./static/" + file_path)
           current_date = datetime.now().isoformat()
           doc = {
            "username" : username,
            "product_id":product_id,
            "quantity" : quantity,
            "nama_pembeli" : nama_pembeli,
            "alamat_pembeli" : alamat_pembeli,
            "nomor_telepon" : nomor_telepon,
            "catatan_pembelian" : catatan_pembelian,
            "total_harga" : total_harga,
            "bukti_pembayaran" : file_path,
            "tanggal": current_date,
            "status": "pending",

          }
           db.transaksi.insert_one(doc)
           return jsonify({'message': 'Order placed successfully'}), 200
         
        
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("login"))

@app.route("/admin_reg")
def admin_register():
    token_receive = request.cookies.get("mytoken")
    try:
        if token_receive:
            payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
            user_info = db.user.find_one({'username': payload['id']})
            if user_info:
                # Jika pengguna sudah login, arahkan ke halaman lain
                return redirect(url_for('home'))
        
        # Jika pengguna belum login, tampilkan halaman registrasi admin
        return render_template("admin_register.html")
    
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return render_template("admin_register.html")


@app.route("/admin_signup", methods=["POST"])
def admin_signup():
    username_receive = request.form["username"]
    nama_receive = request.form["nama_lengkap"]
    pw_receive = request.form["password"]
    adminkey_receive = request.form["admin_key"]
    pw_hash = hashlib.sha256(pw_receive.encode("utf-8")).hexdigest()

    user_exists = bool(db.user.find_one({"username": username_receive}))
    if user_exists:
        return jsonify({"result": "error_uname", "msg": f"An account with username {username_receive} is already exists. Please Login!"})
    elif adminkey_receive != ADMIN_KEY:
        return jsonify({"result": "error_akey", "msg": f"Admin key yang anda masukkan salah!"})
    else:
        doc = {
        "username": username_receive,                              
        "name": nama_receive,
        "password": pw_hash,                                      
        "profile_pic_real": "profile_pics/profile_placeholder.png", 
        "profile_info": "",
        "role": "admin"                                          
        }
        db.user.insert_one(doc)
        return jsonify({"result": "success"})
    

@app.route("/user_signup", methods=["POST"])
def user_signup():
    username_receive = request.form["username"]
    nama_receive = request.form["nama_lengkap"]
    pw_receive = request.form["password"]
    pw_hash = hashlib.sha256(pw_receive.encode("utf-8")).hexdigest()

    user_exists = bool(db.user.find_one({"username": username_receive}))
    if user_exists:
        return jsonify({"result": "error_uname", "msg": f"An account with username {username_receive} is already exists. Please Login!"})
    else:
        doc = {
        "username": username_receive,                              
        "name": nama_receive,
        "password": pw_hash,                                      
        "profile_pic_real": "profile_pics/profile_placeholder.png", 
        "profile_info": "",
        "role": "member"                                          
        }
        db.user.insert_one(doc)
        return jsonify({"result": "success"})
    

@app.route("/sign_in", methods=["POST"])
def sign_in():
    # Sign in
    username_receive = request.form["username_give"]
    password_receive = request.form["password_give"]
    pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
    result = db.user.find_one(
        {
            "username": username_receive,
            "password": pw_hash,
        }
    )
    print(result)
    if result:
        payload = {
            "id": username_receive,
            # the token will be valid for 24 hours
            "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
            "role": result["role"],
        }
        print(payload)
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify(
            {
                "result": "success",
                "token": token,
            }
        )
    # Let's also handle the case where the id and
    # password combination cannot be found
    else:
        return jsonify(
            {
                "result": "fail",
                "msg": "Kami tidak dapat menemukan pengguna dengan kombinasi username/password tersebut.",
            }
        )
    
@app.route("/profil/<username>")
def user(username):
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        status = username == payload["id"]  
        user_info = db.user.find_one({'username': payload['id']})
        user_data = db.user.find_one({"username": username}, {"_id": False})
        return render_template("profil.html", user_info=user_info, user_data=user_data,status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route("/update_profile", methods=["POST"])
def save_img():
    token_receive = request.cookies.get("mytoken")
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload["id"]
        name_receive = request.form["name_give"]
        about_receive = request.form["about_give"]
        new_doc = {
            "name": name_receive, 
            "profile_info": about_receive}
        
        if "file_give" in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"profile_pics/{username}.{extension}"
            file.save("./static/" + file_path)
            new_doc["profile_pic"] = filename
            new_doc["profile_pic_real"] = file_path

        db.user.update_one(
            {"username": payload["id"]}, 
            {"$set": new_doc})
        return jsonify({"result": "success", "msg": "Profil Diperbarui!"})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))
    

@app.route("/administrator/index")
@admin_required
def admin_home():
    articles_count = db.articles.count_documents({})
    products_count = db.products.count_documents({})
    transactions_count = db.transaksi.count_documents({})
    testimony_count = db.testimoni.count_documents({})
    pipeline = [
    {
        '$match': {
            'status': 'selesai'
        }
    },
    {
        '$group': {
            '_id': None,
            'total_harga': {'$sum': '$total_harga'}
        }
    }
    
    ]
    result = db.transaksi.aggregate(pipeline)
    income = 0
    for doc in result:
        income = doc['total_harga']
        break
    thread_count = db.forums.count_documents({})
    contact_count = db.hubungi.count_documents({})
    return render_template("administrator/index.html",articles_count=articles_count, products_count = products_count, transactions_count = transactions_count,testimony_count=testimony_count,income=income,thread_count=thread_count,contact_count=contact_count)

@app.route("/administrator/artikel")
@admin_required
def admin_artikel():
    articles= db.articles.find()
    return render_template("administrator/artikel.html",articles=articles)

@app.route('/tambah_artikel', methods=['POST'])
@admin_required
def tambah_artikel():
    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
    judul =request.form['nama_artikel']
    file = request.files['gambar_artikel']
    filename = secure_filename(file.filename)
    extension = filename.split(".")[-1]
    file_path = f"administrator/assets/image/article-{mytime}.{extension}"
    file.save("./static/" + file_path)
    keterangan_gambar =request.form['keterangan_gambar']
    keterangan_artikel =request.form['keterangan_artikel']
    current_date = datetime.now().isoformat()
    doc = {
        "judul_artikel" : judul,
        "gambar_artikel" : file_path,
        "keterangan_gambar" : keterangan_gambar,
        "keterangan_artikel" : keterangan_artikel,
        "tanggal": current_date,
    }
    db.articles.insert_one(doc)
    return redirect(url_for('admin_artikel'))


@app.route('/edit_artikel', methods=['POST'])
@admin_required
def edit_artikel():
    id =request.form['id']
    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
    judul =request.form['nama_artikel']
    keterangan_gambar =request.form['keterangan_gambar']
    keterangan_artikel =request.form['keterangan_artikel']
    new_doc = {
        "judul_artikel" : judul,
        "keterangan_gambar" : keterangan_gambar,
        "keterangan_artikel" : keterangan_artikel,
        }
    
    if 'gambar_artikel' in request.files and request.files['gambar_artikel'].filename != '':
        article = db.articles.find_one({'_id': ObjectId(id)})
        foto_lama = article.get('gambar_artikel', '')

        # Menghapus gambar lama
        if foto_lama:
            old_file_path = os.path.abspath("./static/" + foto_lama)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        file = request.files['gambar_artikel']
        print(file)
        filename = secure_filename(file.filename)
        extension = filename.split(".")[-1]
        file_path = f"administrator/assets/image/article-{mytime}.{extension}"
        file.save("./static/" + file_path)
        new_doc["gambar_artikel"] = file_path
    else:
        pass
    db.articles.update_one(
            {'_id': ObjectId(id)}, 
            {"$set": new_doc})
    return redirect(url_for('admin_artikel'))


@app.route('/delete_artikel', methods=['POST'])
@admin_required
def delete_artikel():
    id =request.form['id']
    article = db.articles.find_one({'_id': ObjectId(id)})
   
    if article:
        foto = article.get('gambar_artikel', '')
        if foto:
            file_path = os.path.abspath("./static/" + foto)
            if os.path.exists(file_path):
                os.remove(file_path)
        db.articles.delete_one({'_id': ObjectId(id)})
    else:
        pass
    return redirect(url_for('admin_artikel'))



@app.route("/administrator/produk")
@admin_required
def admin_produk():
    products= db.products.find()
    return render_template("administrator/produk.html", products = products)



@app.route('/tambah_produk', methods=['POST'])
@admin_required
def tambah_produk():
    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
    nama_produk =request.form['nama_produk']
    file = request.files['gambar_produk']
    filename = secure_filename(file.filename)
    extension = filename.split(".")[-1]
    file_path = f"administrator/assets/image/product-{mytime}.{extension}"
    file.save("./static/" + file_path)
    deskripsi_produk =request.form['deskripsi_produk']
    harga_produk =int(request.form['harga_produk'])
    stok_produk = int(request.form['stok'])

    current_date = datetime.now().isoformat()
    doc = {
        "nama_produk" : nama_produk,
        "gambar_produk" : file_path,
        "deskripsi_produk" : deskripsi_produk,
        "harga_produk" : harga_produk,
        "stok_produk" : stok_produk,
        "tanggal": current_date,
    }
    db.products.insert_one(doc)
    return redirect(url_for('admin_produk'))


@app.route('/edit_produk', methods=['POST'])
@admin_required
def edit_produk():
    id =request.form['id']
    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
    nama_produk =request.form['nama_produk']
    deskripsi_produk =request.form['deskripsi_produk']
    harga_produk =int(request.form['harga_produk'])
    stok_produk = int(request.form['stok'])

    current_date = datetime.now().isoformat()
    new_doc = {
        "nama_produk" : nama_produk,
        "deskripsi_produk" : deskripsi_produk,
        "harga_produk" : harga_produk,
        "stok_produk" : stok_produk,
        "tanggal": current_date,
        }
    
    if 'gambar_produk' in request.files and request.files['gambar_produk'].filename != '':
        product = db.products.find_one({'_id': ObjectId(id)})
        foto_lama = product.get('gambar_produk', '')

        # Menghapus gambar lama
        if foto_lama:
            old_file_path = os.path.abspath("./static/" + foto_lama)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)

        file = request.files['gambar_produk']
        filename = secure_filename(file.filename)
        extension = filename.split(".")[-1]
        file_path = f"administrator/assets/image/product-{mytime}.{extension}"
        file.save("./static/" + file_path)
        new_doc["gambar_produk"] = file_path
    else:
        pass
    db.products.update_one(
            {'_id': ObjectId(id)}, 
            {"$set": new_doc})
    return redirect(url_for('admin_produk'))


@app.route('/delete_produk', methods=['POST'])
@admin_required
def delete_produk():
    id = request.form['id']
    product = db.products.find_one({'_id': ObjectId(id)})
    if product:
        foto = product.get('gambar_produk', '')
        if foto:
            file_path = os.path.abspath("./static/" + foto)
            if os.path.exists(file_path):
                os.remove(file_path)
        db.products.delete_one({'_id': ObjectId(id)})
    else:
        pass
    return redirect(url_for('admin_produk'))



@app.route("/administrator/transaksi")
@admin_required
def admin_transaksi():
    transactions= list(db.transaksi.find())
    for transaction in transactions:
        transaction['nama_produk'] = db.products.find_one({'_id': ObjectId(transaction['product_id'])})['nama_produk']
    return render_template("administrator/transaksi.html", transactions = transactions)

@app.route('/terima_pembelian', methods=['POST'])
@admin_required
def terima_pembelian():
    id = request.form['id']
    catatan_admin = request.form['catatan_admin']
    transaction =  db.transaksi.find_one({'_id': ObjectId(id)})
    quantity = transaction['quantity']

    db.transaksi.update_one({'_id': ObjectId(id)}, {'$set': {'status': 'diterima', 'catatan_admin': catatan_admin}})
    db.products.update_one({'_id': ObjectId(transaction['product_id'])}, {'$inc': {'stok_produk': -quantity}})

    return redirect(url_for('admin_transaksi'))


@app.route('/tolak_pembelian', methods=['POST'])
@admin_required
def tolak_pembelian():
    id = request.form['id']
    catatan_admin = request.form['catatan_admin']
    db.transaksi.update_one({'_id': ObjectId(id)}, {'$set': {'status': 'ditolak', 'catatan_admin': catatan_admin}})
    return redirect(url_for('admin_transaksi'))

@app.route('/kirim_pembelian', methods=['POST'])
@admin_required
def kirim_pembelian():
    id = request.form['id']
    catatan_admin = request.form['catatan_admin']
    db.transaksi.update_one({'_id': ObjectId(id)}, {'$set': {'status': 'dikirim', 'catatan_admin': catatan_admin}})
    return redirect(url_for('admin_transaksi'))


@app.route("/administrator/testimoni")
@admin_required
def admin_testimoni():
    testimonies= db.testimoni.find()
    return render_template("administrator/testimoni.html", testimonies = testimonies)

@app.route("/administrator/forum")
@admin_required
def admin_forum():
    forums= db.forums.find()
    return render_template("administrator/forum.html", forums = forums)

@app.route('/delete_thread_admin_side', methods=['POST'])
@admin_required
def delete_thread_admin_side():
    id =request.form['id']
    db.forums.delete_one({'_id': ObjectId(id)})
    db.comments.delete_many({"thread_id": id})
    return redirect(url_for('admin_forum'))


@app.route("/administrator/hubungi")
@admin_required
def admin_hubungi():
    contacts = db.hubungi.find()
    return render_template("administrator/hubungi.html", contacts = contacts)


@app.route('/delete_contact', methods=['POST'])
@admin_required
def delete_contact():
    id =request.form['id']
    db.hubungi.delete_one({'_id': ObjectId(id)})
    return redirect(url_for('admin_hubungi'))



if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)