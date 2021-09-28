import argparse
import getpass
from lib_ibroadcast import ciBroadCast
import logging
import os

logger = logging.getLogger('iBroadcast_CLI')

def setup_subcommands():
    def add_common_args(parser):
        parser.add_argument("-p", "--password", help="password for iBroadcast account")
        parser.add_argument("-u", "--username", required=True, help="username for iBroadcast account")
        parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose logging")

    parser = argparse.ArgumentParser(description="iBroadcast CLI")
    parser.add_argument("-V", "--version", action="version", version = f"{parser.prog} version 1.0.0")

    subparsers = parser.add_subparsers(dest="operation")
    subparsers.add_parser("help")

    parser_cp = subparsers.add_parser("create_playlist", aliases=["cp"])
    parser_cp.set_defaults(operation_func = create_playlist)
    add_common_args(parser_cp)
    parser_cp.add_argument("-D", "--description", required=True, help="Playlist description")
    parser_cp.add_argument("-f", "--folder", required=True, help="Folder to create playlist from")
    parser_cp.add_argument("-n", "--name", required=True, help="Playlist name")
    parser_cp.add_argument("--public", dest="public", action="store_true", help="Create a public playlist")
    parser_cp.add_argument("--private", dest="public", action="store_false", default=False, help="Create a private playlist (default)")

    parser_sa = subparsers.add_parser("select_album", aliases=["sa"])
    parser_sa.set_defaults(operation_func = select_albums_by_albumname)
    add_common_args(parser_sa)
    parser_sa.add_argument("-F", "--filter", required=True, help="Filter to apply")

    parser_sf = subparsers.add_parser("select_folder", aliases=["sf"])
    parser_sf.set_defaults(operation_func = select_tracks_by_folder)
    add_common_args(parser_sf)
    parser_sf.add_argument("-f", "--folder", required=True, help="Folder to select from")

    return parser

def create_playlist(args):
    ibroadcast_api.CreatePlayList(uName=args.name, uDescription=args.description, bPublic=args.public)

def select_albums_by_albumname(args):
    ibroadcast_api.SelectAlbumsByAlbumName(uFilter=args.filter)

def select_tracks_by_folder(args):
    ibroadcast_api.SelectTracksByFolder(uFolder=args.folder)

if __name__ == '__main__':
    log_level = logging.INFO
    logger.setLevel(log_level)
    logger.addHandler(logging.StreamHandler())

    parser = setup_subcommands()
    args = parser.parse_args()
    if args.verbose:
        log_level = logging.DEBUG
        logger.setLevel(log_level)
    if args.operation == "help":
        parser.print_help()
        exit(0)
    if args.password is None:
        args.password = getpass.getpass(f"Enter password for {args.username}: ")
    ibroadcast_api = ciBroadCast(bAllowUndocumentedAPIs=True, iLogLevel=log_level)
    ibroadcast_api.Login(uUserName=args.username, uPassword=args.password)
    args.operation_func(args)
    ibroadcast_api.Logout()

