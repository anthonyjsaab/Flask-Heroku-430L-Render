import datetime
import json

import jwt
from flask import Flask, request, jsonify, abort, Response
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from db_config import DB_CONFIG
from flask_cors import CORS
import pytz

SECRET_KEY = "b'|\xe7\xbfU3`\xc4\xec\xa7\xa9zf:}\xb5\xc7\xb9\x139^3@Dv'"
app = Flask(__name__)
app.config[
    'SQLALCHEMY_DATABASE_URI'] = DB_CONFIG
db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)
CORS(app)

from model.user import User, user_schema
from model.transaction import Transaction, transactions_schema, transaction_schema
from model.offer import Offer, offer_schema, offers_schema


def timenow():
    return datetime.datetime.now(pytz.timezone("Asia/Beirut"))


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
        'exp': timenow() + datetime.timedelta(days=4),
        'iat': timenow(),
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
        Transaction.added_date.between(timenow() - datetime.timedelta(hours=72),
                                       timenow())).all()
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
    try:
        user_name = request.json["user_name"]
        password = request.json["password"]
        phone = request.json["phone"]
    except:
        abort(400)
    if User.query.filter_by(user_name=user_name).first():
        abort(403)
    new_user = User(user_name, phone, password)
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


@app.route('/graph/<type>/<period>', methods=['GET'])
def get_points(type, period):
    periods = {'1day': (24, 30), '5days': (120, 60), '30days': (720, 1440)}
    try:
        assert type in ["usd_to_lbp", "lbp_to_usd"], "Invalid type"
        interval_in_minutes = periods[period][1]
        past_hours_amount = periods[period][0]
    except:
        abort(400)
        return
    usd_to_lbp = type == "usd_to_lbp"
    start_date = timenow() - datetime.timedelta(hours=past_hours_amount)
    # print(start_date)
    relevant_transactions = Transaction.query.filter(
        Transaction.added_date.between(start_date, timenow()), Transaction.usd_to_lbp == usd_to_lbp)

    graph_points = []
    for i in range(int(past_hours_amount * 60 / interval_in_minutes) + 1):
        center_date = start_date + datetime.timedelta(minutes=i * interval_in_minutes)
        mini_start_date = center_date - datetime.timedelta(seconds=interval_in_minutes * 30)
        mini_end_date = center_date + datetime.timedelta(seconds=interval_in_minutes * 30)
        # print(mini_start_date, mini_end_date)
        transactions_to_summarize = relevant_transactions.filter(
            Transaction.added_date.between(mini_start_date, mini_end_date)).all()
        if transactions_to_summarize:
            summ = 0
            for transac in transactions_to_summarize:
                summ += transac.lbp_amount / transac.usd_amount
            graph_points.append((i, summ / len(transactions_to_summarize)))
    return Response(json.dumps(graph_points), mimetype='application/json')


@app.route('/offer', methods=['POST'])
def offer_POST():
    maybe_token = extract_auth_token(request)
    if not maybe_token:
        abort(403)
        return
    else:
        try:
            user_id = decode_token(maybe_token)
        except (jwt.ExpiredSignatureError, jwt.InvalidSignatureError):
            abort(403)
            return
        try:
            usd_amount = float(request.json["usd_amount"])
            rate = float(request.json["rate"])
            usd_to_lbp = request.json["usd_to_lbp"]
            print(type(usd_to_lbp))
        except:
            abort(400)
            return
    new_offer = Offer(usd_amount, rate, usd_to_lbp, user_id)
    db.session.add(new_offer)
    db.session.commit()
    return jsonify(offer_schema.dump(new_offer))


@app.route('/offer/<start>/<end>', methods=['GET'])
def offer_GET(start, end):
    try:
        start, end = int(start), int(end)
    except:
        abort(400)
    all_offers = Offer.query.all()
    if end > len(all_offers) and start <= 1:
        relevant_offers = all_offers
    elif end > len(all_offers):
        relevant_offers = all_offers[:-start]
    elif start <= 1:
        relevant_offers = all_offers[-end:]
    else:
        relevant_offers = all_offers[-end:-start]
    return jsonify(offers_schema.dump(relevant_offers))
