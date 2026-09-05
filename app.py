from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import csv, os, hashlib
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'railswap_secret_key_2026'

DATA_DIR    = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
TICKETS_CSV = os.path.join(DATA_DIR, 'tickets.csv')
USERS_CSV   = os.path.join(DATA_DIR, 'users.csv')
TICKET_FIELDS = ['id','train','pname','age','gender','contact','from_station','to_station','date','sold','listed_by']
USER_FIELDS   = ['phone','password']

STATIONS = [
    'Delhi','Mumbai','Chennai','Bangalore','Hyderabad','Kolkata','Vizag','Pune','Ahmedabad',
    'Jaipur','Lucknow','Kanpur','Nagpur','Bhopal','Patna','Guwahati','Chandigarh','Kochi',
    'Coimbatore','Vijayawada','Visakhapatnam','Tirupati','Vizianagaram','Kakinada','Rajahmundry',
    'Nellore','Guntur','Warangal','Secunderabad','Amritsar','Varanasi','Surat','Indore',
    'Ranchi','Bhubaneswar','Thiruvananthapuram','Madurai','Mysore','Dehradun','Jodhpur','Agra'
]

# Demo tickets. 'offset' = days from today. Regenerated daily with fresh dates
# so there are always upcoming "available" tickets to browse, while any
# ticket (demo or real) whose date has passed gets auto-deleted.
SAMPLE_TICKETS = [
    {'train':'Rajdhani Express', 'pname':'Ravi Kumar',   'age':'28','gender':'Male',  'contact':'9876543210','from_station':'Delhi',    'to_station':'Mumbai',   'offset':3},
    {'train':'Shatabdi Express', 'pname':'Priya Sharma', 'age':'35','gender':'Female','contact':'9123456789','from_station':'Chennai',  'to_station':'Bangalore','offset':5},
    {'train':'Duronto Express',  'pname':'Suresh Babu',  'age':'45','gender':'Male',  'contact':'9988776655','from_station':'Hyderabad','to_station':'Delhi',    'offset':7},
    {'train':'Garib Rath',       'pname':'Anita Reddy',  'age':'22','gender':'Female','contact':'8877665544','from_station':'Kolkata',  'to_station':'Chennai',  'offset':9},
    {'train':'Vande Bharat',     'pname':'Kiran Rao',    'age':'30','gender':'Male',  'contact':'7766554433','from_station':'Vizag',    'to_station':'Hyderabad','offset':11},
]

def init_csv():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(TICKETS_CSV):
        with open(TICKETS_CSV, 'w', newline='') as f:
            csv.DictWriter(f, fieldnames=TICKET_FIELDS).writeheader()
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'w', newline='') as f:
            csv.DictWriter(f, fieldnames=USER_FIELDS).writeheader()

def read_csv(path, fields):
    if not os.path.exists(path): return []
    with open(path, 'r', newline='', encoding='utf-8') as f:
        return [dict(r) for r in csv.DictReader(f)]

def write_csv(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)

def hp(p): return hashlib.sha256(p.encode()).hexdigest()

def purge_expired_tickets():
    """Delete tickets whose travel date is before today. Runs on every request."""
    if not os.path.exists(TICKETS_CSV): return
    today = datetime.now().strftime('%Y-%m-%d')
    tickets = read_csv(TICKETS_CSV, TICKET_FIELDS)
    active = [t for t in tickets if t.get('date','') >= today]
    if len(active) != len(tickets):
        write_csv(TICKETS_CSV, TICKET_FIELDS, active)

def ensure_fresh_tickets():
    """Re-add any missing demo tickets with a fresh upcoming date, so the
    'Available Tickets' list always has live tickets to show, day after day."""
    today = datetime.now().date()
    tickets = read_csv(TICKETS_CSV, TICKET_FIELDS)
    existing_ids = {t['id'] for t in tickets}
    changed = False
    for i, tpl in enumerate(SAMPLE_TICKETS, start=1):
        sid = f'sample-{i}'
        if sid not in existing_ids:
            row = {k: v for k, v in tpl.items() if k != 'offset'}
            row.update({'id': sid, 'date': (today + timedelta(days=tpl['offset'])).strftime('%Y-%m-%d'),
                        'sold': 'False', 'listed_by': 'system'})
            tickets.append(row)
            changed = True
    if changed:
        write_csv(TICKETS_CSV, TICKET_FIELDS, tickets)

@app.before_request
def cleanup_before_each_request():
    purge_expired_tickets()
    ensure_fresh_tickets()

@app.route('/')
def index():
    return redirect(url_for('home')) if 'user' in session else render_template('register.html')

@app.route('/login')
def login_page():
    return redirect(url_for('home')) if 'user' in session else render_template('login.html')

@app.route('/home')
def home():
    if 'user' not in session: return redirect(url_for('index'))
    return render_template('home.html', phone=session['user'])

