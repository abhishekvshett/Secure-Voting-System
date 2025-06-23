from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # ✅ Needed for sessions

# Connect to MongoDB
client = MongoClient(os.getenv('MONGO_URI'))
db = client['VotingSystem']

# ✅ Home page
@app.route('/')
def index():
    return render_template('home.html')


# ✅ Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if db.Users.find_one({'email': email}):
            return "❌ User already exists. Please login."

        db.Users.insert_one({'name': name, 'email': email, 'password': password})
        return redirect(url_for('login'))  # 👈 Go to login after registering

    return render_template('register.html')


# ✅ Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = db.Users.find_one({'email': email, 'password': password})

        if user:
            session['user'] = email   # ✅ Store user session
            return redirect(url_for('vote'))
        else:
            return "❌ Invalid email or password. Please try again."

    return render_template('login.html')



# ✅ Vote (only once per user)
@app.route('/vote', methods=['GET', 'POST'])
def vote():
    user_email = session.get('user')

    # 🔒 Ensure user is logged in
    if not user_email:
        return redirect(url_for('login'))

    # 🔐 Check if already voted
    existing_vote = db.Votes.find_one({'voter': user_email})
    if existing_vote:
        return "❌ You have already voted."

    if request.method == 'POST':
        candidate = request.form['candidate']
        db.Votes.insert_one({'candidate': candidate, 'voter': user_email})
        session.clear()  # ✅ Logout after voting
        return render_template('thankyou.html')

    return render_template('vote.html')



# ✅ Results (admin only)
@app.route('/results', methods=['GET', 'POST'])
def results():
    if request.method == 'POST':
        admin_pass = request.form['admin_pass']
        if admin_pass == 'your_password':  # 🔐 Replace with your real admin password

            # 📊 Aggregate vote counts (sorted descending)
            pipeline = [
                {"$group": {"_id": "$candidate", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            results = list(db.Votes.aggregate(pipeline))

            # 🕵️‍♂️ Fetch voter info (audit log)
            votes_list = list(db.Votes.find({}, {"_id": 0, "voter": 1, "candidate": 1}))

            # 🏆 Determine winner
            winner = None
            is_tie = False
            
            if results:
                top_count = results[0]['count']
                top_candidates = [res['_id'] for res in results if res['count'] == top_count]
                
                if len(top_candidates) == 1:
                    winner = top_candidates[0]
                else:
                    is_tie = True
                    winner = ', '.join(top_candidates)

            return render_template("results.html", results=results, votes_list=votes_list, winner=winner,is_tie=is_tie)

        else:
            return "❌ Access denied. Wrong password."

    return render_template("admin_login.html")



#reset_everything
@app.route('/reset_all', methods=['GET', 'POST'])
def reset_all():
    if request.method == 'POST':
        admin_pass = request.form.get('admin_pass')
        if admin_pass == 'your_password':  # your admin password
            db.Users.delete_many({})
            db.Votes.delete_many({})
            return "✅ All users and votes have been reset. System is now clean and ready for new voting."
        else:
            return "❌ Access denied. Wrong admin password."

    return render_template("reset_all.html")



# ✅ Logout (optional)
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
