web: python manage.py collectstatic --noinput && python manage.py createcachetable && gunicorn scrollix.wsgi --bind 0.0.0.0:$PORT --timeout 120

