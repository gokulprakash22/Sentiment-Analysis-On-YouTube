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


#YouTube API
api_service_name = "youtube"
api_version = "v3"
DEVELOPER_KEY = os.environ.get('DEVELOPER_KEY')
youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey = DEVELOPER_KEY)


#functions
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
    video_details["VIDEO_COMMENTS_COUNT"] = response["items"][0]["statistics"]["commentCount"]
    video_details["POLARITY"] = 0
    video_details["TOTAL_COMMENTS_EXTRACTED"]=0
    video_details["VIDEO_ID"] = videoId
    video_details["POSITIVE_COMMENTS"]=[]
    video_details["NEGATIVE_COMMENTS"]=[]
    video_details["NEUTRAL_COMMENTS"]=[]
    video_details["COMMENTS_COUNT"]=0
    video_details["NEXT_PAGE_TOKEN"]=None
    video_details["SUMMARY"]=''
    video_details["POSITIVE_STR"]=''
    video_details["NEGATIVE_STR"]=''
    video_details["NEUTRAL_STR"]=''
    video_details["POSITIVE_COUNT"]=0
    video_details["NEGATIVE_COUNT"]=0
    video_details["NEUTRAL_COUNT"]=0
    video_details["POSITIVE_PERCENT"]=0
    video_details["NEGATIVE_PERCENT"]=0
    video_details["NEUTRAL_PERCENT"]=0
    return video_details

def sentiment_analysis(mat,video_details):
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
        overall_polarity += polarity
        polarity = float(format(polarity, '.2f'))
        comments["polarity"] = polarity
        if polarity > 0:
            video_details["POSITIVE_COMMENTS"].append(comments)
        elif polarity < 0:
            video_details["NEGATIVE_COMMENTS"].append(comments)
        else:
            video_details["NEUTRAL_COMMENTS"].append(comments)
    overall_polarity = float(format(overall_polarity, '.2f'))
    video_details["POLARITY"]=overall_polarity
    return video_details

def get_video_comments(video_details):
    request = youtube.commentThreads().list(
        part="snippet,replies",
        videoId=video_details["VIDEO_ID"]
    )
    response = request.execute()
    video_details["NEXT_PAGE_TOKEN"] = response.get("nextPageToken")
    video_details=sentiment_analysis(response,video_details)
    video_details["COMMENTS_COUNT"]=20
    while video_details["NEXT_PAGE_TOKEN"]:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_details["VIDEO_ID"],
            pageToken=video_details["NEXT_PAGE_TOKEN"]
        )
        response = request.execute()
        video_details["NEXT_PAGE_TOKEN"] = response.get("nextPageToken")
        video_details=sentiment_analysis(response,video_details)
        video_details["COMMENTS_COUNT"]+=20
        print(video_details["COMMENTS_COUNT"])
        if(video_details["COMMENTS_COUNT"]%60==0):
            return video_details
            break
    return video_details

def get_more_comments(video_details):
    while video_details["NEXT_PAGE_TOKEN"]:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_details["VIDEO_ID"],
            pageToken=video_details["NEXT_PAGE_TOKEN"]
        )
        response = request.execute()
        video_details["NEXT_PAGE_TOKEN"] = response.get("nextPageToken")
        video_details=sentiment_analysis(response,video_details)
        video_details["COMMENTS_COUNT"]+=20
        print(video_details["COMMENTS_COUNT"])
        if(video_details["COMMENTS_COUNT"]%60==0):
            return video_details
            break
    return video_details

