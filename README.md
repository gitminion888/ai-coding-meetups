# AI Coding Meetups

A simple web application for organizing AI Coding meetups. Users can create meetups, view upcoming events, and RSVP to them.

## Features

- User registration and authentication
- Create and view upcoming meetups
- RSVP functionality (Going/Maybe/Can't Go)
- Clean, responsive UI using Bootstrap 5
- Flash messages for user feedback

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Register for an account using your email and password
2. Login to your account
3. View upcoming meetups on the home page
4. Create new meetups using the "Create Meetup" button
5. RSVP to meetups you're interested in

## Security Note

This is a basic implementation for demonstration purposes. In a production environment, you should:

- Use proper password hashing (e.g., with `werkzeug.security`)
- Configure a proper secret key
- Use HTTPS
- Implement proper input validation and sanitization
- Add rate limiting for forms
- Use a production-grade database (e.g., PostgreSQL)

## Contributing

Feel free to submit issues and enhancement requests! 