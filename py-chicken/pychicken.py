from gpiozero import MotionSensor
from signal import pause
from datetime import datetime
import tweepy
from picamera import PiCamera
from time import sleep
import os

class PyChicken:
  """Python3 application for Raspberry Pis to take advantage of an onboard camera and a PIR motion sensor to automate backyard foul social media
  """

  def __init__(self):
    self.timestamp = self._set_timestamp()
    self.tweet_interval = (60 * 60) # max 1 tweet per hour
    self.camera = PiCamera()
    self.camera.resolution = (1024, 768)
    self.image_filename = 'tweetpic.jpg'
    self.image_path = '/home/pi'
    self.twitter_image = os.path.join(
      self.image_path,
      self.image_filename
    )

  def _set_timestamp(self):
    """We don't want a chicken walking around all the time to cause a twitter storm. So we'll set a timestamp and use it for comparison so we don't send out too many pictures.
    """
    
    self.timestamp = datetime.now()
    
  def _check_timestamp(self):
    """Check to see if it's OK to send out a tweet or if we should wait. Uses self.timestamp_interval as the minimum wait between events
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
    """capture a still image and save it to a file for uplaoding to a tweet
    """
    
    self.camera.start_preview()
    sleep(2)

    self.camera.capture(self.twitter_image)

    def _send_tweet(self, attach_pic=True, message):
      """takes a still picture that was just taken and sends out a tweet with the picture and some pre-defined text
      """

      pass

    def _get_tweet_quote(self):
      """grabs a random quote about chickens to attach to a tweet that is being sent out
      """

      pass

    def _start_live_stream(self):
      """starts a youtube live stream of the chicken yard and sends out a tweet to the youtube live link
      """

      pass
