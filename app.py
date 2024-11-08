from flask import Flask, render_template, request, redirect, url_for, make_response
from datetime import datetime
from flask_socketio import SocketIO, emit
import csv

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Store user data
users = {}
comments = []
CSV_FILE = 'high_scores.csv'

def save_users_to_csv():
    """Save user and session data to a CSV file."""
    with open(CSV_FILE, 'w', newline='') as csvfile:
        fieldnames = ['username', 'current_challenge', 'start_times', 'completion_times', 'total_time', 'comment']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for user in users.values():
            writer.writerow({
                'username': user['username'],
                'current_challenge': user['current_challenge'],
                'start_times': {k: v.isoformat() if isinstance(v, datetime) else v for k, v in user['start_times'].items()},
                'completion_times': user['completion_times'],
                'total_time': user.get('total_time'),
                'comment': user['comment']
            })

def load_users_from_csv():
    """Load user and session data from a CSV file."""
    try:
        with open(CSV_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                users[row['username']] = {
                    'username': row['username'],
                    'current_challenge': int(row['current_challenge']),
                    'start_times': eval(row['start_times']),
                    'completion_times': eval(row['completion_times']),
                    'total_time': float(row['total_time']) if row['total_time'] != 'None' else None,
                    'comment': row['comment']
                }
    except FileNotFoundError:
        print("CSV file not found. Starting with an empty user list.")

def record_start_time(username, challenge):
    """Record the start time for a challenge if not already started."""
    user = users[username]
    if challenge not in user['start_times']:
        user['start_times'][challenge] = datetime.now()

def record_completion_time(username, challenge):
    """Record the completion time for a challenge."""
    user = users[username]
    if challenge not in user['completion_times']:
        start_time = user['start_times'].get(challenge)
        if start_time:
            completion_time = (datetime.now() - start_time).total_seconds()
            user['completion_times'][challenge] = completion_time
            user['total_time'] = sum(user['completion_times'].values())
            save_users_to_csv()  # Save to CSV whenever completion time is recorded

            # Sort users
            sorted_users = sorted(users.values(), key=lambda x: (
                x.get('total_time') if x.get('total_time') is not None else float('inf'),
                x['completion_times'].get('challenge_four', float('inf')),
                x['completion_times'].get('challenge_three', float('inf')),
                x['completion_times'].get('challenge_two', float('inf')),
                x['completion_times'].get('challenge_one', float('inf'))
            ))

            # Serialize datetime objects before emitting
            serializable_users = [
                {
                    **u,
                    'start_times': {k: v.isoformat() if isinstance(v, datetime) else v for k, v in u['start_times'].items()},
                    'completion_times': u['completion_times']
                }
                for u in sorted_users
            ]

            # Update the leaderboard via WebSocket
            socketio.emit('update_leaderboard', {'users': serializable_users})

@app.route('/')
def index():
    """Home page with leaderboard."""
    username = request.cookies.get('username')

    for user in users.values():
        challenges = ['challenge_one', 'challenge_two', 'challenge_three', 'challenge_four']  # Exclude challenge_five
        if all(challenge in user['completion_times'] for challenge in challenges):
            user['total_time'] = sum(user['completion_times'].values())
        else:
            user['total_time'] = None

    sorted_users = sorted(users.values(), key=lambda x: (
        x.get('total_time') if x.get('total_time') is not None else float('inf'),
        x['completion_times'].get('challenge_four', float('inf')),
        x['completion_times'].get('challenge_three', float('inf')),
        x['completion_times'].get('challenge_two', float('inf')),
        x['completion_times'].get('challenge_one', float('inf'))
    ))

    return render_template('index.html', users=users, sorted_users=sorted_users, username=username)

@app.route('/start', methods=['GET', 'POST'])
def start():
    """Handle the start modal logic."""
    if request.method == 'POST':
        username = request.form.get('name')

        # Initialize user data if not exists
        if username not in users:
            users[username] = {
                'username': username,
                'current_challenge': 1,
                'start_times': {},
                'completion_times': {},
                'comment': ''
            }

        user = users[username]
        current_challenge = user['current_challenge']
        challenge_routes = {
            1: 'challenge_one',
            2: 'challenge_two',
            3: 'challenge_three',
            4: 'challenge_four',
        }
        challenge_route = challenge_routes.get(current_challenge, 'index')

        # Set the username as a cookie
        response = make_response(redirect(url_for(challenge_route)))
        response.set_cookie('username', username)
        return response
    else:
        return render_template('start.html', username=request.cookies.get('username'))

@app.route('/challenge_one', methods=['GET', 'POST'])
def challenge_one():
    """Challenge One"""
    username = request.cookies.get('username')  # Get the username from the cookie
    if not username:
        return redirect(url_for('start'))

    record_start_time(username, 'challenge_one')

    if request.method == 'POST':
        input_username = request.form.get('username')
        password = request.form.get('password')
        if input_username.lower() == 'admin' and password.lower() == 'admin':
            record_completion_time(username, 'challenge_one')
            users[username]['current_challenge'] = 2
            return redirect(url_for('index'))
        else:
            return render_template('challenge_one.html', error="Incorrect credentials.")
    return render_template('challenge_one.html')

@app.route('/challenge_two', methods=['GET', 'POST'])
def challenge_two():
    """Challenge Two"""
    username = request.cookies.get('username')
    if not username:
        return redirect(url_for('start'))

    if users[username]['current_challenge'] < 2:
        return redirect(url_for('index'))

    record_start_time(username, 'challenge_two')

    if request.method == 'POST':
        record_completion_time(username, 'challenge_two')
        users[username]['current_challenge'] = 3
        return redirect(url_for('index'))

    return render_template('challenge_two.html')

@app.route('/challenge_three', methods=['GET', 'POST'])
def challenge_three():
    """Challenge Three: Hidden Authentication"""
    username = request.cookies.get('username')
    if not username:
        return redirect(url_for('start'))

    if users[username]['current_challenge'] < 3:
        return redirect(url_for('index'))

    record_start_time(username, 'challenge_three')

    authenticated = request.args.get('authenticated', 'False').lower()
    form_username = request.args.get('username', '').lower()
    form_password = request.args.get('password', '').lower()

    if authenticated == 'true':
        record_completion_time(username, 'challenge_three')
        users[username]['current_challenge'] = 4
        return redirect(url_for('index'))
    elif form_username == 'admin' and form_password == 'password':
        error = "Authentication method not accepted.<br>look at the url!"
        return render_template('challenge_three.html', error=error)
    else:
        return render_template('challenge_three.html')

@app.route('/challenge_four', methods=['GET', 'POST'])
def challenge_four():
    """Challenge Four: Cookie Authentication"""
    username = request.cookies.get('username')
    if not username:
        return redirect(url_for('start'))

    if users[username]['current_challenge'] < 4:
        return redirect(url_for('index'))

    record_start_time(username, 'challenge_four')

    authenticated_cookie = request.cookies.get('authenticated', 'False').lower()
    if authenticated_cookie == 'true':
        record_completion_time(username, 'challenge_four')
        users[username]['current_challenge'] = 5
        return redirect(url_for('index'))
    else:
        if request.method == 'POST':
            error = "Authentication method not accepted."
            resp = make_response(render_template('challenge_four.html', error=error))
            resp.set_cookie('authenticated', 'False')
            return resp
        else:
            resp = make_response(render_template('challenge_four.html'))
            resp.set_cookie('authenticated', 'False')
            return resp

@app.route('/challenge_five', methods=['GET', 'POST'])
def challenge_five():
    """Challenge Five: Submit a Comment"""
    username = request.cookies.get('username')
    if not username:
        return redirect(url_for('start'))

    if users[username]['current_challenge'] < 5:
        return redirect(url_for('index'))

    if request.method == 'POST':
        comment = request.form.get('comment')
        if comment:
            users[username]['comment'] = comment
            users[username]['current_challenge'] = 5  # Mark challenge as completed

            # Emit the update via WebSocket with serializable data
            serializable_users = [
                {
                    **u,
                    'start_times': {k: v.isoformat() if isinstance(v, datetime) else v for k, v in u['start_times'].items()},
                    'completion_times': u['completion_times']
                }
                for u in users.values()
            ]

            socketio.emit('update_leaderboard', {'users': serializable_users})
            save_users_to_csv()  # Save to CSV whenever a comment is added
            return redirect(url_for('index'))
    return render_template('challenge_five.html')

@app.route('/logout')
def logout():
    """Log out the user"""
    resp = make_response(redirect(url_for('start')))
    resp.set_cookie('username', '', expires=0)  # Clear the username cookie
    return resp

if __name__ == "__main__":
    load_users_from_csv()  # Load user data from CSV on server start
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)
