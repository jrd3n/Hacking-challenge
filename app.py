# Websockets for scoreboard removed
# - [x] score doesnt record previous challenges
# - [x] the start doesnt direct the user straing to challenge 1.

# Issues

# - [x] if the usernamme cookie is not in the user list it tries to run anyway
# - [ ] 
 

from flask import Flask, render_template, request, redirect, url_for, make_response, flash
from datetime import datetime
import csv




app = Flask(__name__)
app.secret_key = 'your_unique_secret_key'


# Store user data
users = {}
CSV_FILE = 'high_scores.csv'

def save_users_to_csv():
    """Save user data to a CSV file."""
    with open(CSV_FILE, 'w', newline='') as csvfile:
        fieldnames = ['User', 'Total Time (s)', 'Challenge 1 Time (s)', 'Challenge 2 Time (s)', 
                      'Challenge 3 Time (s)', 'Challenge 4 Time (s)', 'Comment', 'Current Challenge', 'Start Time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for user in users.values():
            def format_time(value):
                return '%.1f' % value if isinstance(value, (int, float)) else 'N/A'

            writer.writerow({
                'User': user['username'],
                'Total Time (s)': format_time(user['total_time']),
                'Challenge 1 Time (s)': format_time(user['challenge_1_time']),
                'Challenge 2 Time (s)': format_time(user['challenge_2_time']),
                'Challenge 3 Time (s)': format_time(user['challenge_3_time']),
                'Challenge 4 Time (s)': format_time(user['challenge_4_time']),
                'Comment': user['comment'],
                'Current Challenge': user['current_challenge'],
                'Start Time': user['start_time'].isoformat() if user['start_time'] else 'N/A'
            })

def load_users_from_csv():
    """Load user data from a CSV file."""
    try:
        with open(CSV_FILE, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                current_challenge = int(row['Current Challenge']) if row['Current Challenge'] and row['Current Challenge'] != 'N/A' else 1
                
                # Parse start_time if available and not 'N/A'
                start_time = datetime.fromisoformat(row['Start Time']) if row['Start Time'] != 'N/A' else None
                
                users[row['User']] = {
                    'username': row['User'],
                    'total_time': float(row['Total Time (s)']) if row['Total Time (s)'] != 'N/A' else None,
                    'challenge_1_time': float(row['Challenge 1 Time (s)']) if row['Challenge 1 Time (s)'] != 'N/A' else None,
                    'challenge_2_time': float(row['Challenge 2 Time (s)']) if row['Challenge 2 Time (s)'] != 'N/A' else None,
                    'challenge_3_time': float(row['Challenge 3 Time (s)']) if row['Challenge 3 Time (s)'] != 'N/A' else None,
                    'challenge_4_time': float(row['Challenge 4 Time (s)']) if row['Challenge 4 Time (s)'] != 'N/A' else None,
                    'comment': row['Comment'],
                    'current_challenge': current_challenge,
                    'start_time': start_time  # Store start_time directly
                }
    except FileNotFoundError:
        print("CSV file not found. Starting with an empty user list.")
    except KeyError as e:
        print(f"KeyError: {e}. Check if the column name in the CSV matches exactly.")
    except ValueError as e:
        print(f"ValueError: {e}. Check the data types in the CSV.")

@app.route('/')
def index():
    """Home page with leaderboard."""
    load_users_from_csv()  # Load user data from CSV on server start
    username = request.cookies.get('username')


    if username and username not in users:
        # If the username from the cookie is not in the user list, redirect to start with an error
        return render_template('index.html', users=users, username=None, error="Unrecognized user. Please log out and start again.")

     # Sort users by total_time, only if all challenges are completed. Otherwise, use float('inf')
    sorted_users = sorted(users.values(), key=lambda u: u['total_time'] if all([
        u.get('challenge_1_time'),
        u.get('challenge_2_time'),
        u.get('challenge_3_time'),
        u.get('challenge_4_time')
    ]) else float('inf'))

    return render_template('index.html', users=users, username=username, sorted_users=sorted_users)





@app.route('/start', methods=['GET', 'POST'])
def start():
    """Handle the start modal logic."""
    if request.method == 'POST':
        username = request.form.get('name')

        # Check if the username already exists in the users dictionary
        if username in users:
            flash(f"The username '{username}' has already been used. Please choose a different username.", 'danger')
            return redirect(url_for('index'))

        # Initialize user data if not exists
        users[username] = {
            'username': username,
            'challenge_1_time': None,
            'challenge_2_time': None,
            'challenge_3_time': None,
            'challenge_4_time': None,
            'total_time': None,
            'comment': '',
            'current_challenge': 1,
            'start_time': None  # Initialize start_time
        }

        response = make_response(redirect(url_for('challenge_one')))
        response.set_cookie('username', username)
        return response
    else:
        return render_template('start.html', username=request.cookies.get('username'))

def record_start_time(username, challenge):
    """Record the start time for a challenge if not already started."""
    user = users[username]

    # Only set start_time if it's not already set
    if not user['start_time']:
        user['start_time'] = datetime.now()

def record_completion_time(username, challenge):
    """Record the completion time for a challenge."""
    user = users[username]

    if 'start_time' in user and user['start_time']:
        start_time = user['start_time']
        completion_time = (datetime.now() - start_time).total_seconds()
        
        # Record the completion time for the current challenge
        user[f'{challenge}_time'] = completion_time

        # Clear the start time for the next challenge
        user['start_time'] = None

        # Check if all challenge times are completed before calculating total time
        if all([
            user.get('challenge_1_time') is not None,
            user.get('challenge_2_time') is not None,
            user.get('challenge_3_time') is not None,
            user.get('challenge_4_time') is not None
        ]):
            # Recalculate total time only if all challenges are completed
            user['total_time'] = sum(
                time for time in [
                    user.get('challenge_1_time'),
                    user.get('challenge_2_time'),
                    user.get('challenge_3_time'),
                    user.get('challenge_4_time')
                ]
            )
        else:
            # Set total time to None if not all challenges are completed
            user['total_time'] = None

        # Save the updated user data to the CSV
        save_users_to_csv()


@app.route('/challenge_one', methods=['GET', 'POST'])
def challenge_one():
    """Challenge One"""

    username = request.cookies.get('username')

    if not username:

        return redirect(url_for('start'))

    record_start_time(username, 'challenge_one')

    if request.method == 'POST':

        input_username = request.form.get('username')
        password = request.form.get('password')

        if input_username.lower() == 'admin' and password.lower() == 'admin':
            record_completion_time(username, 'challenge_one')
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
            save_users_to_csv()  # Save to CSV whenever a comment is added
            return redirect(url_for('index'))
    return render_template('challenge_five.html')

@app.route('/logout')
def logout():
    """Log out the user."""
    response = make_response(redirect(url_for('index')))
    response.set_cookie('username', '', expires=0)  # Clear the username cookie
    return response

if __name__ == "__main__":
    load_users_from_csv()  # Load user data from CSV on server start
    app.run(host='0.0.0.0', port=8000, debug=True)
