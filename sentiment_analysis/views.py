# Importing packages
from django.shortcuts import render
from django.http import HttpResponse
from django.http import FileResponse
import os
# For parsing URL
from urllib.parse import urlparse, urlencode, parse_qs
# For extracting comments from YouTube
import googleapiclient.discovery
# For translating comments into English
from googletrans import Translator
# For sentiment analysing the translated comment
from textblob import TextBlob


def get_video_id(url):
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p['v'][0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    return None

def get_video_details(videoId):
    global video_details
    video_details={}
    api_service_name = "youtube"
    api_version = "v3"
    DEVELOPER_KEY = os.environ.get('DEVELOPER_KEY')
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey = DEVELOPER_KEY)
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=videoId
    )
    response = request.execute()
    video_details["TITLE"] = response["items"][0]["snippet"]["title"]
    video_details["PUBLISHED_AT"] = response["items"][0]["snippet"]["publishedAt"]
    video_details["CHANNEL_NAME"] = response["items"][0]["snippet"]["channelTitle"]
    video_details["VIEWS_COUNT"] = response["items"][0]["statistics"]["viewCount"]
    video_details["LIKES_COUNT"] = response["items"][0]["statistics"]["likeCount"]
    video_details["DISLIKES_COUNT"] = response["items"][0]["statistics"]["dislikeCount"]
    video_details["COMMENTS_COUNT"] = response["items"][0]["statistics"]["commentCount"]
    video_details["POLARITY"] = 0

def sentiment_analysis(mat):
    translator = Translator()
    overall_polarity = video_details["POLARITY"]
    for item in mat["items"]:       
        comments = {}
        comment = item["snippet"]["topLevelComment"]
        comments["author"] = comment["snippet"]["authorDisplayName"]
        comments["comment"] = comment["snippet"]["textDisplay"]
        comments["likecount"] = comment["snippet"]["likeCount"]
        comments["publishedAt"] = comment["snippet"]["publishedAt"]
        try:
            inp = translator.translate(comment["snippet"]["textDisplay"]).text
        except:
            inp = comment["snippet"]["textDisplay"]
        analyzer = TextBlob(inp)
        polarity = analyzer.sentiment.polarity
        comments["polarity"] = polarity
        overall_polarity += polarity
        if polarity > 0:
            positive_comments.append(comments)
        elif polarity < 0:
            negative_comments.append(comments)
        else:
            neutral_comments.append(comments)
    overall_polarity = float(format(overall_polarity, '.2f'))
    video_details['POLARITY']=overall_polarity

def get_video_comments(videoId):
    global positive_comments
    global negative_comments
    global neutral_comments
    positive_comments = []
    negative_comments = []
    neutral_comments = []
    api_service_name = "youtube"
    api_version = "v3"
    DEVELOPER_KEY = os.environ.get('DEVELOPER_KEY')
    youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey = DEVELOPER_KEY)
    request = youtube.commentThreads().list(
        part="snippet,replies",
        videoId=videoId,
        textFormat="plainText"
    )
    response = request.execute()
    nextPageToken = response.get("nextPageToken")
    sentiment_analysis(response)
    global comments_count
    comments_count=20
    while nextPageToken:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=videoId,
            textFormat="plainText",
            pageToken=nextPageToken
        )
        response = request.execute()
        nextPageToken = response.get("nextPageToken")
        sentiment_analysis(response)
        comments_count+=20
        print(comments_count)
        if(comments_count>=200):
            break

def make_video_report():
    global summary
    global positive_str
    global negative_str
    global neutral_str
    summary=""
    positive_str=""
    negative_str=""
    neutral_str=""
    summary+="VIDEO TITLE : "+video_details['TITLE']
    summary+="\nVIDEO PUBLISHED AT : "+video_details['PUBLISHED_AT']
    summary+="\nCHANNEL NAME : "+video_details['CHANNEL_NAME']
    summary+="\nVIEWS COUNT : "+video_details['VIEWS_COUNT']
    summary+="\nLIKES COUNT : "+video_details['LIKES_COUNT']
    summary+="\nDISLIKES COUNT : "+video_details['DISLIKES_COUNT']
    summary+="\nCOMMENTS COUNT : "+video_details['COMMENTS_COUNT']
    positive_comments_count = len(positive_comments)
    negative_comments_count = len(negative_comments)
    neutral_comments_count = len(neutral_comments)
    positive_percent = float(format(100 * float(positive_comments_count) / float(positive_comments_count + negative_comments_count + neutral_comments_count),'.2f'))
    negative_percent = float(format(100 * float(negative_comments_count) / float(positive_comments_count + negative_comments_count + neutral_comments_count),'.2f'))
    neutral_percent = float(format(100 * float(neutral_comments_count) / float(positive_comments_count + negative_comments_count + neutral_comments_count),'.2f'))
    video_details['POSITIVE_COUNT'] = positive_comments_count
    video_details['NEGATIVE_COUNT'] = negative_comments_count
    video_details['NEUTRAL_COUNT'] = neutral_comments_count
    video_details['POSITIVE_PERCENT'] = positive_percent
    video_details['NEGATIVE_PERCENT'] = negative_percent
    video_details['NEUTRAL_PERCENT'] = neutral_percent
    summary+= "\nPOSITIVE COMMENTS COUNT: "+str(positive_comments_count)+("+" if comments_count>=1000 else "")+" ("+str(positive_percent)+"%)"
    summary+= "\nNEGATIVE COMMENTS COUNT: "+str(negative_comments_count)+("+" if comments_count>=1000 else "")+" ("+str(negative_percent)+"%)"
    summary+= "\nNEUTRAL COMMENTS COUNT: "+str(neutral_comments_count)+("+" if comments_count>=1000 else "")+" ("+str(neutral_percent)+"%)"
    if (video_details['POLARITY'] > 0):
        summary+= "\nOVERALL : Positive comments with Overall Polarity "+str(video_details['POLARITY'])
    elif (video_details['POLARITY'] < 0):
        summary+= "\nOVERALL : Negative reviews with Overall Polarity " + str(video_details['POLARITY'])
    elif (video_details['POLARITY'] == 0):
        summary+= "\nOVERALL : Neutral reviews with Overall Polarity " + str(video_details['POLARITY'])
    for index,comment in enumerate(positive_comments):
        positive_str+=str(index+1)+") "+comment["author"]+": "+comment["comment"]+"\nLikes Count: "+str(comment["likecount"])+", Published At: "+comment["publishedAt"]+"\n\n"
    for index,comment in enumerate(negative_comments):
        negative_str+=str(index+1)+") "+comment["author"]+": "+comment["comment"]+"\nLikes Count: "+str(comment["likecount"])+", Published At: "+comment["publishedAt"]+"\n\n"
    for index,comment in enumerate(neutral_comments):
        neutral_str+=str(index+1)+") "+comment["author"]+": "+comment["comment"]+"\nLikes Count: "+str(comment["likecount"])+", Published At: "+comment["publishedAt"]+"\n\n"

