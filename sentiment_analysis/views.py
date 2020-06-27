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
    video_details["TOTAL_COMMENTS_EXTRACTED"]=0
    video_details["VIDEO_ID"] = videoId

def sentiment_analysis(mat):
    global video_details
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

def get_video_comments():
    global positive_comments
    global negative_comments
    global neutral_comments
    global nextPageToken
    global video_details
    positive_comments = []
    negative_comments = []
    neutral_comments = []
    request = youtube.commentThreads().list(
        part="snippet,replies",
        videoId=video_details["VIDEO_ID"],
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
            videoId=video_details["VIDEO_ID"],
            textFormat="plainText",
            pageToken=nextPageToken
        )
        response = request.execute()
        nextPageToken = response.get("nextPageToken")
        sentiment_analysis(response)
        comments_count+=20
        print(comments_count)
        if(comments_count%100==0):
            break

def get_more_comments():
    global positive_comments
    global negative_comments
    global neutral_comments
    global nextPageToken
    global comments_count
    global video_details
    while nextPageToken:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_details["VIDEO_ID"],
            textFormat="plainText",
            pageToken=nextPageToken
        )
        response = request.execute()
        nextPageToken = response.get("nextPageToken")
        sentiment_analysis(response)
        comments_count+=20
        print(comments_count)
        if(comments_count%100==0):
            break

def make_video_report():
    global summary
    global positive_str
    global negative_str
    global neutral_str
    global nextPageToken
    global video_details
    summary=""
    positive_str=""
    negative_str=""
    neutral_str=""
    summary+="VIDEO TITLE : "+video_details['TITLE']
    summary+="\nVIDEO PUBLISHED AT : "+video_details['PUBLISHED_AT']
    summary+="\nVIDEO ID : "+video_details['VIDEO_ID']
    summary+="\nCHANNEL NAME : "+video_details['CHANNEL_NAME']
    summary+="\nVIEWS COUNT : "+video_details['VIEWS_COUNT']
    summary+="\nLIKES COUNT : "+video_details['LIKES_COUNT']
    summary+="\nDISLIKES COUNT : "+video_details['DISLIKES_COUNT']
    summary+="\nCOMMENTS COUNT : "+video_details['COMMENTS_COUNT']
    video_details['POSITIVE_COUNT'] = len(positive_comments)
    video_details['NEGATIVE_COUNT'] = len(negative_comments)
    video_details['NEUTRAL_COUNT'] = len(neutral_comments)
    video_details["TOTAL_COMMENTS_EXTRACTED"] = video_details['POSITIVE_COUNT']+video_details['NEGATIVE_COUNT']+video_details['NEUTRAL_COUNT']
    video_details['POSITIVE_PERCENT'] = float(format(100 * float(video_details['POSITIVE_COUNT']) / float(video_details['POSITIVE_COUNT'] + video_details['NEGATIVE_COUNT'] + video_details['NEUTRAL_COUNT']),'.2f'))
    video_details['NEGATIVE_PERCENT'] = float(format(100 * float(video_details['NEGATIVE_COUNT']) / float(video_details['POSITIVE_COUNT'] + video_details['NEGATIVE_COUNT'] + video_details['NEUTRAL_COUNT']),'.2f'))
    video_details['NEUTRAL_PERCENT'] = float(format(100 * float(video_details['NEUTRAL_COUNT']) / float(video_details['POSITIVE_COUNT'] + video_details['NEGATIVE_COUNT'] + video_details['NEUTRAL_COUNT']),'.2f'))
    summary+= "\nPOSITIVE COMMENTS COUNT: "+str(video_details['POSITIVE_COUNT'])+("+" if nextPageToken else "")+" ("+str(video_details['POSITIVE_PERCENT'])+"%)"
    summary+= "\nNEGATIVE COMMENTS COUNT: "+str(video_details['NEGATIVE_COUNT'])+("+" if nextPageToken else "")+" ("+str(video_details['NEGATIVE_COUNT'])+"%)"
    summary+= "\nNEUTRAL COMMENTS COUNT: "+str(video_details['NEUTRAL_COUNT'])+("+" if nextPageToken else "")+" ("+str(video_details['NEUTRAL_PERCENT'])+"%)"
    if (video_details['POLARITY'] > 0):
        summary+= "\nOVERALL : Positive Comments With Overall Polarity "+str(video_details['POLARITY'])
    elif (video_details['POLARITY'] < 0):
        summary+= "\nOVERALL : Negative Comments With Overall Polarity " + str(video_details['POLARITY'])
    elif (video_details['POLARITY'] == 0):
        summary+= "\nOVERALL : Neutral Comments With Overall Polarity " + str(video_details['POLARITY'])
    for index,comment in enumerate(positive_comments):
        positive_str+=str(index+1)+") "+comment["author"]+": "+comment["comment"]+"\nLikes Count: "+str(comment["likecount"])+", Published At: "+comment["publishedAt"]+"\n\n"
    for index,comment in enumerate(negative_comments):
        negative_str+=str(index+1)+") "+comment["author"]+": "+comment["comment"]+"\nLikes Count: "+str(comment["likecount"])+", Published At: "+comment["publishedAt"]+"\n\n"
    for index,comment in enumerate(neutral_comments):
        neutral_str+=str(index+1)+") "+comment["author"]+": "+comment["comment"]+"\nLikes Count: "+str(comment["likecount"])+", Published At: "+comment["publishedAt"]+"\n\n"