@app.route('/api/register', methods=['POST'])
def api_register():
    d = request.get_json()
    phone, password, confirm = d.get('phone','').strip(), d.get('password',''), d.get('confirm','')
    if not phone or len(phone)!=10 or not phone.isdigit():
        return jsonify({'success':False,'message':'Valid 10-digit phone number enter చేయండి'})
    if len(password)<4:
        return jsonify({'success':False,'message':'Password minimum 4 characters ఉండాలి'})
    if password!=confirm:
        return jsonify({'success':False,'message':'Passwords match కావడం లేదు'})
    users = read_csv(USERS_CSV, USER_FIELDS)
    if any(u['phone']==phone for u in users):
        return jsonify({'success':False,'message':'ఈ phone number already registered ఉంది'})
    users.append({'phone':phone,'password':hp(password)})
    write_csv(USERS_CSV, USER_FIELDS, users)
    session['user'] = phone
    return jsonify({'success':True})

@app.route('/api/login', methods=['POST'])
def api_login():
    d = request.get_json()
    phone, password = d.get('phone','').strip(), d.get('password','')
    if not phone or not password:
        return jsonify({'success':False,'message':'Phone మరియు password enter చేయండి'})
    users = read_csv(USERS_CSV, USER_FIELDS)
    if any(u['phone']==phone and u['password']==hp(password) for u in users):
        session['user'] = phone
        return jsonify({'success':True})
    return jsonify({'success':False,'message':'Invalid phone number లేదా password'})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user', None)
    return jsonify({'success':True})

@app.route('/api/sell', methods=['POST'])
def api_sell():
    if 'user' not in session: return jsonify({'success':False,'message':'Login అవ్వండి'})
    d = request.get_json()
    fields = ['train','pname','age','gender','contact','from_station','to_station','date']
    vals = {k: d.get(k,'').strip() for k in fields}
    if not all(vals.values()): return jsonify({'success':False,'message':'అన్ని fields fill చేయండి'})
    if vals['gender'] not in ('Male','Female','Other'):
        return jsonify({'success':False,'message':'Valid gender select చేయండి'})
    if len(vals['contact'])!=10 or not vals['contact'].isdigit():
        return jsonify({'success':False,'message':'Valid 10-digit contact number enter చేయండి'})
    tickets = read_csv(TICKETS_CSV, TICKET_FIELDS)
    tickets.append({**vals,'id':str(int(datetime.now().timestamp()*1000)),'sold':'False','listed_by':session['user']})
    write_csv(TICKETS_CSV, TICKET_FIELDS, tickets)
    return jsonify({'success':True})

@app.route('/api/search')
def api_search():
    if 'user' not in session: return jsonify({'success':False,'message':'Login అవ్వండి'})
    frm    = request.args.get('from_station','').strip().lower()
    to     = request.args.get('to_station','').strip().lower()
    age    = request.args.get('age','').strip()
    date   = request.args.get('date','').strip()
    gender = request.args.get('gender','').strip().lower()
    if not all([frm,to,age,date]): return jsonify({'success':False,'message':'అన్ని search fields fill చేయండి'})
    try: sage = int(age)
    except: return jsonify({'success':False,'message':'Valid age enter చేయండి'})
    tickets = read_csv(TICKETS_CSV, TICKET_FIELDS)
    results = [t for t in tickets if
        frm in t['from_station'].lower() and
        to  in t['to_station'].lower() and
        t['date']==date and
        (not gender or gender=='any' or t.get('gender','').lower()==gender) and
        abs(int(t['age'])-sage)<=10]
    return jsonify({'success':True,'results':results,'count':len(results)})

@app.route('/api/stations')
def api_stations():
    tickets = read_csv(TICKETS_CSV, TICKET_FIELDS)
    used = {t['from_station'] for t in tickets} | {t['to_station'] for t in tickets}
    all_stations = sorted(set(STATIONS) | used)
    return jsonify({'success':True,'stations':all_stations})

@app.route('/api/stats')
def api_stats():
    tickets = read_csv(TICKETS_CSV, TICKET_FIELDS)
    routes = len(set(f"{t['from_station']}-{t['to_station']}" for t in tickets))
    return jsonify({'total':len(tickets),'available':sum(1 for t in tickets if t['sold']=='False'),'routes':routes})

@app.route('/api/all-tickets')
def api_all_tickets():
    if 'user' not in session: return jsonify({'success':False,'message':'Login అవ్వండి'})
    tickets = read_csv(TICKETS_CSV, TICKET_FIELDS)
    return jsonify({'success':True,'tickets':tickets,'count':len(tickets)})

@app.route('/api/available-tickets')
def api_available_tickets():
    if 'user' not in session: return jsonify({'success':False,'message':'Login అవ్వండి'})
    tickets = read_csv(TICKETS_CSV, TICKET_FIELDS)
    available = [t for t in tickets if t['sold']=='False']
    return jsonify({'success':True,'tickets':available,'count':len(available)})

if __name__ == '__main__':
    init_csv()
    app.run(debug=True, port=5000)