def make_video_report(video_details):
    video_details["SUMMARY"]=''
    video_details["POSITIVE_STR"]=''
    video_details["NEGATIVE_STR"]=''
    video_details["NEUTRAL_STR"]=''
    video_details["SUMMARY"]+="VIDEO TITLE : "+video_details["TITLE"]
    video_details["SUMMARY"]+="\nVIDEO PUBLISHED AT : "+video_details["PUBLISHED_AT"]
    video_details["SUMMARY"]+="\nVIDEO ID : "+video_details["VIDEO_ID"]
    video_details["SUMMARY"]+="\nCHANNEL NAME : "+video_details["CHANNEL_NAME"]
    video_details["SUMMARY"]+="\nVIEWS COUNT : "+str(video_details["VIEWS_COUNT"])
    video_details["SUMMARY"]+="\nLIKES COUNT : "+str(video_details["LIKES_COUNT"])
    video_details["SUMMARY"]+="\nDISLIKES COUNT : "+str(video_details["DISLIKES_COUNT"])
    video_details["SUMMARY"]+="\nCOMMENTS COUNT : "+str(video_details["VIDEO_COMMENTS_COUNT"])
    video_details["POSITIVE_COUNT"]=len(video_details["POSITIVE_COMMENTS"])
    video_details["NEGATIVE_COUNT"]=len(video_details["NEGATIVE_COMMENTS"])
    video_details["NEUTRAL_COUNT"]=len(video_details["NEUTRAL_COMMENTS"])
    video_details["TOTAL_COMMENTS_EXTRACTED"]=video_details["POSITIVE_COUNT"]+video_details["NEGATIVE_COUNT"]+video_details["NEUTRAL_COUNT"]
    video_details["POSITIVE_PERCENT"] = float(format(100 * float(video_details["POSITIVE_COUNT"]) / float(video_details["POSITIVE_COUNT"] + video_details["NEGATIVE_COUNT"] + video_details["NEUTRAL_COUNT"]),".2f"))
    video_details["NEGATIVE_PERCENT"] = float(format(100 * float(video_details["NEGATIVE_COUNT"]) / float(video_details["POSITIVE_COUNT"] + video_details["NEGATIVE_COUNT"] + video_details["NEUTRAL_COUNT"]),".2f"))
    video_details["NEUTRAL_PERCENT"] = float(format(100 * float(video_details["NEUTRAL_COUNT"]) / float(video_details["POSITIVE_COUNT"] + video_details["NEGATIVE_COUNT"] + video_details["NEUTRAL_COUNT"]),".2f"))
    video_details["SUMMARY"]+= "\nPOSITIVE COMMENTS COUNT: "+str(video_details["POSITIVE_COUNT"])+("+" if video_details["NEXT_PAGE_TOKEN"] else "")+" ("+str(video_details["POSITIVE_PERCENT"])+"%)"
    video_details["SUMMARY"]+= "\nNEGATIVE COMMENTS COUNT: "+str(video_details["NEGATIVE_COUNT"])+("+" if video_details["NEXT_PAGE_TOKEN"] else "")+" ("+str(video_details["NEGATIVE_PERCENT"])+"%)"
    video_details["SUMMARY"]+= "\nNEUTRAL COMMENTS COUNT: "+str(video_details["NEUTRAL_COUNT"])+("+" if video_details["NEXT_PAGE_TOKEN"] else "")+" ("+str(video_details["NEUTRAL_PERCENT"])+"%)"
    if (video_details["POLARITY"] > 0):
        video_details["SUMMARY"]+= "\nOVERALL : Positive Comments With Overall Polarity "+str(video_details["POLARITY"])
    elif (video_details["POLARITY"] < 0):
        video_details["SUMMARY"]+= "\nOVERALL : Negative Comments With Overall Polarity " + str(video_details["POLARITY"])
    elif (video_details["POLARITY"] == 0):
        video_details["SUMMARY"]+= "\nOVERALL : Neutral Comments With Overall Polarity " + str(video_details["POLARITY"])
    for index,comment in enumerate(video_details["POSITIVE_COMMENTS"]):
        video_details["POSITIVE_STR"]+=str(index+1)+") "+comment["author"]+": "+comment["comment"]+"\nLikes Count: "+str(comment["likecount"])+", Published At: "+comment["publishedAt"]+", Polarity: "+str(comment["polarity"])+"\n\n"
    for index,comment in enumerate(video_details["NEGATIVE_COMMENTS"]):
        video_details["NEGATIVE_STR"]+=str(index+1)+") "+comment["author"]+": "+comment["comment"]+"\nLikes Count: "+str(comment["likecount"])+", Published At: "+comment["publishedAt"]+", Polarity: "+str(comment["polarity"])+"\n\n"
    for index,comment in enumerate(video_details["NEUTRAL_COMMENTS"]):
        video_details["NEUTRAL_STR"]+=str(index+1)+") "+comment["author"]+": "+comment["comment"]+"\nLikes Count: "+str(comment["likecount"])+", Published At: "+comment["publishedAt"]+", Polarity: "+str(comment["polarity"])+"\n\n"
    return video_details

