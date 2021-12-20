import argparse
import getpass
import glob
from lib_ibroadcast import ciBroadCast
import logging
import logging.config
import os
from os import path
from typing import Dict
from typing import List

logging.config.fileConfig(path.join(path.dirname(path.abspath(__file__)), 'logging.conf'))
logger:logging.Logger = logging.getLogger(__name__)

def setup_subcommands() -> argparse.ArgumentParser:
    """
    Set up the argument parser and the handlers for each subcommand.
    """
    def add_common_args(parser:argparse.ArgumentParser) -> None:
        """
        Add all the arguments to a the parser that every parser should have.
        """
        parser.add_argument("-d", "--dryrun", action="store_true", default=False, help="do not actually make changes")
        parser.add_argument("-p", "--password", help="password for iBroadcast account")
        parser.add_argument("-u", "--username", required=True, help="username for iBroadcast account")
        parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose logging")

    parser:argparse.ArgumentParser = argparse.ArgumentParser(description="iBroadcast CLI")
    parser.add_argument("-V", "--version", action="version", version = f"{parser.prog} version 1.0.0")
    parser.set_defaults(verbose=False)

    subparsers:argparse.ArgumentParser = parser.add_subparsers(dest="operation")
    subparsers.add_parser("help")

    parser_cp:argparse.ArgumentParser = subparsers.add_parser("create_playlist", aliases=["cp"])
    parser_cp.set_defaults(operation_func = create_playlist)
    add_common_args(parser_cp)
    parser_cp.add_argument("-D", "--description", required=True, help="Playlist description")
    parser_cp.add_argument("-f", "--folder", required=True, help="Folder to create playlist from")
    parser_cp.add_argument("-n", "--name", required=True, help="Playlist name")
    parser_cp.add_argument("--public", dest="public", action="store_true", help="Create a public playlist")
    parser_cp.add_argument("--private", dest="public", action="store_false", default=False, help="Create a private playlist (default)")

    parser_sa:argparse.ArgumentParser = subparsers.add_parser("select_album", aliases=["sa"])
    parser_sa.set_defaults(operation_func = select_albums_by_albumname)
    add_common_args(parser_sa)
    parser_sa.add_argument("-F", "--filter", required=True, help="Filter to apply")

    parser_sf:argparse.ArgumentParser = subparsers.add_parser("select_folder", aliases=["sf"])
    parser_sf.set_defaults(operation_func = select_tracks_by_folder)
    add_common_args(parser_sf)
    parser_sf.add_argument("-f", "--folder", required=True, help="Folder to select from")

    parser_uf:argparse.ArgumentParser = subparsers.add_parser("upload_folder", aliases=["uf"])
    parser_uf.set_defaults(operation_func = upload_folder)
    add_common_args(parser_uf)
    parser_uf.add_argument("-f", "--folder", required=True, help="Folder to upload from")
    parser_uf.add_argument("-F", "--force", action="store_true", default=False, help="Upload even if previously uploaded")
    parser_uf.add_argument("-r", "--recursive", action="store_true", default=False, help="Upload folder recursively")

    parser_ut:argparse.ArgumentParser = subparsers.add_parser("upload_track", aliases=["uf"])
    parser_ut.set_defaults(operation_func = upload_track)
    add_common_args(parser_ut)
    parser_ut.add_argument("-t", "--track", required=True, help="Track to upload")
    parser_ut.add_argument("-F", "--force", action="store_true", default=False, help="Upload even if previously uploaded")

    return parser

def create_playlist(args:argparse.Namespace) -> None:
    if not args.dryrun:
        ibroadcast_api.CreatePlayList(uName=args.name, uDescription=args.description, bPublic=args.public)

def select_albums_by_albumname(args:argparse.Namespace) -> None:
    if not args.dryrun:
        ibroadcast_api.SelectAlbumsByAlbumName(uFilter=args.filter)

def select_tracks_by_folder(args:argparse.Namespace) -> None:
    if not args.dryrun:
        ibroadcast_api.SelectTracksByFolder(uFolder=args.folder)

def upload_folder(args:argparse.Namespace) -> None:
    """
    Update all the songs in a folder.
    """
    def list_files(folder:str, supported_filetypes:List[str], recursive:bool) -> List[str]:
        """
        Enumerate all files in the folder that match the supported extension list, possbly recursing
        into subfolders, and ignoring "hidden" files (".whatever").
        """
        ext:str
        files:str = []
        filename:str
        for filename in glob.glob(os.path.join(folder, '*')):
            basename:str = os.path.basename(filename)
            if basename.startswith('.'):
                if verbose:
                    logger.debug(f"Skipping {filename} - 'hidden' file")
                continue
            if os.path.isdir(filename):
                if recursive:
                    logger.debug(f"Recursing into {filename}")
                    files += list_files(filename, supported_filetypes, recursive)
                continue
            _, ext = os.path.splitext(basename)
            if ext not in supported_filetypes:
                logger.error(f"Skipping {filename} - not a supported filetype")
                continue
            files.append(filename)
        return files
    filename:str
    logger.debug(f"Uploading tracks from {args.folder}{' recursively' if args.recursive else ''}")
    supported_filetypes:Dict = ibroadcast_api.GetSupportedFiletypes()
    folder_files:List[str] = list_files(args.folder, supported_filetypes, args.recursive)
    for filename in folder_files:
        logger.debug(f"Processing {filename}")
        if args.dryrun:
            logger.info(f"Skipping {filename} - dry run mode")
            continue
        success:bool = ibroadcast_api.UploadTrack(filename, bForce=args.force)
        if success:
            logger.info(f"Upload of {filename} succeeded.")
        else:
            logger.error(f"Upload of {filename} failed.")

def upload_track(args:argparse.Namespace) -> None:
    """
    Update a single song.
    """
    ext:str
    filename:str = args.track
    logger.debug(f"Uploading track {filename}")
    supported_filetypes:Dict = ibroadcast_api.GetSupportedFiletypes()
    _, ext = os.path.splitext(os.path.basename(filename))
    if ext not in supported_filetypes:
        logger.error(f"Skipping {filename} - not a supported filetype")
        return
    if args.dryrun:
        logger.info(f"Skipping {filename} - dry run mode")
        return
    success:bool = ibroadcast_api.UploadTrack(filename, bForce=args.force)
    if success:
        logger.info(f"Upload of {filename} succeeded.")
    else:
        logger.error(f"Upload of {filename} failed.")

if __name__ == '__main__':
    log_level:int = logging.INFO

    parser:argparse.ArgumentParser = setup_subcommands()
    args:argparse.Namespace = parser.parse_args()
    if args.verbose:
        log_level = logging.DEBUG
        logger.setLevel(log_level)
    if args.operation == "help":
        parser.print_help()
        exit(0)
    if args.password is None:
        args.password = getpass.getpass(f"Enter password for {args.username}: ")
    if args.dryrun:
        logger.info("Changes are suppressed by --dryrun")
    ibroadcast_api:ciBroadCast = ciBroadCast(bAllowUndocumentedAPIs=True, iLogLevel=log_level)
    ibroadcast_api.Login(uUserName=args.username, uPassword=args.password)
    args.operation_func(args)
    ibroadcast_api.Logout()
