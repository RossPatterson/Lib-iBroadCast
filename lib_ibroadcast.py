"""
lib_ibroadcast
==============

A simple command line script with helper functions, developed for convenient creation of playlists

"""

from typing import Dict
from typing import List
from typing import Union
import hashlib
import logging
import logging.config
import requests
import json
from os import path


class ServerError(Exception):
    """
    Exception on an connection error
    """
    pass

def MatchWildCard(*,uValue:str,uMatchWithWildCard:str) -> bool:
    """
    The main function that checks if two given strings match.
    The uMatchWithWildCard string may contain wildcard characters (* and ? are supported)


    :return: True if the wildcard checks matches, otherwise False
    """

    # If we reach at the end of both strings, we are done
    if len(uMatchWithWildCard) == 0 and len(uValue) == 0:
        return True

    # Make sure that the characters after '*' are present
    # in uValue string. This function assumes that the uMatchWithWildCard
    # string will not contain two consecutive '*'
    if len(uMatchWithWildCard) > 1 and uMatchWithWildCard[0] == '*' and len(uValue) == 0:
        return False

    # If the uMatchWithWildCard string contains '?', or current characters
    # of both strings match
    if (len(uMatchWithWildCard) > 1 and uMatchWithWildCard[0] == '?') or (len(uMatchWithWildCard) != 0 and len(uValue) != 0 and uMatchWithWildCard[0] == uValue[0]):
        return MatchWildCard(uMatchWithWildCard=uMatchWithWildCard[1:], uValue=uValue[1:])

    # If there is *, then there are two possibilities
    # a) We consider current character of uValue string
    # b) We ignore current character of uValue string.
    if len(uMatchWithWildCard) != 0 and uMatchWithWildCard[0] == '*':
        return MatchWildCard(uMatchWithWildCard=uMatchWithWildCard[1:], uValue=uValue) or MatchWildCard(uMatchWithWildCard=uMatchWithWildCard, uValue=uValue[1:])

    return False




