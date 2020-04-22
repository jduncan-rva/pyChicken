import os
from signal import pause
from datetime import datetime
from time import sleep
from random import randrange
import configparser
import csv
import requests
import logging
import tweepy
from gpiozero import MotionSensor
from picamera import PiCamera

class pyChicken:
  """Python3 application for Raspberry Pis to take advantage of an onboard camera and a PIR motion sensor to automate backyard foul social media
  """

  def __init__(self, options):

    self.logger = logging.getLogger()
    
    # grab the config file and read in the options
    self.logger.debug("Processing __init__.py")
    self.config = configparser.ConfigParser()
    self.config.read(options.config)

    # There's a motion sensor installed and we want to use it via the GPIO pins
    self.use_motion_sensor = self.config['motion_sensor']['enabled']
    if self.use_motion_sensor:
      self.logger.debug("Setting motion sensor pin number")
      self.motion_sensor_pin = self.config['motion_sensor']['gpio_pin']

    # We're going to be using a camera attached to our Raspberry Pi Note: this
    # is written for direct-connected cameras, not USB cameras as of right now
    self.use_camera = self.config['camera']['enabled']
    if self.use_camera:
      self.logger.info("Initializing camera")
      self.camera = PiCamera()
      self.camera.resolution = (1024, 768)
      sleep(2)

    # check to see if we're going to be sending tweets
    self.send_tweets = self.config['twitter']['enabled']

    # If we're going to be sending out tweets we need to set up access through
    # the Twitter API
    if self.send_tweets:
      self.twitter = self._create_twitter_api()
      self._setup_twitter_params() 

    self.send_livestream = self.config['livestream']['send_livestream']
  
    self.chicken_facts = list()
    self.chicken_facts_count = len(self.chicken_facts)
    self.timestamp = self._set_timestamp()

  def _setup_twitter_params(self):
    """ Sets up some needed parameterss to properly process information and send it to Twitter.
    """
    
    self.tweet_interval = self.config['twitter']['tweet_interval']
    if self.use_camera:
      self.logger.info("Seetting up media information for Twitter")
      self.image_filename = 'tweetpic.jpg'
      self.image_path = '/home/pi'
      self.twitter_image = os.path.join(
                         self.image_path,
                         self.image_filename
      )

  def _create_twitter_api(self):
    """sets up and confirms the Twitter API is functional. Returns the twitter API object for use in other functions.
    """

    consumer_key = self.config['twitter']['consumer_key']
    consumer_secret = self.config['twitter']['consumer_secret']
    access_token = self.config['twitter']['access_token']
    access_token_secret = self.config['twitter']['access_token_secret']

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)

    api = tweepy.API(auth,
                    wait_on_rate_limit=True,
                    wait_on_rate_limit_notify=True)

    try:
      api.verify_credentials()
    except Exception as e:
      self.logger.error("Error verifying Twitter API", exc_info=True)
      raise e
    self.logger.info("Twitter API connected and verified")

    return api

  def _set_timestamp(self):
    """ We don't want a chicken walking around all the time to cause a twitter storm. So we'll set a timestamp and use it for comparison so we don't send out too many pictures.
    """
    
    timestamp = datetime.now()

    return timestamp
    
  def _check_timestamp(self):
    """ Checks to see if it's OK to send out a tweet or if we should wait. Uses self.timestamp_interval as the minimum wait between events
    """

    curr_time = datetime.now()
    time_since_tweet = curr_time - self.timestamp
    secs_since_tweet = time_since_tweet.total_seconds()

    if ( secs_since_tweet > self.tweet_interval ):
      self.timestamp = self._set_timestamp()
      return True

    else:
      return False

  def _image_capture(self):
    """ Captures a still image and save it to a file for uplaoding to a tweet
    """
    
    # we don't want to try to capture a pic if we're running a livestream
    if self.running_livestream:
      self.logger.info("Livestream running. Not going to capture image")
      return False
    else:
      try:
        self.logger.info("Preparing to capture image")
        self.camera.start_preview()
        sleep(2)

        self.camera.capture(self.twitter_image)
        return False

      except Exception as e:
        self.logger.error("Unable to capture image.", exc_info=True)
        raise e

  def _send_tweet(self, message, attach_pic=True):
    """ Takes a still picture that was just taken and sends out a tweet with the picture and some pre-defined text
    """
    if self.running_livestream:
      self.twitter_api.update_status(self.livestream_message)
    else:
      message = self._get_tweet_quote()
      status = self.twitter_api.update_with_media(self.twitter_image, message)

      self.twitter_api.update_status(status = message)

  def _get_tweet_fact(self):
    """ Grabs a random fact about chickens to attach to a tweet that is being sent out
    """
    fact_number = randrange(self.chicken_facts_count)
    fact = self.chicken_facts(fact_number)

    fact_type = fact[0]
    fact_content = fact[1]
    fact_author = fact[2]

    if fact_type == "fact":
      message = "Chicken fact %s: %s source: %s" % (fact_number, 
      fact_content,
      fact_author)

    if fact_type == "quote":
      message = "Chicken Quote %s: %s --%s" % (fact_number, 
      fact_content, 
      fact_author)

  def _run_livestream(self):
    """ Starts a youtube live stream of the chicken yard and sends out a tweet to the youtube live link
    """

    self.running_livestream = True

    # TODO

    self.running_livestream = False

    pass

  def _load_facts_file(self, facts_file):
    """ Takes a CSV fie in the format:
    <fact_type>,<fact_content>,<fact_author> and loads it into the database for
    use when sending out tweets.
    """

  def _add_tweet_quote(self, quote, fact_type='fact', author=None):
    """ Used to add a quote to the running instance of py-chicken, and update the counter for the number of facts
    """

    self.chicken_facts.append((fact_type, quote, author))
    self.chicken_facts_count = len(self.chicken_facts)

    return True

  def _motion_sensor(self):
    """ Events to trigger when the motion sensor is triggered. things ike social media and livestreams and pics and whatever else you can come up with.
    """

    print("motion detected at {t}!".format(t=datetime.now()))
    print("capturing image at {p}".format(p=self.twitter_image))
    self._image_capture()

  def run(self):
    """ The primary function. This is called by a script, loads a CSV file full of facts to use as social media content, and begins checking for the motion sensor, start livestreams, etc.
    """

    print("Initializing Motion Sensor")
    pir = MotionSensor(self.motion_sensor_pin)
    pir.when_motion = self._motion_sensor

    pause()