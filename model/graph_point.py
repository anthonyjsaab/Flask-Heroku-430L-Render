from ..app import db, ma, datetime
import enum


class Period(enum.Enum):
    ONE = 'one'
    FIVE = 'five'
    MONTH = 'month'


class GraphPoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    corresponding_datetime = db.Column(db.DateTime)
    lbp_amount = db.Column(db.Float)
    usd_to_lbp = db.Column(db.Boolean)
    timeframe = db.Column(db.Enum(Period))

    def __init__(self, lbp_amount, usd_to_lbp, timeframe, corresponding_datetime):
        super(GraphPoint, self).__init__(lbp_amount=lbp_amount, usd_to_lbp=usd_to_lbp, timeframe=timeframe,
                                         corresponding_datetime=corresponding_datetime)


class GraphPointSchema(ma.Schema):
    class Meta:
        fields = ("id", "corresponding_datetime", "lbp_amount", "usd_to_lbp", "timeframe")
        model = GraphPoint


graph_point_schema = GraphPointSchema()
graph_points_schema = GraphPointSchema(many=True)
