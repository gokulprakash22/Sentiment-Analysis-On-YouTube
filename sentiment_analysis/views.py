from django.shortcuts import render
# Importing packages
import urllib.request
import urllib.parse
import urllib.error
from bs4 import BeautifulSoup
import ssl
import json
import ast
import json
import csv
import os
import pickle
import re
import matplotlib.pyplot as plt
import google.oauth2.credentials
import googletrans
from urllib.request import Request, urlopen
from googletrans import Translator
from textblob import TextBlob
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from django.http import HttpResponse




# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and client_secret.
THIS_FOLDER=os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(THIS_FOLDER,'client_secret.json')
TOKEN_PICKLE=os.path.join(THIS_FOLDER,'token.pickle')

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'

def get_authenticated_service():
    credentials = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            credentials = pickle.load(token)
    #  Check if the credentials are invalid or do not exist
    if not credentials or not credentials.valid:
        # Check if the credentials have expired
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            credentials = flow.run_console()

        # Save the credentials for the next run
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(credentials, token)

    return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)


def write_to_csv(comments):
    pass


def draw_piechart():
    positive = video_details['POSITIVE']
    negative = video_details['NEGATIVE']
    neutral = video_details['NEUTRAL']
    positive_num = video_details['POSITIVE_NUM']
    negative_num = video_details['NEGATIVE_NUM']
    neutral_num = video_details['NEUTRAL_NUM']
    labels = ['Positive [' + str(positive) + '%]\nCount : ' + str(positive_num),
              'Negative [' + str(negative) + '%]\nCount : ' + str(negative_num),
              'Neutral [' + str(neutral) + '%]\nCount : ' + str(neutral_num)]
    sizes = [positive, negative, neutral]
    name = [str(positive) + '%', str(negative) + '%', str(neutral) + '%']
    colors = ['blue', 'red', 'yellow']
    patches, texts = plt.pie(sizes, colors=colors, startangle=90, labels=name)
    plt.legend(patches, labels, loc="best")
    plt.title("Youtube comments analysis Pie Chart")
    plt.axis('equal')
    plt.tight_layout()
    plt.show()


def make_report():
    global resstr2
    resstr2=''
    resstr2+="TITLE : "+video_details['TITLE']
    resstr2+="\nCHANNEL NAME : "+video_details['CHANNEL_NAME']
    resstr2+="\nNUMBER OF VIEWS : "+video_details['NUMBER_OF_VIEWS']
    resstr2+="\nLIKES : "+video_details['LIKES']
    resstr2+="\nDISLIKES : "+video_details['DISLIKES']
    resstr2+="\nNUMBER OF SUBSCRIPTIONS : "+video_details['NUMBER_OF_SUBSCRIPTIONS']
    resstr2 += "\nNUMBER OF POSITIVE COMMENTS : " + str(video_details['POSITIVE_NUM'])
    resstr2 += "\nNUMBER OF NEGATIVE COMMENTS : " + str(video_details['NEGATIVE_NUM'])
    resstr2 += "\nNUMBER OF NEUTRAL COMMENTS : " + str(video_details['NEUTRAL_NUM'])

    positive_num = video_details['POSITIVE_NUM']
    negative_num = video_details['NEGATIVE_NUM']
    neutral_num = video_details['NEUTRAL_NUM']
    positive_percent = 100 * float(positive_num) / float(positive_num + negative_num + neutral_num)
    negative_percent = 100 * float(negative_num) / float(positive_num + negative_num + neutral_num)
    neutral_percent = 100 * float(neutral_num) / float(positive_num + negative_num + neutral_num)
    positive = float(format(positive_percent, '.2f'))
    negative = float(format(negative_percent, '.2f'))
    neutral = float(format(neutral_percent, '.2f'))

    video_details['POSITIVE'] = positive
    video_details['NEGATIVE'] = negative
    video_details['NEUTRAL'] = neutral
    resstr2 += "\nPOSITIVE : NEGATIVE : NEUTRAL :: " + str(positive) + " : " + str(negative) + " : " + str(neutral)

    if (video_details['POLARITY'] > 0):
        resstr2+= "\nOVERALL : Positive comments with Polarity "+str(video_details['POLARITY'])
        print("OVERALL : Positive reviews with Polarity",video_details['POLARITY'])
    elif (video_details['POLARITY'] < 0):
        resstr2+= "\nOVERALL : Negative reviews with Polarity " + str(video_details['POLARITY'])
        print("OVERALL : Negative comments with Polarity",video_details['POLARITY'])
    elif (video_details['POLARITY'] == 0):
        resstr2+= "\nOVERALL : Neutral reviews with Polarity " + str(video_details['POLARITY'])
        print("OVERALL : Neutral comments with Polarity",video_details['POLARITY'])



