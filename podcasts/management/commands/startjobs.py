# Standard Library
import logging

# Django
from django.conf import settings
from django.core.management.base import BaseCommand

# Third Party
import feedparser
from dateutil import parser
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

import requests
import re
import time

# Models
from podcasts.models import Episode


logger = logging.getLogger(__name__)


def save_new_episodes(feed):
    """Saves new episodes to the database.

    Checks the episode GUID agaist the episodes currently stored in the
    database. If not found, then a new `Episode` is added to the database.

    Args:
        feed: requires a feedparser object   
    """
    article_image =''
    media_url = ''
    enclosure_href = ''
    parser_ = ''
    raw = ''
    try:
        response = requests.get(feed)

        if response and response.status_code == 200:
            raw = response.text

        else:
            pass

    except (requests.exceptions.ConnectionError, requests.exceptions.MissingSchema):
        pass

    # if raw <item>'s have a '<image> ... </image>' pattern extract the image url and
    # put this image url in an <enclosure /> tag which can be handled by feedparser
    raw = re.sub(r'(<item>.*?)<image>.*?(http.*?jpg|png|gif).*?</image>(.*?</item>)',
                r'\1<enclosure url="\2" />\3', raw)

    # some url give an empty raw string, in that case parse with the url instead of 
    # the raw string
    if raw:
        parser_ = feedparser.parse(raw)

    else:
        parser_ = feedparser.parse(feed)


    for entry in parser_.entries:
        if entry.enclosures:
            enclosure_href = entry.enclosures[0]['href']
    
        else:
            enclosure_href = ''

    # check if there is media_content
        try:
            media_url = entry.media_content[0]['url']
    
        except AttributeError:
            media_url = ''

    #use the enclosure_href for the image if it exists, else use the media_url
        if enclosure_href:
            article_image = enclosure_href
        else:
            article_image = media_url

        # some entry have no attribute published, in that case check for attribute
        # updated, if that does not exist give default date of 1970-1-1
        try: 
            published = entry.published
            published_parsed = entry.updated_parsed
    
        except AttributeError:
            published = entry.get('updated', '1970-01-01')
            published_parsed = entry.get('updated_parsed', 
                time.struct_time((1970, 1, 1, 0, 0, 0, 0, 0, 0)))

        

        podcast_title = parser_.channel.title  
        if not Episode.objects.filter(guid=entry.guid).exists():
            episode = Episode(
                title=entry.title,
                description=entry.description,
                pub_date=parser.parse(published),
                link=entry.link,
                image=article_image,
                podcast_name=podcast_title,
                guid=entry.guid,
            )
            episode.save()


def fetch_entrepreneur_episodes():
    """Fetches new episodes from RSS for the Entrepreneur Python Podcast."""
    _feed = "https://www.entrepreneur.com/latest.rss"
    save_new_episodes(_feed)


def fetch_punch_technology_episodes():
    """Fetches new episodes from RSS for punch  Podcast."""
    _feed = "https://rss.punchng.com/v1/category/technology"
    save_new_episodes(_feed)


def fetch_tech_point_africa_episodes():
    """Fetches new episodes from RSS for punch  Podcast."""
    _feed = "https://techpoint.africa/feed/"
    save_new_episodes(_feed)


def delete_old_job_executions(max_age=604_800):
    """Deletes all apscheduler job execution logs older than `max_age`."""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs apscheduler."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            fetch_entrepreneur_episodes,
            trigger="interval",
            minutes=5,
            id="The Entrepreneur Podcast",  # Each job MUST have a unique ID
            max_instances=1,
            # Replaces existing and stops duplicates on restart of the app.
            replace_existing=True,
        )
        logger.info("Added job: The Entrepreneur Podcast.")

        scheduler.add_job(
            fetch_punch_technology_episodes,
            trigger="interval",
            minutes=5,
            id="punch technology Feed",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job: punch technology Feed.")

        scheduler.add_job(
            fetch_tech_point_africa_episodes,
            trigger="interval",
            minutes=5,
            id="tech point africa Feed",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added job: tech point africa Feed.")

        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(
                day_of_week="mon", hour="00", minute="00"
            ),  # Midnight on Monday, before start of the next work week.
            id="Delete Old Job Executions",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Added weekly job: Delete Old Job Executions.")

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")