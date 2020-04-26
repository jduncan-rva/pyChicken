import os
from signal import pause
from datetime import datetime
from time import sleep
from random import randrange
import configparser
import requests
import yaml
import logging
import threading
import subprocess
import tweepy
from gpiozero import MotionSensor
from picamera import PiCamera

class pyChicken:
  """Python3 application for Raspberry Pis to take advantage of an onboard camera and a PIR motion sensor to automate backyard foul social media
  """

  def __init__(self, options):

    # Grab the config file and read in the options
    logging.basicConfig(filename='pychicken.log',
                      level=logging.INFO,
                      format='%(asctime)s %(name)s %(levelname)s: %(message)s',
                      datefmt='%m-%d %H:%M:%S')
    logging.debug("Processing __init__.py")
    config = configparser.ConfigParser()
    config.read(options.config)

    # Get state of facts engine 
    use_facts = config['facts']['enabled']
    # There's a motion sensor installed and we want to use it via the GPIO pins
    use_motion_sensor = config['motion_sensor']['enabled']
    # We're going to be using a camera attached to our Raspberry Pi Note: this
    # is written for direct-connected cameras, not USB cameras as of right now
    use_camera = config['camera']['enabled']
    # check to see if we're going to be sending tweets
    send_tweets = config['twitter']['enabled']
    # check to see if we're going to be running livestreams
    send_livestream = config['livestream']['enabled']
    
    if use_facts:
      self.facts_url = config['facts']['facts_url']
      self.facts, self.facts_count = self._load_facts_file()
    
    if use_motion_sensor:
      logging.info("Setting motion sensor pin number")
      self.motion_sensor_pin = config['motion_sensor']['gpio_pin']

    if use_camera:
      if config['camera']['text']:
        camera_text = config['camera']['text']
      else:
        camera_text = False
      self._initialize_camera(camera_text=camera_text)

    # If we're going to be sending out tweets we need to set up access through
    # the Twitter API
    if send_tweets:

      self.tweet_interval = config['twitter']['tweet_interval']
      consumer_key = config['twitter']['consumer_key']
      consumer_secret = config['twitter']['consumer_secret']
      access_token = config['twitter']['access_token']
      access_token_secret = config['twitter']['access_token_secret']

      self.twitter = self._create_twitter_api(key=consumer_key,
                     secret=consumer_secret,
                     token=access_token,
                     token_secret=access_token_secret,
                     use_camera=use_camera)

    # We set this to false to start because it's checked by self._image_capture
    # TODO - make this cleaner
    self.running_livestream = False
    self.timestamp = self._set_timestamp()

  def _initialize_camera(self, camera_text):
    """ Gets the camera set up and ready for use"""

    logging.info("Initializing camera")
    self.camera = PiCamera()
    self.camera.resolution = (1024, 768)
    if camera_text:
      self.camera.annotate_text = camera_text
    sleep(2)

  def _create_twitter_api(self, key, secret, token, token_secret, use_camera):
    """sets up and confirms the Twitter API is functional. Returns the twitter API object for use in other functions.
    """

    auth = tweepy.OAuthHandler(key, secret)
    auth.set_access_token(token, token_secret)

    api = tweepy.API(auth,
                    wait_on_rate_limit=True,
                    wait_on_rate_limit_notify=True)

    try:
      api.verify_credentials()
    except Exception as e:
      logging.error("Error verifying Twitter API", exc_info=True)
      raise e
    logging.info("Twitter API connected and verified")

    if use_camera:
      logging.info("Seetting up media information for Twitter")
      self.image_filename = 'tweetpic.jpg'
      self.image_path = '/home/pi'
      self.twitter_image = os.path.join(
                         self.image_path,
                         self.image_filename
      )

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
    
    try:
      logging.info("Capturing image")
      self.camera.capture(self.twitter_image, use_video_port=True)
      
      return True

    except Exception as e:
      logging.error("Unable to capture image.", exc_info=True)
      raise e

  def _send_tweet(self):
    """ Takes a still picture that was just taken and sends out a tweet with the picture and some pre-defined text
    """

    message = self._get_tweet_fact()
    if self._image_capture(): # This returns True if an image is captured
      media_id = list()
      logging.info("sending tweet with image")
      media = self.twitter.media_upload(self.twitter_image)
      logging.info("uploading twitter media: %s", media.media_id_string)
      media_id.append(media.media_id)

      self.twitter.update_status(status=message, media_ids=media_id)

      return update.id

    else:
      logging.info("sending tweet without image")
      update = self.twitter.update_status(status=message)

      return update.id

  def _get_tweet_fact(self):
    """ Grabs a random fact about chickens to attach to a tweet that is being sent out
    """
    fact_number = randrange(self.facts_count)
    fact = self.facts[fact_number]

    fact_type = fact['type']
    fact_content = fact['content']
    fact_author = fact['source']

    if fact_type == "fact":
      message = "Chicken fact %s: %s source: %s" % (fact_number, 
      fact_content,
      fact_author)

    if fact_type == "quote":
      message = "Chicken Quote %s: %s --%s" % (fact_number, 
      fact_content, 
      fact_author)

    return message

  # def _run_livestream(self):
  #   """ Starts a youtube live stream of the chicken yard and sends out a tweet to the youtube live link
  #   """

  #   self.running_livestream = True

  #   # TODO

  #   self.running_livestream = False

  def _load_facts_file(self):
    """ Takes a CSV fie in the format:
    <fact_type>,<fact_content>,<fact_author> and loads it into the database for
    use when sending out tweets.
    """

    logging.info("Loading facts from %s", self.facts_url)
    r = requests.get(self.facts_url, stream=True)
    facts = yaml.load(r.content, Loader=yaml.BaseLoader)

    facts_count = len(facts)
    logging.info("Loaded %s facts", facts_count)

    return facts, facts_count

  def _motion_sensor(self):
    """ Events to trigger when the motion sensor is triggered. things ike social media and livestreams and pics and whatever else you can come up with.
    """

    logging.info("Motion sensor event triggered")
    self._send_tweet()
    
  def _run_motion_sensor(self):
    """The threaded motion sensor object"""

    logging.info("Starting Motion Sensor Thread")
    pir = MotionSensor(self.motion_sensor_pin)
    pir.when_motion = self._motion_sensor

    pause()

  def _run_retrieve_facts(self):
    """The threaded facts retrieval object"""

    logging.info("Starting Facts Thread")
    sleep(3600)
    self.facts, self.facts_count = self._load_facts_file()  

  def run(self):
    """ The primary function. This is called by a script, loads a CSV file full of facts to use as social media content, and begins checking for the motion sensor, start livestreams, etc.
    """

    facts_thread = threading.Thread(name='facts', 
                  target=self._run_retrieve_facts)
    motion_thread = threading.Thread(name='motion_sensor',
                  target=self._run_motion_sensor)

    facts_thread.start()
    motion_thread.start()