def write_to_csv(video_details):
    import csv
    with open("comments.csv", "w") as comments_file:
        comments_writer = csv.writer(comments_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        comments_writer.writerow(["SUMMARY"])
        comments_writer.writerow(["S.No","Details","Value"])
        comments_writer.writerow([1,"Video Title", video_details["TITLE"]])
        comments_writer.writerow([2,"Video Published At", video_details["PUBLISHED_AT"]])
        comments_writer.writerow([3,"Video ID", video_details["VIDEO_ID"]])
        comments_writer.writerow([4,"Channel Name", video_details["CHANNEL_NAME"]])
        comments_writer.writerow([5,"Views Count", video_details["VIEWS_COUNT"]])
        comments_writer.writerow([6,"Likes Count", video_details["LIKES_COUNT"]])
        comments_writer.writerow([7,"Dislikes Count", video_details["DISLIKES_COUNT"]])
        comments_writer.writerow([8,"Comments Count", video_details["COMMENTS_COUNT"]])
        comments_writer.writerow([9,"Positive Comments Count", str(video_details["POSITIVE_COUNT"])+("+" if video_details["NEXT_PAGE_TOKEN"] else "")+" ("+str(video_details["POSITIVE_PERCENT"])+"%)"])
        comments_writer.writerow([10,"Negative Comments Count", str(video_details["NEGATIVE_COUNT"])+("+" if video_details["NEXT_PAGE_TOKEN"] else "")+" ("+str(video_details["NEGATIVE_PERCENT"])+"%)"])
        comments_writer.writerow([11,"Neutral Comments Count", str(video_details["NEUTRAL_COUNT"])+("+" if video_details["NEXT_PAGE_TOKEN"] else "")+" ("+str(video_details["NEUTRAL_PERCENT"])+"%)"])
        if (video_details["POLARITY"] > 0):
            comments_writer.writerow([12,"Overall", "Positive Comments With Overall Polarity "+str(video_details["POLARITY"])])
        elif (video_details["POLARITY"] < 0):
            comments_writer.writerow([12,"Overall", "Negative Comments With Overall Polarity "+str(video_details["POLARITY"])])
        elif (video_details["POLARITY"] == 0):
            comments_writer.writerow([12,"Overall", "Neutral Comments With Overall Polarity "+str(video_details["POLARITY"])])
        comments_writer.writerow([])
        comments_writer.writerow(["COMMENTS"])
        comments_writer.writerow(["S.No", "Category", "Author", "Comment", "Likes Count", "Published At", "Polarity"])
        for index,comment in enumerate(video_details["POSITIVE_COMMENTS"]):
            try:
                comments_writer.writerow([index+1,"Positive Comment",comment["author"],comment["comment"],comment["likecount"],comment["publishedAt"],comment["polarity"]])
            except:
                comments_writer.writerow([index+1,"Positive Comment","Can't Decode In CSV","Can't Decode In CSV",comment["likecount"],comment["publishedAt"],comment["polarity"]])
        for index,comment in enumerate(video_details["NEGATIVE_COMMENTS"]):
            try:
                comments_writer.writerow([index+1,"Negative Comment",comment["author"],comment["comment"],comment["likecount"],comment["publishedAt"],comment["polarity"]])
            except:
                comments_writer.writerow([index+1,"Negative Comment","Can't Decode In CSV","Can't Decode In CSV",comment["likecount"],comment["publishedAt"],comment["polarity"]])
        for index,comment in enumerate(video_details["NEUTRAL_COMMENTS"]):
            try:
                comments_writer.writerow([index+1,"Neutral Comment",comment["author"],comment["comment"],comment["likecount"],comment["publishedAt"],comment["polarity"]])
            except:
                comments_writer.writerow([index+1,"Neutral Comment","Can't Decode In CSV","Can't Decode In CSV",comment["likecount"],comment["publishedAt"],comment["polarity"]])

def draw_piechart(video_details):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    labels=["Positive : " + str(video_details["POSITIVE_PERCENT"]) + "%\nCount : " + str(video_details["POSITIVE_COUNT"])+("+" if video_details["NEXT_PAGE_TOKEN"] else ""),
            "Negative : " + str(video_details["NEGATIVE_PERCENT"]) + "%\nCount : " + str(video_details["NEGATIVE_COUNT"])+("+" if video_details["NEXT_PAGE_TOKEN"] else ""),
            "Neutral : " + str(video_details["NEUTRAL_PERCENT"]) + "%\nCount : " + str(video_details["NEUTRAL_COUNT"])+("+" if video_details["NEXT_PAGE_TOKEN"] else "")]
    sizes = [video_details["POSITIVE_PERCENT"], video_details["NEGATIVE_PERCENT"], video_details["NEUTRAL_PERCENT"]]
    name = [str(video_details["POSITIVE_PERCENT"]) + "%", str(video_details["NEGATIVE_PERCENT"]) + "%", str(video_details["NEUTRAL_PERCENT"]) + "%"]
    colors = ["green", "red", "yellow"]
    patches, texts = plt.pie(sizes, colors=colors, startangle=90, labels=name)
    plt.legend(patches, labels, loc="best")
    plt.title("YouTube Video Comments Analysis Pie Chart")
    plt.axis("equal")
    plt.savefig("piechart.png")
    plt.close()


# Views
def index(request):
    return render(request,"index.html")

def report(request):
    url = request.POST["destination"]
    videoId=get_video_id(url)
    if(videoId==None):
        return render(request,"index.html")
    video_details=get_video_details(videoId)
    video_details=get_video_comments(video_details)
    video_details=make_video_report(video_details)
    write_to_csv(video_details)
    draw_piechart(video_details)
    request.session["VIDEO_DETAILS"]=video_details
    return render(request, "results.html", {"summary": video_details["SUMMARY"], "positive_str":video_details["POSITIVE_STR"],"negative_str":video_details["NEGATIVE_STR"],"neutral_str":video_details["NEUTRAL_STR"],"nextPageToken":video_details["NEXT_PAGE_TOKEN"],"total_comments_extracted":video_details["TOTAL_COMMENTS_EXTRACTED"]})

def more_comments(request):
    video_details=request.session["VIDEO_DETAILS"]
    video_details=get_more_comments(video_details)
    video_details=make_video_report(video_details)
    write_to_csv(video_details)
    draw_piechart(video_details)
    request.session["VIDEO_DETAILS"]=video_details
    return render(request, "results.html", {"summary": video_details["SUMMARY"], "positive_str":video_details["POSITIVE_STR"],"negative_str":video_details["NEGATIVE_STR"],"neutral_str":video_details["NEUTRAL_STR"],"nextPageToken":video_details["NEXT_PAGE_TOKEN"],"total_comments_extracted":video_details["TOTAL_COMMENTS_EXTRACTED"]})

def csv(request):
    csv_file = open("comments.csv", "rb")
    response = FileResponse(csv_file)
    return response

def pie_chart(request):
    pie_chart = open("piechart.png", "rb")
    response = FileResponse(pie_chart)
    return response