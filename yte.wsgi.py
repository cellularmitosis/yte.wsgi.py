#!/usr/bin/env python3

# A WSGI-compliant REST API wrapper around YoutubeExplodeSync.
# See https://github.com/cellularmitosis/yte.wsgi.py

# Copyright 2023 Jason Pepas.
# Released under the terms of the MIT license.
# See https://opensource.org/license/mit/

# See https://pythonnet.github.io/pythonnet/python.html
# See https://github.com/Tyrrrz/YoutubeExplode
# See https://github.com/cellularmitosis/YoutubeExplodeSync
# See https://peps.python.org/pep-333/
# See https://peps.python.org/pep-3333/

import os
import sys
import urllib.parse
import json
import plistlib

import pythonnet
pythonnet.load("coreclr")
import clr

clr.AddReference("AngleSharp")
clr.AddReference("YoutubeExplode")
import YoutubeExplode

yt = YoutubeExplode.YoutubeClient()

#
# Utility functions
#

def is_GET(request):
    return request["REQUEST_METHOD"].upper() == "GET"

def is_POST(request):
    return request["REQUEST_METHOD"].upper() == "POST"

status_codes = {
    200: "200 OK",
    400: "400 Bad Request",
    404: "404 Not Found",
}

def make_text_plain_response(status_code, body):
    d = {}
    d["body"] = body
    d["status"] = status_codes[status_code]
    d["headers"] = [
        ("Content-Type", "text/plain; charset=UTF-8"),
        ("Content-Length", str(len(d["body"])))
    ]
    return d

def make_200_ok_text_plain_response(body="200 OK\n"):
    return make_text_plain_response(200, body)

def make_400_bad_request_text_plain_response(body="400 Bad Request\n"):
    return make_text_plain_response(400, body)

def make_404_not_found_text_plain_response(body="404 Not Found\n"):
    return make_text_plain_response(404, body)

def format_dict_as_json(body, pretty=False):
    if pretty:
        return json.dumps(body, sort_keys=True, indent=4) + "\n"
    else:
        return json.dumps(body, sort_keys=True) + "\n"

def format_dict_as_xml_plist(body):
    return plistlib.dumps(body, fmt=plistlib.FMT_XML)

def format_dict_as_binary_plist(body):
    return plistlib.dumps(body, fmt=plistlib.FMT_BINARY)

def format_dict(body, request):
    format = request.get("HTTP_ACCEPT", "*/*").lower()
    # Note: there is no standard Content-Type for plists.
    # See http://www.iana.org/assignments/media-types/media-types.xhtml
    if format == "application/x-plist":
        return (format, format_dict_as_xml_plist(body))
    elif format == "application/x-plist.binary":
        return (format, format_dict_as_binary_plist(body))
    elif format == "application/json":
        return ("application/json", format_dict_as_json(body))
    else:
        return ("application/json", format_dict_as_json(body, pretty=True))

def make_response_from_dict(status_code, body, request):
    d = {}
    (response_format, formatted_body) = format_dict(body, request)
    d["body"] = formatted_body
    d["status"] = status_codes[status_code]
    d["headers"] = [
        ("Content-Type", response_format),
        ("Content-Length", str(len(d["body"])))
    ]
    return d

def parse_POST_params(request):
    # Thanks to https://wsgi.tutorial.codepoint.net/parsing-the-request-post
    # See also https://stackoverflow.com/q/22894078
    try:
        length = int(request.get("CONTENT_LENGTH", 0))
    except (ValueError):
        length = 0
    request_body = request["wsgi.input"].read(length)
    # print("request_body: %s" % request_body)
    qs = urllib.parse.parse_qs(request_body.decode())
    # Note: parse_qs will return an array for each item, because the user might
    # have set a value more than once in the query string.  We'll go with the
    # last value of each array.
    qs2 = {}
    for k, v in qs.items():
        qs2[k] = v[-1]
    return qs2

def parse_GET_query(request):
    # Thanks to https://wsgi.tutorial.codepoint.net/parsing-the-request-get
    qs = urllib.parse.parse_qs(request.get("QUERY_STRING", ""))
    # Note: parse_qs will return an array for each item, because the user might
    # have set a value more than once in the query string.  We'll go with the
    # last value of each array.
    qs2 = {}
    for k, v in qs.items():
        qs2[k] = v[-1]
    return qs2

def route(request):
    return routes.get(request["PATH_INFO"], None)

def application(request, start_response_fn):
    handler = route(request)
    if handler is None:
        response = make_404_not_found_text_plain_response()
    else:
        response = handler(request)
    start_response_fn(response["status"], response["headers"])
    if type(response["body"]) is str:
        response["body"] = response["body"].encode()
    return [response["body"]]

