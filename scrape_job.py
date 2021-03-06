import requests
import socks
import bs4
import hashlib
import re
import json
import datetime
import random
import os
from PIL import Image
import io
import psycopg2
import subprocess
import boto3 
import datetime 
import sys
from retrieve_posts import retrieve_posts_csv

# Constants
CRAIGSLIST_URLS = [
"https://newyork.craigslist.org",
"https://raleigh.craigslist.org",
"https://pittsburgh.craigslist.org"
]

NUMBER_OF_POSTS = int(sys.argv[1])
DATABASE_URL =  os.environ.get('DATABASE_URL')
ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY_ID')
SECRET_KEY = os.environ.get('AWS_SECRET_KEY')


def upload_to_aws(local_file, bucket, s3_file):
    s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
                      aws_secret_access_key=SECRET_KEY)
    s3.upload_file(local_file, bucket, s3_file)
    print("Upload Successful")
    
def CollectMissedConnectionsLink(location):
    '''Returns a list of recent posts urls from the location specific missed
    connection url passed'''
    craigslistMissedConnectionsUrls = []
    randomCraigslistUrl = CRAIGSLIST_URLS[location] + "/search/mis"
    response = requests.get(randomCraigslistUrl).text
    soup = bs4.BeautifulSoup(response, "html.parser")
    for link in soup.findAll('a', href=True, text=''):
        if ('html' in link['href']):
            craigslistMissedConnectionsUrls.append( link['href'] )
    return craigslistMissedConnectionsUrls

def GetTitle(pageContent):
    '''Returns the title of the passed page content'''
    title = pageContent.select('title')[0].get_text()
    title = Clean(title)
    return title

def GetLocation(randomLocationUrl):
    '''Scrape a readable location from the location specific missed connections
    url so that it can be displayed in the header'''
    location = CRAIGSLIST_URLS[randomLocationUrl]
    if ".org" in location:
        location = CRAIGSLIST_URLS[randomLocationUrl][8:-15]
    else:
        location = CRAIGSLIST_URLS[randomLocationUrl][8:-14]
    return location

def GetHash(postBody):
    '''Returns a hash of the post body passed to it'''
    hashObject = hashlib.md5(postBody)
    hashedPostBody = hashObject.hexdigest()
    return hashedPostBody;

def GetPageContent(linkToVisit):
    '''Returns the page content of the link passed to it'''
    response = requests.get(linkToVisit)
    pageContent = bs4.BeautifulSoup(response.text, "html.parser")
    return pageContent;

def GetBody(finalUrl):
    '''Returns the body of the post from the url passed to it. Dependent
    upon the structure of the craiglist page'''
    pageContent = GetPageContent(finalUrl)
    body = pageContent.select('section#postingbody')[0].get_text()
    body = body.split("QR Code Link to This Post")[1]
    body = Clean(body)
    return body

def Clean(content):
    ''''Returns a slightly styled version of the content passed to it'''
    content = re.sub('\n', '', content)
    content = (content).replace('"', "'")
    content = content.rstrip()
    content = content.encode('utf-8')
    return content

def GetQueryData(pageContent, finalUrl, randomLocationUrl):
    '''Returns a json compliant post'''
    title = GetTitle(pageContent)
    today = datetime.date.today()
    location = GetLocation(randomLocationUrl)
    body = GetBody(finalUrl)
    hashedPost = GetHash(body)
    # For debugging purposes

    print("Post from %s fetched" % location)
    print(body)
    return (title.decode('utf-8'), body.decode('utf-8'), str(location), str(today), str(hashedPost))

def ScrapeImages(finalUrl):
    '''Scrapes and shuffles all the images found in a post from the url passed'''
    images = []
    IMAGE_HASHES =  []
    response = requests.get(finalUrl).text
    soup = bs4.BeautifulSoup(response, "html.parser")
    # commented out 2020-11-25 because occasionally its failing and I'm not using it anyway
'''
    for link in soup.findAll('a', href=True, text=''):
            if ('images' in link['href']):
                images.append( link['href'] )
    for img in soup.findAll('img'):
        images.append(img['src'])
    
    print("images found: %s" % len(images))
    for img in images:
        scraped_images = os.listdir("static/images/scraped_images")
        random.shuffle(scraped_images)
        opened_images = []
        
        for i in range(0, len(scraped_images)):
            opened_images.append(Image.open("static/images/scraped_images/%s.jpg" % i))
        for x in range(0, len(opened_images)):
            opened_images[x].save(("static/images/scraped_images/%s" % scraped_images[x]), "JPEG")
        if ("50x50" not in img) and img not in IMAGE_HASHES:
            file = io.StringIO(urllib2.urlopen(img).read())
            img = Image.open(file)
            image_number = image_number + 1
            img.save("static/images/scraped_images/%s.jpg" % image_number, "JPEG")
            print("image saved!")'''

def main():
    print("scrape job initiated")
    #   4. Pick a random location, scrape recent posts and chose one to add
    for x in range(0, NUMBER_OF_POSTS):

        # 5. Pick a location randomly
        randomLocationUrl = random.randint(0,2)

        # 6. Collect regional Missed Connections posts linkToVisit
        craigslistMissedConnectionsUrls = CollectMissedConnectionsLink(randomLocationUrl)

        # 7. Shuffle the collected links to randomize selection
        random.shuffle(craigslistMissedConnectionsUrls)

        # 8. Get Missed Connections post body from the new links
        craigslistMissedConnectionsUrls = CollectMissedConnectionsLink(randomLocationUrl)

        # 9. Get a random number and use it to select the post to be added
        randomPostUrl = random.randint(0,len(craigslistMissedConnectionsUrls)-1)
        finalUrl = craigslistMissedConnectionsUrls[randomPostUrl]

        # 12. Check if it's already in the store, if not add it and scrape any images found in it
        pageContent = GetPageContent(finalUrl)

        data = GetQueryData(pageContent, finalUrl, randomLocationUrl)

        query =  "INSERT INTO posts_scraped (title, body, location, time, hash) VALUES (%s, %s, %s, %s, %s);"
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require', user=os.environ.get('DATABASE_USER'), password=os.environ.get('DATABASE_PASSWORD'))
            cursor = conn.cursor()
            t = cursor.execute(query, data)
            conn.commit()
            cursor.close()
            conn.close()
            print("Post has been added to the database\n")
        except Exception as e:
            print("Error %s" % e)
        ScrapeImages(finalUrl)
        
    #scraped_images = os.listdir("static/images/scraped_images")
    #random.shuffle(scraped_images)
    #opened_images = []
    csv = retrieve_posts_csv()
    csv_file = open('output.csv', 'w')
    csv_file.write(csv)
    csv_file.close()

    upload_to_aws('output.csv', 'mixed-connections', 'output_%s.csv' % datetime.datetime.now())

    # commented out 2020-11-25 because occasionally its failing and I'm not using it anyway
    '''for i in range(0, len(scraped_images)-1):
        opened_images.append(Image.open("static/images/scraped_images/%s.jpg" % i))
        
    for x in range(0, len(opened_images)):
        opened_images[x].save(("static/images/scraped_images/%s" % scraped_images[x]), "JPEG")
    im = Image.new('RGB', (200,200), (0,0,0))
    im.save('static/images/scraped_images/mix.gif', save_all=True, append_images=opened_images)
    upload_to_aws('static/images/scraped_images/mix.gif', 'mixed-connections-images', 'mix_%s.gif' % (datetime.datetime.now()))
    '''
    return

if __name__ == "__main__":
    main()