def get_details(url):
    # Making the website believe that you are accessing it using a mozilla browser
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    webpage = urlopen(req).read()

    # Creating a BeautifulSoup object of the html page for easy extraction of data.
    soup = BeautifulSoup(webpage, 'html.parser')
    html = soup.prettify('utf-8')

    for span in soup.findAll('span', attrs={'class': 'watch-title'}):
        video_details['TITLE'] = span.text.strip()

    for script in soup.findAll('script', attrs={'type': 'application/ld+json'}):
        channelDesctiption = json.loads(script.text.strip())
        video_details['CHANNEL_NAME'] = channelDesctiption['itemListElement'][0]['item']['name']

    for div in soup.findAll('div', attrs={'class': 'watch-view-count'}):
        video_details['NUMBER_OF_VIEWS'] = div.text.strip()

    for button in soup.findAll('button', attrs={'title': 'I like this'}):
        video_details['LIKES'] = button.text.strip()

    for button in soup.findAll('button', attrs={'title': 'I dislike this'}):
        video_details['DISLIKES'] = button.text.strip()

    for span in soup.findAll('span', attrs={'class': 'yt-subscription-button-subscriber-count-branded-horizontal yt-subscriber-count'}):
        video_details['NUMBER_OF_SUBSCRIPTIONS'] = span.text.strip()



def get_video_comments(request,service, **kwargs):
    comments = []
    results = service.commentThreads().list(**kwargs).execute()
    num=1
    positive_num = 0
    negative_num = 0
    neutral_num = 0
    polarity = 0
    translator = Translator()
    flag=0
    global resstr
    resstr=''
    while results:
        for item in results['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            comments.append(comment)

            try:
                inp = translator.translate(comment).text
            except:
                inp=comment
            analyzer = TextBlob(inp)
            polarity += analyzer.sentiment.polarity
            if analyzer.sentiment.polarity > 0:
                positive_num += 1
                resstr+=str(num)+' : Positive comment : '+comment+'\n'
                print(num, ": Positive comment :", comment)
                num += 1


            elif analyzer.sentiment.polarity < 0:
                negative_num += 1
                resstr += str(num) + ' : Positive comment : ' + comment + '\n'
                print(num, ": Negative comment :", comment)
                num += 1

            elif analyzer.sentiment.polarity == 0:
                neutral_num += 1
                resstr += str(num) + ' : Positive comment : ' + comment + '\n'
                print(num, ": Neutral comment :", comment)
                num += 1


            if(num>100):
                flag=1
                break
        if (flag == 1):
            break
        if 'nextPageToken' in results:
            kwargs['pageToken'] = results['nextPageToken']
            results = service.commentThreads().list(**kwargs).execute()
        else:
            break

    polarity = float(format(polarity, '.2f'))
    video_details['POLARITY']=polarity
    video_details['POSITIVE_NUM'] = positive_num
    video_details['NEGATIVE_NUM'] = negative_num
    video_details['NEUTRAL_NUM'] = neutral_num

    return comments


def get_videos(service, **kwargs):
    final_results = []
    results = service.search().list(**kwargs).execute()

    i = 0
    max_pages = 3
    num=1
    while results and i < max_pages:
        final_results.extend(results['items'])
        for item in final_results:
            title = item['snippet']['title']
            print(num,":",title)
            num+=1
        # Check if another page exists
        if 'nextPageToken' in results:
            kwargs['pageToken'] = results['nextPageToken']
            results = service.search().list(**kwargs).execute()
            i += 1
        else:
            break
    return final_results


def search_videos_by_keyword(service, **kwargs):
    results = get_videos(service, **kwargs)
    item=int(input("Enter video number :"))
    video_id = results[item-1]['id']['videoId']


def search_videos_by_url(request,x, service, **kwargs):
    video_id = x
    url='https://www.youtube.com/watch?v='+video_id
    get_details(url)
    final_result = []
    comments = get_video_comments(request,service, part='snippet', videoId=video_id, textFormat='plainText')
    final_result.extend([(video_id, comment) for comment in comments])


# Create your views here.
video_details={}
resstr=''
resstr2=''
def index(request):
    return render(request,'index.html')

def search(request):
    keyword = request.POST.get("destination","guest")
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    try:
        service = get_authenticated_service()
    except:
        os.remove(TOKEN_PICKLE)
        service = get_authenticated_service()
    if (re.search("v=", keyword) != None):
        x = re.split("v=", keyword)
        x = x[1]
        search_videos_by_url(request, x, service, q=keyword, part='id,snippet', eventType='completed', type='video')
        make_report()
        return render(request, 'results.html', {'comments': resstr, 'report': resstr2})
    else:
        # search_videos_by_url(service, q=keyword, part='id,snippet', eventType='completed', type='video')
        return render(request, 'videos.html', {'name': 'Sriram'})




def pie(request):
    draw_piechart()
    return render(request, 'results.html', {'comments': resstr, 'report': resstr2})