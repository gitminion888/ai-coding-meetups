from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))

# Get the database URL and fix postgres:// if needed
database_url = os.getenv('DATABASE_URL', 'sqlite:///meetups.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize database tables
def init_db():
    try:
        with app.app_context():
            db.create_all()
            print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        raise

# Initialize database tables on startup
init_db()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    proposals = db.relationship('MeetupProposal', backref='creator', lazy=True)

    def get_proposal_count(self):
        return MeetupProposal.query.filter_by(created_by=self.id).count()

class MeetupProposal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='voting')  # voting, finalized
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def title(self):
        user = User.query.get(self.created_by)
        proposal_number = MeetupProposal.query.filter_by(created_by=self.created_by).filter(MeetupProposal.id <= self.id).count()
        return f"{user.name}'s Proposal #{proposal_number}"

class TimeLocationSuggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('meetup_proposal.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    suggested_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SuggestionVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey('time_location_suggestion.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('suggestion_id', 'user_id', name='unique_vote'),)

class Meetup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proposal_id = db.Column(db.Integer, db.ForeignKey('meetup_proposal.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class RSVP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meetup_id = db.Column(db.Integer, db.ForeignKey('meetup.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'yes', 'no', 'maybe'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    proposals = MeetupProposal.query.filter_by(status='voting').order_by(MeetupProposal.created_at.desc()).all()
    upcoming_meetups = Meetup.query.filter(Meetup.date >= datetime.now()).order_by(Meetup.date).all()
    return render_template('index.html', proposals=proposals, meetups=upcoming_meetups)

@app.route('/proposal/new', methods=['GET', 'POST'])
@login_required
def new_proposal():
    if request.method == 'POST':
        proposal = MeetupProposal(
            created_by=current_user.id
        )
        db.session.add(proposal)
        db.session.commit()
        
        # Add initial time/location suggestion if provided
        date = request.form.get('date')
        location = request.form.get('location')
        if date and location:
            date = datetime.strptime(date, '%Y-%m-%dT%H:%M')
            suggestion = TimeLocationSuggestion(
                proposal_id=proposal.id,
                date=date,
                location=location,
                suggested_by=current_user.id
            )
            db.session.add(suggestion)
            db.session.commit()
        
        flash('Meetup proposal created! Others can now suggest times/locations and vote.', 'success')
        return redirect(url_for('view_proposal', proposal_id=proposal.id))
    
    return render_template('new_proposal.html')

@app.route('/proposal/<int:proposal_id>')
def view_proposal(proposal_id):
    proposal = MeetupProposal.query.get_or_404(proposal_id)
    suggestions = TimeLocationSuggestion.query.filter_by(proposal_id=proposal_id).all()
    
    # Get vote counts for each suggestion
    suggestion_votes = {}
    for suggestion in suggestions:
        votes = SuggestionVote.query.filter_by(suggestion_id=suggestion.id).count()
        suggestion_votes[suggestion.id] = votes
        
    return render_template('view_proposal.html', 
                         proposal=proposal, 
                         suggestions=suggestions,
                         suggestion_votes=suggestion_votes)

@app.route('/proposal/<int:proposal_id>/suggest', methods=['POST'])
@login_required
def add_suggestion(proposal_id):
    proposal = MeetupProposal.query.get_or_404(proposal_id)
    if proposal.status != 'voting':
        flash('This proposal is no longer accepting suggestions.', 'error')
        return redirect(url_for('view_proposal', proposal_id=proposal_id))
    
    date = datetime.strptime(request.form.get('date'), '%Y-%m-%dT%H:%M')
    location = request.form.get('location')
    
    suggestion = TimeLocationSuggestion(
        proposal_id=proposal_id,
        date=date,
        location=location,
        suggested_by=current_user.id
    )
    db.session.add(suggestion)
    db.session.commit()
    
    flash('Your suggestion has been added!', 'success')
    return redirect(url_for('view_proposal', proposal_id=proposal_id))

@app.route('/suggestion/<int:suggestion_id>/vote', methods=['POST'])
@login_required
def vote_suggestion(suggestion_id):
    suggestion = TimeLocationSuggestion.query.get_or_404(suggestion_id)
    proposal = MeetupProposal.query.get(suggestion.proposal_id)
    
    if proposal.status != 'voting':
        flash('Voting is closed for this proposal.', 'error')
        return redirect(url_for('view_proposal', proposal_id=proposal.id))
    
    existing_vote = SuggestionVote.query.filter_by(
        suggestion_id=suggestion_id,
        user_id=current_user.id
    ).first()
    
    if existing_vote:
        db.session.delete(existing_vote)
        flash('Your vote has been removed.', 'success')
    else:
        vote = SuggestionVote(
            suggestion_id=suggestion_id,
            user_id=current_user.id
        )
        db.session.add(vote)
        flash('Your vote has been recorded!', 'success')
    
    db.session.commit()
    return redirect(url_for('view_proposal', proposal_id=proposal.id))

@app.route('/proposal/<int:proposal_id>/finalize', methods=['POST'])
@login_required
def finalize_proposal(proposal_id):
    proposal = MeetupProposal.query.get_or_404(proposal_id)
    
    if proposal.created_by != current_user.id:
        flash('Only the proposal creator can finalize the meetup.', 'error')
        return redirect(url_for('view_proposal', proposal_id=proposal_id))
    
    suggestion_id = request.form.get('suggestion_id')
    suggestion = TimeLocationSuggestion.query.get_or_404(suggestion_id)
    
    meetup = Meetup(
        proposal_id=proposal.id,
        title=proposal.title,
        date=suggestion.date,
        location=suggestion.location,
        description=proposal.description,
        created_by=current_user.id
    )
    
    proposal.status = 'finalized'
    db.session.add(meetup)
    db.session.commit()
    
    flash('Meetup has been finalized!', 'success')
    return redirect(url_for('index'))

@app.route('/meetup/<int:meetup_id>/rsvp', methods=['POST'])
@login_required
def rsvp(meetup_id):
    status = request.form.get('status')
    if status not in ['yes', 'no', 'maybe']:
        flash('Invalid RSVP status', 'error')
        return redirect(url_for('index'))
    
    rsvp = RSVP.query.filter_by(user_id=current_user.id, meetup_id=meetup_id).first()
    if rsvp:
        rsvp.status = status
    else:
        rsvp = RSVP(user_id=current_user.id, meetup_id=meetup_id, status=status)
        db.session.add(rsvp)
    
    db.session.commit()
    flash('RSVP updated successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.password == password:  # In production, use proper password hashing
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        user = User(email=email, password=password, name=name)  # In production, hash the password
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=8083) 