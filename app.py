from flask import Flask, render_template, request, redirect, url_for, make_response, session
from datetime import datetime
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.secret_key = 'supersecretkey'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store user data
users = {}
comments = []

def record_start_time(username, challenge):
    """Record the start time for a challenge if not already started"""
    user = users[username]
    if challenge not in user['start_times']:
        user['start_times'][challenge] = datetime.now()

def record_completion_time(username, challenge):
    """Record the completion time for a challenge"""
    user = users[username]
    if challenge not in user['completion_times']:
        start_time = user['start_times'].get(challenge)
        if start_time:
            completion_time = (datetime.now() - start_time).total_seconds()
            user['completion_times'][challenge] = completion_time
            # Recalculate total time
            user['total_time'] = sum(user['completion_times'].values())
            # Sort users
            sorted_users = sorted(users.values(), key=lambda x: (
                x.get('total_time') if x.get('total_time') is not None else float('inf'),
                x['completion_times'].get('challenge_four', float('inf')),
                x['completion_times'].get('challenge_three', float('inf')),
                x['completion_times'].get('challenge_two', float('inf')),
                x['completion_times'].get('challenge_one', float('inf'))
            ))

            # Update the leaderboard via WebSocket
            socketio.emit('update_leaderboard', {'users': list(sorted_users)})


@app.route('/')
def index():
    """Home page with leaderboard"""
    username = session.get('username')

    # Calculate total times for users only if all challenges are completed
    for user in users.values():
        # Check if the user has completed all challenges
        challenges = ['challenge_one', 'challenge_two', 'challenge_three', 'challenge_four']
        if all(challenge in user['completion_times'] for challenge in challenges):
            user['total_time'] = sum(user['completion_times'].values())
        else:
            user['total_time'] = None

    # Sort users based on the criteria
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
    """Handle the start modal logic"""
    if request.method == 'POST':
        username = request.form.get('name')
        session['username'] = username

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

        # Determine the route for the current challenge
        challenge_routes = {
            1: 'challenge_one',
            2: 'challenge_two',
            3: 'challenge_three',
            4: 'challenge_four',
            # Add more challenges here if necessary
        }
        challenge_route = challenge_routes.get(current_challenge, 'index')

        return redirect(url_for(challenge_route))
    else:
        # If GET request, render the start template (if needed)
        return render_template('start.html', username=session.get('username'))

@app.route('/challenge_one', methods=['GET', 'POST'])
def challenge_one():
    """Challenge One"""
    username = session.get('username')
    if not username:
        return redirect(url_for('start'))

    record_start_time(username, 'challenge_one')

    if request.method == 'POST':
        input_username = request.form.get('username')
        password = request.form.get('password')
        if input_username == 'admin' and password == 'admin':
            record_completion_time(username, 'challenge_one')
            users[username]['current_challenge'] = 2
            return redirect(url_for('index'))
        else:
            return render_template('challenge_one.html', error="Incorrect credentials.")
    return render_template('challenge_one.html')

@app.route('/challenge_two', methods=['GET', 'POST'])
def challenge_two():
    """Challenge Two"""
    username = session.get('username')
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
    username = session.get('username')
    if not username:
        return redirect(url_for('start'))

    if users[username]['current_challenge'] < 3:
        return redirect(url_for('index'))

    record_start_time(username, 'challenge_three')

    # Check if 'authenticated' parameter is in the URL
    authenticated = request.args.get('authenticated', 'False')
    form_username = request.args.get('username')
    form_password = request.args.get('password')

    if authenticated == 'True':
        # User has manipulated the URL parameter
        record_completion_time(username, 'challenge_three')
        users[username]['current_challenge'] = 4
        return redirect(url_for('index'))
    elif form_username == 'admin' and form_password == 'password':
        # Incorrect authentication method
        error = "Authentication method not accepted.<br>look at the url!"
        return render_template('challenge_three.html', error=error)
    else:
        # Initial load or incorrect credentials
        return render_template('challenge_three.html')

@app.route('/challenge_four', methods=['GET', 'POST'])
def challenge_four():
    """Challenge Four: Cookie Authentication"""
    username = session.get('username')
    if not username:
        return redirect(url_for('start'))

    if users[username]['current_challenge'] < 4:
        return redirect(url_for('index'))

    record_start_time(username, 'challenge_four')

    # Check the 'authenticated' cookie
    authenticated_cookie = request.cookies.get('authenticated', 'False')
    if authenticated_cookie == 'True':
        # User has authenticated by changing the cookie
        record_completion_time(username, 'challenge_four')
        users[username]['current_challenge'] = 5  # Update to next challenge or mark as completed
        return redirect(url_for('index'))
    else:
        if request.method == 'POST':
            # Form submission received, but authentication fails
            error = "Authentication method not accepted."
            # Set the 'authenticated' cookie to 'False' in the response
            resp = make_response(render_template('challenge_four.html', error=error))
            resp.set_cookie('authenticated', 'False')
            return resp
        else:
            # Initial GET request or no valid authentication
            # Set the 'authenticated' cookie to 'False' in the response
            resp = make_response(render_template('challenge_four.html'))
            resp.set_cookie('authenticated', 'False')
            return resp

@app.route('/challenge_five', methods=['GET', 'POST'])
def challenge_five():
    """Challenge Five: Submit a Comment"""
    username = session.get('username')
    if not username:
        return redirect(url_for('start'))

    # Ensure the user is on the correct challenge
    if users[username]['current_challenge'] < 5:
        return redirect(url_for('index'))

    if request.method == 'POST':
        comment = request.form.get('comment')
        if comment:
            # Assign the comment to the user
            users[username]['comment'] = comment
            # Mark the challenge as completed and move to the next
            users[username]['current_challenge'] = 5
            # Emit the update via WebSocket (if using Socket.IO)
            socketio.emit('update_leaderboard', {'users': list(users.values())})
            return redirect(url_for('index'))
    return render_template('challenge_five.html')

@app.route('/logout')
def logout():
    """Log out the user"""
    session.clear()
    return redirect(url_for('start'))

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)