#
# YoutubeExplodeSync serialization layer
#

def Thumbnail_to_dict(th):
    return {
        "__typename": str(th.GetType()),
        "Url": th.Url,
        "Resolution": str(th.Resolution),
    }

def Author_to_dict(a):
    return {
        "__typename": str(a.GetType()),
        "ChannelId": str(a.ChannelId),
        "ChannelUrl": a.ChannelUrl,
        "ChannelTitle": a.ChannelTitle,
    }

def Engagement_to_dict(e):
    return {
        "__typename": str(e.GetType()),
        "ViewCount": e.ViewCount,
        "LikeCount": e.LikeCount,
        "DislikeCount": e.DislikeCount,
    }

def Video_to_dict(v):
    return {
        "__typename": str(v.GetType()),
        "Id": str(v.Id),
        "Url": v.Url,
        "Title": v.Title,
        "Author": Author_to_dict(v.Author),
        "UploadDate": str(v.UploadDate),
        "Description": v.Description,
        "Thumbnails": list(map(Thumbnail_to_dict, v.Thumbnails)),
        "Keywords": list(v.Keywords),
        "Engagement": Engagement_to_dict(v.Engagement),
    }

def Channel_to_dict(ch):
    return {
        "__typename": str(ch.GetType()),
        "Id": str(ch.Id),
        "Url": ch.Url,
        "Title": ch.Title,
        "Thumbnails": list(map(Thumbnail_to_dict, ch.Thumbnails)),
    }

def VideoSearchResult_to_dict(vsr):
    return {
        "__typename": str(vsr.GetType()),
        "Id": str(vsr.Id),
        "Url": vsr.Url,
        "Title": vsr.Title,
        "Author": Author_to_dict(vsr.Author),
        "Duration": str(vsr.Duration),
        "Thumbnails": list(map(Thumbnail_to_dict, vsr.Thumbnails))
    }

def ChannelSearchResult_to_dict(csr):
    return {
        "__typename": str(csr.GetType()),
        "Id": str(csr.Id),
        "Url": csr.Url,
        "Title": csr.Title,
        "Thumbnails": list(map(Thumbnail_to_dict, csr.Thumbnails))
    }

def PlaylistSearchResult_to_dict(psr):
    return {
        "__typename": str(psr.GetType()),
        "Id": str(psr.Id),
        "Url": psr.Url,
        "Title": psr.Title,
        "Author": Author_to_dict(psr.Author),
        "Thumbnails": list(map(Thumbnail_to_dict, psr.Thumbnails))
    }

def ISearchResult_to_dict(isr):
    vsr = isr.asVideoSearchResult()
    if vsr is not None:
        return VideoSearchResult_to_dict(vsr)
    csr = isr.asChannelSearchResult()
    if csr is not None:
        return ChannelSearchResult_to_dict(csr)
    psr = isr.asPlaylistSearchResult()
    if psr is not None:
        return PlaylistSearchResult_to_dict(psr)
    raise Exception("Malformed ISearchResult: %s" % isr)

def PagedSearchResults_to_dict(psr):
    d = {
        "__typename": str(psr.GetType()),
        "ContinuationToken": psr.ContinuationToken,
        "Results": []
    }
    for r in psr.Results:
        d["Results"].append(ISearchResult_to_dict(r))
    return d

#
# Endpoints
#

routes = {}

def root_endpoint(request):
    d = {}
    d["status"] = "200 OK"
    d["body"] = """Usage:

Search for "iMac":
curl -X POST -d "q=iMac" http://localhost:8000/search

Search for "El Niño" (spaces replaced with '+', unicode percent-escaped):
curl -X POST -d "q=El+Ni%C3%B1o" http://localhost:8000/search

Return minified JSON:
curl -X POST -H "Accept: application/json" -d "q=iMac" http://localhost:8000/search

Return an Apple Property List (.plist), XML format:
curl -X POST -H "Accept: application/x-plist" -d "q=iMac" http://localhost:8000/search

Return an Apple Property List (.plist), binary format:
curl -X POST -H "Accept: application/x-plist.binary" -d "q=iMac" http://localhost:8000/search

To get the next page, include the continuationToken from the previous search:
curl -X POST -d "q=iMac&continuationToken=..." http://localhost:8000/search

Search only for videos:
curl -X POST -d "q=iMac" http://localhost:8000/search/videos

Search only for channels:
curl -X POST -d "q=iMac" http://localhost:8000/search/channels

Search only for playlists:
curl -X POST -d "q=iMac" http://localhost:8000/search/playlists

Get the details of a video:
curl -X GET http://localhost:8000/video?id=dQw4w9WgXcQ

Get the details of a channel:
curl -X GET http://localhost:8000/channel?id=UCuAXFkgsw1L7xaCfnd5JJOw
curl -X GET http://localhost:8000/channel?handle=RickAstleyYT
curl -X GET http://localhost:8000/channel?slug=BlenderFoundation
curl -X GET http://localhost:8000/channel?user=65scribe

List the video uploads of a channel:
curl -X GET http://localhost:8000/channel/uploads?id=UCuAXFkgsw1L7xaCfnd5JJOw

"""
    d["headers"] = [
        ("Content-Type", "text/plain; charset=UTF-8"),
        ("Content-Length", str(len(d["body"])))
    ]
    return d
