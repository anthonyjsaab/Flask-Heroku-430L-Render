from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

from flask_cors import CORS
app = Flask(__name__)
app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'postgres://wkjvumxnirhcbx:046c40445f3e128229090cb1b25f84769559e8dd215a1ac9b13137af47812ea9@ec2-34-206-148-196.compute-1.amazonaws.com:5432/dfsi1fcrvq2qaa'
CORS(app)
db = SQLAlchemy(app)



class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usd_amount = db.Column(db.Float)
    lbp_amount = db.Column(db.Float)
    usd_to_lbp = db.Column(db.Boolean)

    def __init__(self, usd_amount, lbp_amount, usd_to_lbp):
        self.usd_to_lbp = usd_to_lbp
        self.lbp_amount = lbp_amount
        self.usd_amount = usd_amount


@app.route('/transaction', methods=['POST'])
def transaction():
    try:
        print(request.data)
        print(request.json)
        usd_amount = request.json["usd_amount"]
        lbp_amount = request.json["lbp_amount"]
        usd_to_lbp = request.json["usd_to_lbp"]
        new_transaction = Transaction(usd_amount, lbp_amount, usd_to_lbp)
        db.session.add(new_transaction)
        db.session.commit()
        return jsonify({'Success': True})
    except:
        print("huh")
        return jsonify({'Success': False})


@app.route('/exchangeRate', methods=['GET'])
def exchangeRate():
    allTransactions = Transaction.query.all()
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
                                              