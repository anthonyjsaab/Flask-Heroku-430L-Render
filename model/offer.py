from app import db, ma, datetime, pytz, User


def timenow():
    return datetime.datetime.now(pytz.timezone("Asia/Beirut"))


class Offer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usd_amount = db.Column(db.Float)
    rate = db.Column(db.Float)
    usd_to_lbp = db.Column(db.Boolean)
    added_date = db.Column(db.DateTime)
    phone = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                        nullable=True)

    def __init__(self, usd_amount, rate, usd_to_lbp, user_id):
        super(Offer, self).__init__(usd_amount=usd_amount,
                                    rate=rate, usd_to_lbp=usd_to_lbp,
                                    user_id=user_id, phone=User.query.filter_by(id=user_id)[0].phone,
                                    added_date=timenow())


class OfferSchema(ma.Schema):
    class Meta:
        fields = ("id", "usd_amount", "rate", "usd_to_lbp", "user_id", "phone", "added_date")
        model = Offer


offer_schema = OfferSchema()
offers_schema = OfferSchema(many=True)
