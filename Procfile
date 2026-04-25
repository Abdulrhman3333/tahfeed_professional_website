web: gunicorn myproject.wsgi:application --log-file - --bind 0.0.0.0:$PORT
release: python manage.py migrate
