import os
import io
import shutil
from signal import pause
from datetime import datetime
from time import sleep, time
from random import randrange
from http import server
import socketserver
import configparser
import requests
import yaml
import logging
import threading
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

    if send_livestream:
      self.running_livestream = False
      self.livestream_duration = config['livestream']['duration']
      self.http_port = config['livestream']['http_port']
      self.ws_port = config['livestream']['ws_port']
      self.page = """\
        < html >
        <head >
        <title > picamera MJPEG streaming demo < /title >
        </head >
        <body >
        <h1 > PiCamera MJPEG Streaming Demo < /h1 >
        <img src = "stream.mjpg" width = "640" height = "480" / >
        </body >
        </html >
        """

    if use_facts:
      self.facts_url = config['facts']['facts_url']
      self.facts, self.facts_count = self._load_facts_file()

    if use_motion_sensor:
      logging.info("Setting motion sensor pin number")
      self.motion_sensor_pin = config['motion_sensor']['gpio_pin']

    if use_camera:
      if config['camera']['text']:
        self.camera_text = config['camera']['text']
        self.vflip = config['camera']['vflip']
        self.hflip = config['camera']['hflip']
        self.width = config['camera']['width']
        self.height = config['camera']['height']
        self.framerate = config['camera']['framerate']
      else:
        self.camera_text = False

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

    self.timestamp = self._set_timestamp()

  def _initialize_camera(self):
    """ Gets the camera set up and ready for use"""

    try:
      logging.info("Initializing camera")
      self.camera = PiCamera()
      self.camera.resolution = (self.width, self.height)
      self.camera.framerate = self.framerate
      if self.camera_text:
        self.camera.annotate_text = self.camera_text
        sleep(2)

      return True

    except Exception as e:
      logging.error("Unable to initalize camera", exc_info=True)
      raise e

  def _close_camera(self):
    """ Cleanly closes down the camera interface. Apparently there are memory leaks and we can't leave it open forever"""

    try:
      logging.info("Closing camera interface")
      self.camera.close()

    except Exception as e:
      logging.error("Unable to close camera", exc_info=True)
      raise e

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

    if (secs_since_tweet > self.tweet_interval):
      self.timestamp = self._set_timestamp()
      return True

    else:
      return False

  def _image_capture(self):
    """ Captures a still image and save it to a file for uplaoding to a tweet
    """

    try:
      self._initialize_camera()
      logging.info("Capturing image")
      self.camera.capture(self.twitter_image, use_video_port=True)
      self._close_camera()
      return True

    except Exception as e:
      logging.error("Unable to capture image.", exc_info=True)
      raise e

  def _send_tweet(self):
    """ Takes a still picture that was just taken and sends out a tweet with the picture and some pre-defined text
    """

    try:
      # A live stream is running
      if self.running_livestream:
        message = "Hey! We're running a livestream right now! Come check us out at foo"

        update = self.twitter.update_status(status=message)

      else:
        message = self._get_tweet_fact()

      if self._image_capture():  # This returns True if an image is captured
        media_id = list()
        logging.info("sending tweet with image")
        media = self.twitter.media_upload(self.twitter_image)
        logging.debug("uploading twitter media: %s",
            media.media_id_string)
        media_id.append(media.media_id)

        update = self.twitter.update_status(
        status=message, media_ids=media_id)

      else:
        logging.info("sending tweet without image")
        update = self.twitter.update_status(status=message)

      logging.info("Updated Twitter status: %s", update.id)
      return update.id

    except Exception as e:
      logging.error("Unable to send Twitter update", exc_info=True)
      raise e

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
    while True:
      sleep(3600)
      self.facts, self.facts_count = self._load_facts_file()

  def _run_livestream(self):
    """ The thread function to run the livestream"""

    self.running_livestream = True
    global output 
    output = StreamingOutput()
    self._initialize_camera()
    logging.info("starting livestream")
    self.camera.start_recording(output, format='mjpeg')
    try:
      address = ('', 8000)
      server = StreamingServer(address, StreamingHandler)
      server.serve_forever()
      sleep(100)
      logging.info("Closing livestream")
      self._close_camera()
      self.running_livestream = False

    except Exception as e:
      logging.error("Unable to begin livestream", exc_info=True)
      raise e

  def run(self):
    """ The primary function. This is called by a script, loads a CSV file full of facts to use as social media content, and begins checking for the motion sensor, start livestreams, etc.
    """

    facts_thread = threading.Thread(name='facts',
            target=self._run_retrieve_facts)
    motion_thread = threading.Thread(name='motion_sensor',
            target=self._run_motion_sensor)
    livestream_thread = threading.Thread(name='livestream',
              target=self._run_livestream)

    facts_thread.start()
    motion_thread.start()
    livestream_thread.start()


class StreamingOutput(object):
  def __init__(self):
    self.frame = None
    self.buffer = io.BytesIO()
    self.condition = threading.Condition()

  def write(self, buf):
    if buf.startswith(b'\xff\xd8'):
      # New frame, copy the existing buffer's content and notify all
      # clients it's available
      self.buffer.truncate()
      with self.condition:
        self.frame = self.buffer.getvalue()
        self.condition.notify_all()
      self.buffer.seek(0)
    return self.buffer.write(buf)

class StreamingHandler(server.BaseHTTPRequestHandler):
  def __init__(self):
    self.page = """\
    < html >
    <head >
    <title > picamera MJPEG streaming demo < /title >
    </head >
    <body >
    <h1 > PiCamera MJPEG Streaming Demo < /h1 >
    <img src = "stream.mjpg" width = "640" height = "480" / >
    </body >
    </html >
    """

  def do_GET(self):
    if self.path == '/':
      self.send_response(301)
      self.send_header('Location', '/index.html')
      self.end_headers()
    elif self.path == '/index.html':
      content = self.page.encode('utf-8')
      self.send_response(200)
      self.send_header('Content-Type', 'text/html')
      self.send_header('Content-Length', len(content))
      self.end_headers()
      self.wfile.write(content)
    elif self.path == '/stream.mjpg':
      self.send_response(200)
      self.send_header('Age', 0)
      self.send_header('Cache-Control', 'no-cache, private')
      self.send_header('Pragma', 'no-cache')
      self.send_header(
      'Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
      self.end_headers()
      try:
        while True:
          with output.condition:
            output.condition.wait()
            frame = output.frame
          self.wfile.write(b'--FRAME\r\n')
          self.send_header('Content-Type', 'image/jpeg')
          self.send_header('Content-Length', len(frame))
          self.end_headers()
          self.wfile.write(frame)
          self.wfile.write(b'\r\n')

      except Exception as e:
        logging.warning('Removed streaming client %s: %s', self.client_address, str(e))
    else:
      self.send_error(404)
      self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
  allow_reuse_address = True
  daemon_threads = True
