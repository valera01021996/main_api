from flask import Flask
from routes.alert_routes import alert_bp
from routes.solved_routes import solved_bp
from routes.acknowledged_routes import acknowledged_bp

app = Flask(__name__)

app.secret_key = 'your_secret_key_here'

app.register_blueprint(alert_bp)
app.register_blueprint(solved_bp)
app.register_blueprint(acknowledged_bp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