def write_to_csv():
    import csv
    with open('comments.csv', 'w') as comments_file:
        comments_writer = csv.writer(comments_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        comments_writer.writerow(['S.No', 'Category', 'Author', 'Comment', 'Likes Count', 'Published At', 'Polarity'])
        for index,comment in enumerate(positive_comments):
            try:
                comments_writer.writerow([index+1,"Positive Comment",comment["author"],comment["comment"],comment["likecount"],comment["publishedAt"],comment["polarity"]])
            except:
                comments_writer.writerow([index+1,"Positive Comment","Can't Decode in CSV","Can't Decode in CSV",comment["likecount"],comment["publishedAt"],comment["polarity"]])
        for index,comment in enumerate(negative_comments):
            try:
                comments_writer.writerow([index+1,"Negative Comment",comment["author"],comment["comment"],comment["likecount"],comment["publishedAt"],comment["polarity"]])
            except:
                comments_writer.writerow([index+1,"Negative Comment","Can't Decode in CSV","Can't Decode in CSV",comment["likecount"],comment["publishedAt"],comment["polarity"]])
        for index,comment in enumerate(neutral_comments):
            try:
                comments_writer.writerow([index+1,"Neutral Comment",comment["author"],comment["comment"],comment["likecount"],comment["publishedAt"],comment["polarity"]])
            except:
                comments_writer.writerow([index+1,"Neutral Comment","Can't Decode in CSV","Can't Decode in CSV",comment["likecount"],comment["publishedAt"],comment["polarity"]])

def draw_piechart():
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    positive_comments_count = video_details['POSITIVE_COUNT']
    negative_comments_count = video_details['NEGATIVE_COUNT']
    neutral_comments_count = video_details['NEUTRAL_COUNT']
    positive_percent = video_details['POSITIVE_PERCENT']
    negative_percent = video_details['NEGATIVE_PERCENT']
    neutral_percent = video_details['NEUTRAL_PERCENT']
    labels=['Positive : ' + str(positive_percent) + '%\nCount : ' + str(positive_comments_count)+("+" if comments_count>=1000 else ""),
            'Negative : ' + str(negative_percent) + '%\nCount : ' + str(negative_comments_count)+("+" if comments_count>=1000 else ""),
            'Neutral : ' + str(neutral_percent) + '%\nCount : ' + str(neutral_comments_count)+("+" if comments_count>=1000 else "")]
    sizes = [positive_percent, negative_percent, neutral_percent]
    name = [str(positive_percent) + '%', str(negative_percent) + '%', str(neutral_percent) + '%']
    colors = ['green', 'red', 'yellow']
    patches, texts = plt.pie(sizes, colors=colors, startangle=90, labels=name)
    plt.legend(patches, labels, loc="best")
    plt.title("Youtube Comments Analysis Pie Chart")
    plt.axis('equal')
    plt.tight_layout()
    plt.show()
    plt.close()


# Views
video_details={}
positive_comments = []
negative_comments = []
neutral_comments = []
summary=""
positive_str=""
negative_str=""
neutral_str=""
comments_count=0

def index(request):
    return render(request,'index.html')

def report(request):
    url = request.POST["destination"]
    videoId=get_video_id(url)
    if(videoId==None):
        return render(request,'index.html')
    get_video_details(videoId)
    get_video_comments(videoId)
    make_video_report()
    write_to_csv()
    return render(request, 'results.html', {'summary': summary, 'positive_str':positive_str,'negative_str':negative_str,'neutral_str':neutral_str})

def csv(request):
    csv_file = open('comments.csv', 'rb')
    response = FileResponse(csv_file)
    return response

def pie_chart(request):
    error_str=""
    try:
        draw_piechart()
    except:
        error_str="Some Problem occured. Please Try again later"
    return render(request, 'results.html', {'summary': summary, 'positive_str':positive_str,'negative_str':negative_str,'neutral_str':neutral_str, 'error_str':error_str})