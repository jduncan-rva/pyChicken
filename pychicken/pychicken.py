import os
from signal import pause
from datetime import datetime
from time import sleep
from random import randrange
import tweepy
from gpiozero import MotionSensor
from picamera import PiCamera

motion_sensor_pin = 14

class pyChicken:
  """Python3 application for Raspberry Pis to take advantage of an onboard camera and a PIR motion sensor to automate backyard foul social media
  """

  def __init__(self, motion_sensor_pin=motion_sensor_pin):
    self.timestamp = self._set_timestamp()
    self.tweet = True
    self.tweet_interval = (60 * 60) # max 1 tweet per hour
    self.image_filename = 'tweetpic.jpg'
    self.image_path = '/home/pi'
    self.twitter_image = os.path.join(
      self.image_path,
      self.image_filename
    )
    self.running_livestream = False
    self.livestreams = False
    self.motion_sensor_pin = motion_sensor_pin

    self.chicken_facts = list()
    self.chicken_facts_count = len(self.chicken_facts)

  def _set_timestamp(self):
    """ We don't want a chicken walking around all the time to cause a twitter storm. So we'll set a timestamp and use it for comparison so we don't send out too many pictures.
    """
    
    self.timestamp = datetime.now()

    return True
    
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
    if not self.running_livestream: 
      self.camera.start_preview()
      sleep(2)

      self.camera.capture(self.twitter_image)

  def _send_tweet(self, message, attach_pic=True):
    """ Takes a still picture that was just taken and sends out a tweet with the picture and some pre-defined text
    """
    if self.running_livestream:
      message = self.livestream_message
    else:
      message = self._get_tweet_quote()

    pass

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
    <fact_type>,<fact_content>,<fact_author>
    and loads it into the database for use when sending out tweets.
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

  def run(self, options):
    """ The primary function. This is called by a script, loads a CSV file full of facts to use as social media content, and begins checking for the motion sensor, start livestreams, etc.
    """

    camera = PiCamera()
    camera.resolution = (1024, 768)
    print("Initializing Camera")
    sleep(2)

    print("Initializing Motion Sensor")
    pir = MotionSensor(self.motion_sensor_pin)
    pir.when_motion = self._motion_sensor

    pause()