routes["/"] = root_endpoint

# Unicode test: search for "El Niño":
#   curl -d "q=El+Ni%C3%B1o" http://localhost:8000/search
def search_endpoint(request):
    if not is_POST(request):
        return make_400_bad_request_text_plain_response()
    params = parse_POST_params(request)
    if "q" not in params:
        return make_400_bad_request_text_plain_response("400 Bad Request: missing 'q' parameter.\n")
    search_query = urllib.parse.unquote_plus(params["q"], encoding="utf-8")
    continuationToken = params.get("continuationToken", None)
    # print("search_query: \"%s\"" % search_query)
    if request["PATH_INFO"] == "/search":
        psr = yt.Search.GetResults(search_query, continuationToken)
    elif request["PATH_INFO"] == "/search/videos":
        psr = yt.Search.GetVideos(search_query, continuationToken)
    elif request["PATH_INFO"] == "/search/channels":
        psr = yt.Search.GetChannels(search_query, continuationToken)
    elif request["PATH_INFO"] == "/search/playlists":
        psr = yt.Search.GetPlaylists(search_query, continuationToken)
    body = PagedSearchResults_to_dict(psr)
    response = make_response_from_dict(200, body, request)
    return response
routes["/search"] = search_endpoint
routes["/search/videos"] = search_endpoint
routes["/search/channels"] = search_endpoint
routes["/search/playlists"] = search_endpoint

def video_endpoint(request):
    params = parse_GET_query(request)
    if "id" not in params:
        return make_400_bad_request_text_plain_response("400 Bad Request: missing 'id' query parameter.\n")
    v_id_str = urllib.parse.unquote_plus(params["id"], encoding="utf-8")
    v_id = YoutubeExplode.Videos.VideoId(v_id_str)
    v = yt.Videos.Get(v_id)
    body = Video_to_dict(v)
    response = make_response_from_dict(200, body, request)
    return response
routes["/video"] = video_endpoint

def channel_endpoint(request):
    params = parse_GET_query(request)
    if "id" in params:
        ch_id_str = urllib.parse.unquote_plus(params["id"], encoding="utf-8")
        ch_id = YoutubeExplode.Channels.ChannelId(ch_id_str)
        ch = yt.Channels.Get(ch_id)
    elif "handle" in params:
        h_str = urllib.parse.unquote_plus(params["handle"], encoding="utf-8")
        h = YoutubeExplode.Channels.ChannelHandle(h_str)
        ch = yt.Channels.GetByHandle(h)
    elif "user" in params:
        u_str = urllib.parse.unquote_plus(params["user"], encoding="utf-8")
        u = YoutubeExplode.Channels.UserName(u_str)
        ch = yt.Channels.GetByUser(u)
    elif "slug" in params:
        s_str = urllib.parse.unquote_plus(params["slug"], encoding="utf-8")
        s = YoutubeExplode.Channels.ChannelSlug(s_str)
        ch = yt.Channels.GetBySlug(s)
    else:
        return make_400_bad_request_text_plain_response()
    body = Channel_to_dict(ch)
    response = make_response_from_dict(200, body, request)
    return response
routes["/channel"] = channel_endpoint

# def channel_uploads_endpoint(request):
#     params = parse_GET_query(request)
#     if "id" in params:
#         ch_id_str = urllib.parse.unquote_plus(params["id"], encoding="utf-8")
#         ch_id = YoutubeExplode.Channels.ChannelId(ch_id_str)
#         u = yt.Channels.GetUploads(ch_id)
#     else:
#         return make_400_bad_request_text_plain_response()
#     body = list(map(PlaylistVideo_to_dict, u))
#     response = make_response_from_dict(200, body, request)
#     return response
# routes["/channel/uploads"] = channel_uploads_endpoint

if __name__ == "__main__":
    from wsgiref.simple_server import make_server
    print("listening on port 8000")
    httpd = make_server("", 8000, application)
    httpd.serve_forever()