class ciBroadCast:
    """
    Main class, to access the iBroadCast API
    Just a smaller subset of the API is implemented


    Raises:
        ValueError on invalid login
        ServerError on connection issues
    """


    def __init__(self, bAllowUndocumentedAPIs:bool=False, iLogLevel:int=None):
        self._uVersion:str              = '1.0.0'
        self._uClient:str               = "lib_iBroadCast"
        self._uUserName:str             = ''
        self._uPassword:str             = ''
        self._uDeviceName:str           = 'lib_iBroadCast'
        self._dLibrary:Dict             = {}                # The complete user library
        self._aAlbums:List[str]         = []                # List of all SELECTED albums (add album function)
        self._aTracks:List[str]         = []                # List of all SELECTED songs (add songs function)
        self._aPlayListIndex:List       = []                # List of all playlists, index reference only
        self._dPlayListName:Dict        = {}                # dict of playlist,key is playlist name, value ist list of playlist values
        self._uUserId:str               = ''
        self._uToken:str                = ''
        self._uLogPrefix:str            = 'iBroadcast:'
        self._uUrl:str                  = "https://json.ibroadcast.com/s/JSON/status"
        self._dHeaders:Dict             = {'Content-Type': 'application/json'}
        self._dMap_Albums:Dict[str,int] = {}                # map of album library entry name to list indices
        self._iAlbums_IndexAlbumName:int = 0                # Index of album name in an album values list
        self._iAlbums_IndexTracks:int  = 0                  # Index of album tracks in an album values list
        self._dMap_PlayLists:Dict[str,int] = {}
        self._iPlayLists_IndexPlayListName:int = 0
        self._dMap_Tracks:Dict[str,int] = {}
        self._iTracks_IndexPath:int     = 0
        self._aMD5s:List[str]           = []                # All the MD5 checksums the server knows about.
        self._uUploadUrl:str            = "https://upload.ibroadcast.com"
        self._bAllowUndocumentedAPIs:bool = bAllowUndocumentedAPIs

        self.oLogger:logging           = logging.getLogger(__name__)
        self.InitLogger(iLogLevel)

    def InitLogger(self, iLogLevel:int=None) -> None:
        """
        Initializes the logger to set the log level and a console handler
        :return: None
        """

        logging.config.fileConfig(path.join(path.dirname(path.abspath(__file__)), 'logging.conf'), disable_existing_loggers=False)

        if iLogLevel:
            self.oLogger.setLevel(iLogLevel)

    def _LogError(self,*, uMsg:str) -> None:
        """
        Internal helper to log an error line
        :param str uMsg: The message to log
        :return: None
        """
        self.oLogger.error(f"{self._uLogPrefix}{uMsg}")

    def _LogInfo(self,*, uMsg:str) -> None:
        """
        Internal helper to log an info line
        :param str uMsg: The message to log
        :return: None
        """
        self.oLogger.info(f"{self._uLogPrefix}{uMsg}")

    def _LogDebug(self,*, uMsg:str) -> None:
        """
        Internal helper to log a debug line
        :param str uMsg: The message to log
        :return: None
        """
        self.oLogger.debug(f"{self._uLogPrefix}{uMsg}")

    def Login(self,*, uUserName:str, uPassword: str) -> bool:
        """
        Login to iBroadcast with the given username and password
        :param str uUserName: the iBroadcast username (email address)
        :param str uPassword: the iBroadcast password
        :return: True if successful
        """
        # Default to passed in values, but fallback to initial data.
        dRet:Dict
        self._uUserName = uUserName
        self._uPassword = uPassword

        self._LogDebug(uMsg='Logging in ....')

        # Build a request object.
        uReq:str = json.dumps({
                                'mode': 'status',
                                'email_address': self._uUserName,
                                'password': self._uPassword,
                                'version': self._uVersion,
                                'client': self._uClient,
                                'supported_types': 1,
                            })

        dRet = self._PostRequest(uCommand=uReq)

        if 'user' not in dRet:
            self._LogError(uMsg='Invalid login')
            raise ValueError('Invalid login')

        self._uUserId               = dRet['user']['id']
        self._uToken                = dRet['user']['token']
        self._LogDebug(uMsg='Login successful')
        return True

    def Logout(self) -> None:
        """
        Log outs from iBroadcast
        :return: None
        """
        self._LogDebug(uMsg='Logging out')
        if self._uUserId:
            self._PostCommand(uCommand='logout',dAddPar={})
        self._uUserId = ''
        self._uToken  = ''
        return None

    def GetLibrary(self) -> Dict:
        """
        Retrieves a user library from iBroadcast
        For a format description please refer to "https://devguide.ibroadcast.com/?p=library"
        :return: a dict of the library
        """
        self._LogDebug(uMsg='Getting user library')
        self._dLibrary = self._PostCommand(uCommand='library',dAddPar={})
        self._ReadPlayLists()
        return self._dLibrary

    def DeletePlayList(self,uName:str) -> bool:
        """
        Deletes a playlist

        :param str uName: The Name of the playlist
        :return: True is successfully
        """
        uIndex:str

        self._LogDebug(uMsg=f'Delete Playlist {uName}')

        if uName in self._dPlayListName:
            uIndex = self._dPlayListName[uName][-1]
            dRet = self._PostCommand(uCommand='deleteplaylist',dAddPar={"playlist_id": [uIndex]})
            return dRet.get('result',False)
        return False


    def CreatePlayList(self,uName:str, uDescription:str='', bPublic:bool=False) -> bool:
        """
        Creates a playlist from the currently selected songs (either albums or songs)
        If the playlist exists, it will be deleted

        :param str uName: The Name of the playlist
        :param uDescription: The description of the playlist
        :param bPublic: Flag, if the playlist should be public
        :return: True is successfully
        """

        aTracks:List=[]
        dRet:Dict
        uAlbumIndex:str
        # uSongIndex:str
        aAlbum:List
        dAlbums:Dict

        if uName in self._dPlayListName:
            self.DeletePlayList(uName=uName)

        self._LogDebug(uMsg=f'Create Playlist {uName}')

        dAlbums = self._dLibrary.get('library',{}).get('albums',{})

        for uAlbumIndex in self._aAlbums:
            aAlbum=dAlbums[uAlbumIndex]
            for uTrack in aAlbum[self._iAlbums_IndexTracks]:
                aTracks.append(uTrack)

        for uTrack in self._aTracks:
            aTracks.append(uTrack)

        dRet=self._PostCommand(uCommand='createplaylist',dAddPar={'name':uName,'description':uDescription,'tracks':aTracks,'make_public':bPublic})
        return dRet.get('result',False)


    def _ReadPlayLists(self) ->  int:
        """
        Internal function to read the playlists from a library
        :return: The number of playlists
        """

        dPlayLists:Dict[str]
        aAlbum:List
        iIndexPlayListName:int
        uPlayListIndex:str
        uPlayListName:str

        self._LogDebug(uMsg='Parsing existing playlists')

        if len(self._dLibrary)==0:
            self.GetLibrary()

        dPlayLists = self._dLibrary.get('library',{}).get('playlists',{})
        if len(dPlayLists)==0:
            return 0

        self._dMap_PlayLists = dPlayLists.get('map',{})
        self._iPlayLists_IndexPlayListName = self._dMap_PlayLists.get('name',0)

        for uPlayListIndex in dPlayLists:
            if uPlayListIndex!='map':
                uPlayListName = dPlayLists[uPlayListIndex][self._iPlayLists_IndexPlayListName]
                self._LogDebug(uMsg=f"Found playlist: {uPlayListName}")
                self._aPlayListIndex.append(uPlayListIndex)
                self._dPlayListName[uPlayListName] = dPlayLists[uPlayListIndex]
                self._dPlayListName[uPlayListName].append(uPlayListIndex)
        return len(self._aPlayListIndex)

    def SelectTracksByFolder(self, *, uFolder:str, bAppend=True) ->  int:
        """
        Selects songs from the users library, based on a given path
        :param str uFolder: The folder to use
        :param bool bAppend: If true, the current list of selected songs will be extended, otherwise a new list will be created
        :return: The number of selected songs
        """

        dTracks:Dict[str]
        uTrackPath:str

        self._LogDebug(uMsg=f"Select Tracks, Path: {uFolder}")

        if not bAppend:
            del self._aTracks[:]

        if len(self._dLibrary)==0:
            self.GetLibrary()

        dTracks = self._dLibrary.get('library',{}).get('tracks',{})
        if len(dTracks)==0:
            return 0

        self._dMap_Tracks = dTracks.get('map',{})
        self._iTracks_IndexPath = self._dMap_Albums.get('path',12)

        for uTrackIndex in dTracks:
            if uTrackIndex!='map':
                uTrackPath = dTracks[uTrackIndex][self._iTracks_IndexPath]
                if uTrackPath.startswith(uFolder):
                    if not uTrackIndex in self._aTracks:
                        self._aTracks.append(uTrackIndex)
        return len(self._aTracks)

    def SelectAlbumsByAlbumName(self, *, uFilter:str, bAppend=True) ->  int:
        """
        Selects albums from the users library, based on a given filter
        The filter supports wildcard matches (?/*)
        :param str uFilter: The wildcard filter to use
        :param bool bAppend: If true, the current list of selected albums will be extended, otherwise a new list will be created
        :return: The number of selected albums
        """

        dAlbums:Dict[str]
        uAlbumName:str
        uAlbumIndex:str

        self._LogDebug(uMsg=f"Select Albums, Filter: {uFilter}")

        if not bAppend:
            del self._aAlbums[:]

        if len(self._dLibrary)==0:
            self.GetLibrary()

        dAlbums = self._dLibrary.get('library',{}).get('albums',{})
        if len(dAlbums)==0:
            return 0

        self._dMap_Albums = dAlbums.get('map',{})
        self._iAlbums_IndexAlbumName = self._dMap_Albums.get('name',0)
        self._iAlbums_IndexTracks = self._dMap_Albums.get('tracks',1)

        for uAlbumIndex in dAlbums:
            if uAlbumIndex!='map':
                uAlbumName = dAlbums[uAlbumIndex][self._iAlbums_IndexAlbumName]
                if MatchWildCard(uValue=uAlbumName,uMatchWithWildCard=uFilter):
                    self._LogDebug(uMsg=f"Selected Album: {uAlbumName}")
                    if not uAlbumIndex in self._aAlbums:
                        self._aAlbums.append(uAlbumIndex)
        return len(self._aAlbums)

    def _PostCommand(self,*,uCommand:str, dAddPar:Dict) -> Dict:
        """
        Post a simple iBroadcast API command
        :param str uCommand: The command to post
        :param dict dAddPar: Additional parameters
        :return: A result dictionary
        """

        dCmd:Dict
        uCmd:str

        dCmd = {
                'mode': uCommand,
                'user_id': self._uUserId,
                'token': self._uToken,
                'device_name':self._uDeviceName,
                'version':self._uVersion,
                'client':self._uClient
               }

        dCmd.update(dAddPar)
        uCmd = json.dumps(dCmd)
        return self._PostRequest(uCommand=uCmd)


    def _PostRequest(self, uCommand:str) -> Dict:
        """
        Post a fully prepared iBroadcast API request to the standard URL
        :param str uCommand: The command string to post
        :return: A result dictionary
        """

        return self._Post(self._uUrl, uData=uCommand, dHeaders=self._dHeaders).json()

    def _Post(self, uUrl:str, uData:str='', dHeaders:dict={}, dFiles:dict=None): # -> Response:
        """
        Post a fully prepared iBroadcast API string
        :param str uUrl: The URL to post to
        :param str uCommand: The data string to post
        :param dict dHeaders: The request headers to post
        :param dict dFiles: Open file(s) to post
        :return: A response object
        """

        oResponse:Response
        uMsg:str

        try:
            oResponse = requests.post(uUrl, data=uData, headers=dHeaders, files=dFiles)
            if not oResponse.ok:
                uMsg = f'Server returned bad status on command {uData} : Status code: {oResponse.status_code}'
                self._LogError(uMsg=uMsg)
                raise ServerError(uMsg)
            return oResponse
        except Exception:
            raise ServerError('Server connection error')

    def GetMD5s(self) -> List[str]:
        """
        Retrieves the MD5 checksums from
        a user library from iBroadcast

        *** THIS API IS UNDOCUMENTED! USE AT YOUR OWN RISK! ***
        :return: an array of the library's MD5 checksums
        """
        # This API was discovered in the ibroadcast-uploader.py sample.
        if not self._bAllowUndocumentedAPIs:
            raise ServerError("Undocumented APIs have not been enabled.")

        oResponse:Response
        uData:str=f'user_id={self._uUserId}&token={self._uToken}'
        dHeaders:dict={'Content-Type': 'application/x-www-form-urlencoded'}

        self._LogDebug(uMsg='Getting user MD5 checksums')
        oResponse = self._Post(self._uUploadUrl, uData=uData, dHeaders=dHeaders)
        dResult:Dict = oResponse.json()
        if 'md5' not in dResult:
            raise ServerError('Server returned a response we do not understand.')
        self._aMD5s = dResult['md5']
        self._LogDebug(uMsg=f"Loaded {len(self._aMD5s)} checksums")
        return self._aMD5s

    def GetSupportedFiletypes(self) -> List[str]:
        """
        Retrieves the list of supported media filetypes from iBroadcast

        *** THIS API IS UNDOCUMENTED! USE AT YOUR OWN RISK! ***
        :return: an array of the library's MD5 checksums
        """
        # This API was discovered in the ibroadcast-uploader.py sample.
        if not self._bAllowUndocumentedAPIs:
            raise ServerError("Undocumented APIs have not been enabled.")

        aExtensions:List[str] = []
        dRet:Dict
        uFiletype:str

        self._LogDebug(uMsg='Getting supported filetypes')
        dRet = self._PostCommand(uCommand='status', dAddPar={'supported_types': 1,})
        if 'supported' not in dRet:
            raise ServerError('Server returned a response we do not understand.')
        for uFiletype in dRet['supported']:
            aExtensions.append(uFiletype['extension'])
        return aExtensions

    def UploadTrack(self, uFilepath:str, bForce:bool=False) -> bool:
        """
        Uploads a track file to the user library in iBroadcast

        *** THIS API IS UNDOCUMENTED! USE AT YOUR OWN RISK! ***
        :param str uFilepath: The file to upload.
        :param bool bForce: True if the file should be uploaded even if it is already present.
        :return: True if successful, False otherwise
        """
        # This API was discovered in the ibroadcast-uploader.py sample.
        if not self._bAllowUndocumentedAPIs:
            raise ServerError("Undocumented APIs have not been enabled.")

        oResponse:Response
        uData:str
        uTrackMD5:str = ""
        oUploadFile:File

        self._LogDebug(uMsg='Uploading file')
        if not bForce:
            if not self._aMD5s:
                self.GetMD5s()
            # Get an md5 of the file contents and compare it to what's up
            # there already
            uTrackMD5 = self._CalcMD5(uFilepath)
            if uTrackMD5 in self._aMD5s:
                self._LogInfo(uMsg=f'File {uFilepath} has already been uploaded, skipping.')
                return True    # Arguable if this is a "successful" upload or not :-(

        uData = {
            'user_id': self._uUserId,
            'token': self._uToken,
            'file_path': uFilepath,
            'method': self._uClient
        }
        with open(uFilepath, 'rb') as oUploadFile:
            oResponse = self._Post(self._uUploadUrl, uData=uData, dFiles={'file': oUploadFile})
            result:bool = oResponse.json().get('result',False)
            if result:
                self._aMD5s.append(uTrackMD5)
            return result

    def _CalcMD5(self, uFilepath:str) -> str:
        oFile:File
        oHash:Hash
        uChunk:str
        with open(uFilepath, 'rb') as oFile:
            oHash = hashlib.md5()
            uChunk = oFile.read(8192)
            while uChunk:
                oHash.update(uChunk)
                uChunk = oFile.read(8192)
        return oHash.hexdigest()
