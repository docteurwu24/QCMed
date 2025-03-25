# --- START OF FILE server.py ---

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os # Import os to construct the database path reliably

# --- Configuration ---
app = Flask(__name__)

# --- Database Configuration (PostgreSQL for Production, SQLite for Local Fallback) ---
# Render provides the PostgreSQL URL in the DATABASE_URL environment variable.
# For local development, we fall back to the SQLite database.
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Fix for newer SQLAlchemy versions requiring "postgresql://"
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    print("Using PostgreSQL database (Production/Render).")
else:
    print("DATABASE_URL not found or invalid, using local SQLite database (Development).")
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'leaderboard.db')
    DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model ---
class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pseudo = db.Column(db.String(50), nullable=False)
    qcm_id = db.Column(db.String(100), nullable=False) # Increased length just in case theme names get long
    # --- CORRECTION HERE: Changed Integer to Float ---
    score = db.Column(db.Float, nullable=False)
    # -------------------------------------------------

    # Ensure uniqueness for a combination of pseudo and QCM ID
    __table_args__ = (db.UniqueConstraint('pseudo', 'qcm_id', name='unique_pseudo_qcm_score'),)

# --- Database Initialization ---
# Use app.app_context() to ensure context is available
with app.app_context():
    # Check if the database file exists before creating tables
    # This isn't strictly necessary with create_all but can be useful
    # if os.path.exists(DATABASE_PATH):
    #     print(f"Database found at: {DATABASE_PATH}")
    # else:
    #     print(f"Database not found, will be created at: {DATABASE_PATH}")

    try:
        db.create_all()
        print("Database tables checked/created successfully.")
    except Exception as e:
        print(f"Error during database initialization: {e}")
        # Depending on the error, you might want to exit or handle differently
        # For now, we'll let the app continue, but log the error.


# --- API Routes ---

# Add a score (or update it if the new score is higher)
@app.route('/add_score', methods=['POST'])
def add_score():
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 415 # Use 415 Unsupported Media Type

    data = request.json
    pseudo = data.get('pseudo')
    qcm_id = data.get('qcm_id')
    # --- CORRECTION HERE: Ensure score is treated as float ---
    score_value = data.get('score')
    # --------------------------------------------------------

    # Basic validation
    if not pseudo or not isinstance(pseudo, str) or len(pseudo.strip()) == 0:
        return jsonify({'error': 'Invalid or missing pseudo'}), 400
    if not qcm_id or not isinstance(qcm_id, str) or len(qcm_id.strip()) == 0:
        return jsonify({'error': 'Invalid or missing qcm_id'}), 400
    if score_value is None:
         return jsonify({'error': 'Missing score'}), 400

    # Try converting score to float for consistent handling
    try:
        score = float(score_value)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid score format, must be a number'}), 400


    # Find existing score for this user and QCM
    existing_score = Score.query.filter_by(pseudo=pseudo, qcm_id=qcm_id).first()

    try:
        if existing_score:
            # User exists, check if the new score is better
            if score > existing_score.score:
                existing_score.score = score
                db.session.commit()
                print(f"Updated score for {pseudo} on {qcm_id} to {score}")
                return jsonify({'message': 'Score updated successfully!', 'pseudo': pseudo, 'qcm_id': qcm_id, 'score': score}), 200
            else:
                print(f"Score not improved for {pseudo} on {qcm_id} ({score} vs existing {existing_score.score})")
                return jsonify({'message': 'Existing score is higher or equal.', 'existing_score': existing_score.score}), 200 # 200 OK is fine, just indicate no change
        else:
            # No existing score, create a new entry
            new_score = Score(pseudo=pseudo, qcm_id=qcm_id, score=score)
            db.session.add(new_score)
            db.session.commit()
            print(f"Added new score for {pseudo} on {qcm_id}: {score}")
            return jsonify({'message': 'Score added successfully!', 'pseudo': pseudo, 'qcm_id': qcm_id, 'score': score}), 201 # 201 Created is appropriate here
    except Exception as e:
        db.session.rollback() # Rollback transaction on error
        print(f"Database error on add/update score: {e}")
        return jsonify({'error': 'Database operation failed', 'details': str(e)}), 500


# Get the leaderboard for a specific QCM
@app.route('/leaderboard/<string:qcm_id>', methods=['GET'])
def get_leaderboard(qcm_id):
    if not qcm_id or len(qcm_id.strip()) == 0:
        return jsonify({'error': 'Invalid or missing qcm_id in URL'}), 400

    try:
        # Query scores, order by score descending, limit for sanity (e.g., top 100)
        scores = Score.query.filter_by(qcm_id=qcm_id).order_by(Score.score.desc()).limit(100).all()

        # Format the leaderboard data including rank
        leaderboard = [
            {'rank': i + 1, 'pseudo': s.pseudo, 'score': s.score}
            for i, s in enumerate(scores)
        ]

        print(f"Retrieved leaderboard for {qcm_id}: {len(leaderboard)} entries")
        return jsonify(leaderboard), 200
    except Exception as e:
        print(f"Database error on fetching leaderboard for {qcm_id}: {e}")
        return jsonify({'error': 'Failed to retrieve leaderboard', 'details': str(e)}), 500

# --- Main Execution (Removed for Production) ---
# The production server (Waitress/Gunicorn) will run the 'app' object directly.
# The following block is only for local development testing.
# if __name__ == '__main__':
#     print(f"Starting local development server...")
#     print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
#     # Be cautious with debug=True
#     app.run(debug=False, host='127.0.0.1', port=5000)
# --- END OF FILE server.py ---
