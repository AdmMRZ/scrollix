from django.core.management.base import BaseCommand
from manga.services import seed_genres_from_api
class Command(BaseCommand):
    help = 'Fetch all MangaDex tags and populate the Genre table.'
    def handle(self, *args, **options):
        self.stdout.write('Fetching genres from MangaDex API...')
        count = seed_genres_from_api()
        self.stdout.write(self.style.SUCCESS(f'Done — {count} genres seeded.'))
