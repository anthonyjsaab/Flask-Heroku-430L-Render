import datetime
import jwt
from flask import Flask, request, jsonify, abort
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from db_config import DB_CONFIG

SECRET_KEY = "b'|\xe7\xbfU3`\xc4\xec\xa7\xa9zf:}\xb5\xc7\xb9\x139^3@Dv'"
app = Flask(__name__)
app.config[
    'SQLALCHEMY_DATABASE_URI'] = DB_CONFIG
db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)

from model.user import User, user_schema
from model.transaction import Transaction, transactions_schema, transaction_schema


def extract_auth_token(authenticated_request):
    auth_header = authenticated_request.headers.get('Authorization')
    if auth_header:
        return auth_header.split(" ")[1]
    else:
        return None


def decode_token(token):
    payload = jwt.decode(token, SECRET_KEY, 'HS256')
    return payload['sub']


def create_token(user_id):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=4),
        'iat': datetime.datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm='HS256'
    )


@app.route('/transaction', methods=['POST'])
def transaction_POST():
    maybe_token = extract_auth_token(request)
    if not maybe_token:
        user_id = None
    else:
        try:
            user_id = decode_token(maybe_token)
        except (jwt.ExpiredSignatureError, jwt.InvalidSignatureError):
            abort(403)
            return
    usd_amount = request.json["usd_amount"]
    lbp_amount = request.json["lbp_amount"]
    usd_to_lbp = request.json["usd_to_lbp"]
    new_transaction = Transaction(usd_amount, lbp_amount, usd_to_lbp, user_id)
    db.session.add(new_transaction)
    db.session.commit()
    return jsonify(transaction_schema.dump(new_transaction))


@app.route('/transaction', methods=['GET'])
def transaction_GET():
    maybe_token = extract_auth_token(request)
    if not maybe_token:
        abort(403)
        return
    try:
        user_id = decode_token(maybe_token)
    except (jwt.ExpiredSignatureError, jwt.InvalidSignatureError):
        abort(403)
        return
    relevant_transactions = Transaction.query.filter_by(user_id=user_id)
    return jsonify(transactions_schema.dump(relevant_transactions))


@app.route('/exchangeRate', methods=['GET'])
def exchangeRate():
    allTransactions = Transaction.query.filter(
        Transaction.added_date.between(datetime.datetime.now() - datetime.timedelta(hours=72),
                                       datetime.datetime.now())).all()
    usd_sell_rates_sum = 0
    usd_buy_rates_sum = 0
    total_sells = 0
    total_buys = 0

    for transact in allTransactions:
        current_rate = transact.lbp_amount / transact.usd_amount

        # Selling USD
        if transact.usd_to_lbp:
            usd_sell_rates_sum += current_rate
            total_sells += 1
        # Buying USD
        else:
            usd_buy_rates_sum += current_rate
            total_buys += 1

    return_json = {"usd_to_lbp": None, "lbp_to_usd": None}

    if total_sells:
        return_json["usd_to_lbp"] = int(usd_sell_rates_sum * 100 / total_sells) / 100
    if total_buys:
        return_json["lbp_to_usd"] = int(usd_buy_rates_sum * 100 / total_buys) / 100

    return jsonify(return_json)


@app.route('/user', methods=['POST'])
def signup():
    user_name = request.json["user_name"]
    if User.query.filter_by(user_name=user_name).first():
        abort(403)
    password = request.json["password"]
    new_user = User(user_name, password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify(user_schema.dump(new_user))


@app.route('/authentication', methods=['POST'])
def get_token():
    if "user_name" not in request.json or "password" not in request.json:
        abort(400)
        return
    user_name = request.json["user_name"]
    password = request.json["password"]
    relevantUser = User.query.filter_by(user_name=user_name).first()
    if not relevantUser:
        abort(403)
        return
    if not bcrypt.check_password_hash(relevantUser.hashed_password, password):
        abort(403)
        return
    return jsonify({'token': create_token(relevantUser.id)})