def write_to_csv():
    import csv
    global nextPageToken
    global video_details
    with open('comments.csv', 'w') as comments_file:
        comments_writer = csv.writer(comments_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        comments_writer.writerow(['SUMMARY'])
        comments_writer.writerow(['S.No','Details','Value'])
        comments_writer.writerow([1,'Video Title', video_details['TITLE']])
        comments_writer.writerow([2,'Video Published At', video_details['PUBLISHED_AT']])
        comments_writer.writerow([3,'Video ID', video_details['VIDEO_ID']])
        comments_writer.writerow([4,'Channel Name', video_details['CHANNEL_NAME']])
        comments_writer.writerow([5,'Views Count', video_details['VIEWS_COUNT']])
        comments_writer.writerow([6,'Likes Count', video_details['LIKES_COUNT']])
        comments_writer.writerow([7,'Dislikes Count', video_details['DISLIKES_COUNT']])
        comments_writer.writerow([8,'Comments Count', video_details['COMMENTS_COUNT']])
        comments_writer.writerow([9,'Positive Comments Count', str(video_details['POSITIVE_COUNT'])+("+" if nextPageToken else "")+" ("+str(video_details['POSITIVE_PERCENT'])+"%)"])
        comments_writer.writerow([10,'Negative Comments Count', str(video_details['NEGATIVE_COUNT'])+("+" if nextPageToken else "")+" ("+str(video_details['NEGATIVE_PERCENT'])+"%)"])
        comments_writer.writerow([11,'Neutral Comments Count', str(video_details['NEUTRAL_COUNT'])+("+" if nextPageToken else "")+" ("+str(video_details['NEUTRAL_PERCENT'])+"%)"])
        if (video_details['POLARITY'] > 0):
            comments_writer.writerow([12,'OVERALL', 'Positive Comments With Overall Polarity '+str(video_details['POLARITY'])])
        elif (video_details['POLARITY'] < 0):
            comments_writer.writerow([12,'OVERALL', 'Negative Comments With Overall Polarity '+str(video_details['POLARITY'])])
        elif (video_details['POLARITY'] == 0):
            comments_writer.writerow([12,'OVERALL', 'Neutral Comments With Overall Polarity '+str(video_details['POLARITY'])])
        comments_writer.writerow([])
        comments_writer.writerow(['COMMENTS'])
        comments_writer.writerow(['S.No', 'Category', 'Author', 'Comment', 'Likes Count', 'Published At', 'Polarity'])
        for index,comment in enumerate(positive_comments):
            try:
                comments_writer.writerow([index+1,"Positive Comment",comment["author"],comment["comment"],comment["likecount"],comment["publishedAt"],comment["polarity"]])
            except:
                comments_writer.writerow([index+1,"Positive Comment","Can't Decode In CSV","Can't Decode In CSV",comment["likecount"],comment["publishedAt"],comment["polarity"]])
        for index,comment in enumerate(negative_comments):
            try:
                comments_writer.writerow([index+1,"Negative Comment",comment["author"],comment["comment"],comment["likecount"],comment["publishedAt"],comment["polarity"]])
            except:
                comments_writer.writerow([index+1,"Negative Comment","Can't Decode In CSV","Can't Decode In CSV",comment["likecount"],comment["publishedAt"],comment["polarity"]])
        for index,comment in enumerate(neutral_comments):
            try:
                comments_writer.writerow([index+1,"Neutral Comment",comment["author"],comment["comment"],comment["likecount"],comment["publishedAt"],comment["polarity"]])
            except:
                comments_writer.writerow([index+1,"Neutral Comment","Can't Decode In CSV","Can't Decode In CSV",comment["likecount"],comment["publishedAt"],comment["polarity"]])

def draw_piechart():
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    global nextPageToken
    global video_details
    labels=['Positive : ' + str(video_details['POSITIVE_PERCENT']) + '%\nCount : ' + str(video_details['POSITIVE_COUNT'])+("+" if nextPageToken else ""),
            'Negative : ' + str(video_details['NEGATIVE_PERCENT']) + '%\nCount : ' + str(video_details['NEGATIVE_COUNT'])+("+" if nextPageToken else ""),
            'Neutral : ' + str(video_details['NEUTRAL_PERCENT']) + '%\nCount : ' + str(video_details['NEUTRAL_COUNT'])+("+" if nextPageToken else "")]
    sizes = [video_details['POSITIVE_PERCENT'], video_details['NEGATIVE_PERCENT'], video_details['NEUTRAL_PERCENT']]
    name = [str(video_details['POSITIVE_PERCENT']) + '%', str(video_details['NEGATIVE_PERCENT']) + '%', str(video_details['NEUTRAL_PERCENT']) + '%']
    colors = ['green', 'red', 'yellow']
    patches, texts = plt.pie(sizes, colors=colors, startangle=90, labels=name)
    plt.legend(patches, labels, loc="best")
    plt.title(video_details['TITLE']+" Video Comments Analysis Pie Chart")
    plt.axis('equal')
    plt.savefig('piechart.png')
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
nextPageToken=None
api_service_name = "youtube"
api_version = "v3"
DEVELOPER_KEY = os.environ.get('DEVELOPER_KEY')
youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey = DEVELOPER_KEY)

def index(request):
    return render(request,'index.html')

def report(request):
    url = request.POST["destination"]
    videoId=get_video_id(url)
    if(videoId==None):
        return render(request,'index.html')
    get_video_details(videoId)
    get_video_comments()
    make_video_report()
    write_to_csv()
    draw_piechart()
    return render(request, 'results.html', {'summary': summary, 'positive_str':positive_str,'negative_str':negative_str,'neutral_str':neutral_str,'nextPageToken':nextPageToken,'total_comments_extracted':video_details["TOTAL_COMMENTS_EXTRACTED"]})

def more_comments(request):
    get_more_comments()
    make_video_report()
    write_to_csv()
    draw_piechart()
    return render(request, 'results.html', {'summary': summary, 'positive_str':positive_str,'negative_str':negative_str,'neutral_str':neutral_str,'nextPageToken':nextPageToken,'total_comments_extracted':video_details["TOTAL_COMMENTS_EXTRACTED"]})

def csv(request):
    csv_file = open('comments.csv', 'rb')
    response = FileResponse(csv_file)
    return response

def pie_chart(request):
    pie_chart = open('piechart.png', 'rb')
    response = FileResponse(pie_chart)
    return response