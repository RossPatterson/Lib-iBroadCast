import argparse
import getpass
import glob
from lib_ibroadcast import ciBroadCast
import logging
import os

logger = logging.getLogger('iBroadcast_CLI')

def setup_subcommands():
    def add_common_args(parser):
        parser.add_argument("-d", "--dryrun", action="store_true", default=False, help="do not actually make changes")
        parser.add_argument("-p", "--password", help="password for iBroadcast account")
        parser.add_argument("-u", "--username", required=True, help="username for iBroadcast account")
        parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose logging")

    parser = argparse.ArgumentParser(description="iBroadcast CLI")
    parser.add_argument("-V", "--version", action="version", version = f"{parser.prog} version 1.0.0")
    parser.set_defaults(verbose=False)

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

    parser_uf = subparsers.add_parser("upload_folder", aliases=["uf"])
    parser_uf.set_defaults(operation_func = upload_folder)
    add_common_args(parser_uf)
    parser_uf.add_argument("-f", "--folder", required=True, help="Folder to upload from")
    parser_uf.add_argument("-F", "--force", action="store_true", default=False, help="Upload even if previously uploaded")
    parser_uf.add_argument("-r", "--recursive", action="store_true", default=False, help="Upload folder recursively")

    return parser

def create_playlist(args):
    if not args.dryrun:
        ibroadcast_api.CreatePlayList(uName=args.name, uDescription=args.description, bPublic=args.public)

def select_albums_by_albumname(args):
    if not args.dryrun:
        ibroadcast_api.SelectAlbumsByAlbumName(uFilter=args.filter)

def select_tracks_by_folder(args):
    if not args.dryrun:
        ibroadcast_api.SelectTracksByFolder(uFolder=args.folder)

def upload_folder(args):
    def list_files(folder, supported_filetypes, recursive, verbose):
        """
        Enumerate all files in the folder that match the supported extension list, possbly recursing
        into subfolders, and ignoring "hidden" files (".whatever").
        """
        files = []
        for filename in glob.glob(os.path.join(folder, '*')):
            basename = os.path.basename(filename)
            if basename.startswith('.'):
                if verbose:
                    logger.debug(f"Skipping {filename} - 'hidden' file")
                continue
            if os.path.isdir(filename):
                if recursive:
                    if verbose:
                        logger.debug(f"Recursing into {filename}")
                    files += list_files(filename, supported_filetypes, recursive, verbose)
                continue
            dummy, ext = os.path.splitext(basename)
            if ext not in supported_filetypes:
                if verbose:
                    logger.debug(f"Skipping {filename} - not a supported filetype")
                continue
            files.append(filename)
        return files
    if args.verbose:
        logger.debug(f"Uploading tracks from {args.folder}{' recursively' if args.recursive else ''}")
    supported_filetypes = ibroadcast_api.GetSupportedFiletypes()
    folder_files = list_files(args.folder, supported_filetypes, args.recursive, args.verbose)
    for filename in folder_files:
        if args.verbose:
            logger.debug(f"Uploading {filename}")
        if not args.dryrun:
            success = ibroadcast_api.UploadTrack(filename, bForce=args.force)
            if not success:
                logger.info(f"Upload of {filename} failed.")

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
    if args.dryrun:
        logger.info("Changes are suppressed by --dryrun")
    ibroadcast_api = ciBroadCast(bAllowUndocumentedAPIs=True, iLogLevel=log_level)
    ibroadcast_api.Login(uUserName=args.username, uPassword=args.password)
    args.operation_func(args)
    ibroadcast_api.Logout()

