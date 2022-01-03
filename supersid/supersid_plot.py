#!/usr/bin/env python3
"""
Plot SuperSID data files.

supersid_plot
version: 1.3.1 enhanced for Python 3
Original Copyright: Stanford Solar Center - 2008
Copyright: Eric Gibert - 2012


Support one to many files as input, even in Drag & Drop
Draw multi-stations graphs
Offer the possibility to generate PDF and email it (perfect for batch mode)
Offer the possibility to fetch NOAA XRA data and add them on the plot
"""
import sys
import datetime
import time
import itertools
import os.path
import glob
# matplolib tools
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter as ff
import matplotlib.dates
# Internet and Email modules
import mimetypes
import smtplib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders, utils
import argparse
# SuperSID modules
from sidfile import SidFile
from config import readConfig, printConfig, CONFIG_FILE_NAME
from supersid_common import exist_file

try:
    clock = time.process_time   # new in Python 3.3
except Exception:
    clock = time.clock          # removed in Python 3.8


PAPER_SIZE = {
    'A3': (29.7 / 2.54, 42.0 / 2.54),
    'A4': (21.0 / 2.54, 29.7 / 2.54),
    'A5': (14.8 / 2.54, 21.0 / 2.54),
    'LEGAL': (8.5, 14),
    'LETTER': (8.5, 11)
}


def sendMail(config, To_mail, msgBody, PDFfile):
    """Send the mail using the smtplib module.

    The plot (as PDF) attached
    """
    senderEmail = config.get("from_mail", "")
    mailserver = config.get("email_server", "")
    mailport = config.get("email_port", "")

    # set mailserveruser to None if no login required
    mailserveruser = config.get("email_login", "")

    # set mailserverpasswd to None if no login required
    mailserverpasswd = config.get("email_password", "")

    # create the mail message
    msg = MIMEMultipart(_subtype='html')
    msg['Subject'] = 'Auto-generated eMail from SuperSID'
    msg.attach(MIMEText(msgBody))

    # Following headers are useful to show the email correctly
    msg['From'] = senderEmail
    msg['Reply-to'] = senderEmail
    msg['To'] = To_mail
    msg['Date'] = utils.formatdate(localtime=1)

    # attach the PDF file
    ctype, encoding = mimetypes.guess_type(PDFfile)
    if ctype is None:
        ctype = 'application/octet-stream'
        print(
            "MIME type for '{}' is unknown. Falling back to '{}'"
            .format(PDFfile, ctype))
    maintype, subtype = ctype.split('/', 1)
    with open(PDFfile, 'rb') as pdf:
        att = MIMEBase(maintype, subtype)
        att.set_payload(pdf.read())
        encoders.encode_base64(att)
        att.add_header('Content-Disposition', 'attachment', filename=PDFfile)
        msg.attach(att)

    # Establish an SMTP object by connecting to your mail server
    s = smtplib.SMTP(mailserver, mailport)
    print("Connect to:", mailserver, mailport)
    s.connect(mailserver, port=mailport)
    if 'YES' == config.get("email_tls", ""):
        s.starttls()
    if mailserveruser:
        s.login(mailserveruser, mailserverpasswd)
    # Send the email - real from, real to, extra headers and content ...
    s.sendmail(senderEmail, To_mail, msg.as_string())
    s.close()
    print("Email to %s sent." % To_mail)


class SUPERSID_PLOT():

    def m2hm(self, x, i):
        """Small function to format the time on horizontal axis, minor ticks"""
        t = matplotlib.dates.num2date(x)
        h = t.hour
        m = t.minute
        # only for odd hours
        return '%(h)02d:%(m)02d' % {'h': h, 'm': m} if h % 2 == 1 else ''

    def m2yyyymmdd(self, x, i):
        """Small function to format the date on horizontal axis, major ticks"""
        t = matplotlib.dates.num2date(x)
        y = t.year
        m = t.month
        d = t.day
        return '%(y)04d-%(m)02d-%(d)02d --' % {'y': y, 'm': m, 'd': d}

    def get_station_color(self, config, call_sign):
        if config:
            for station in config.stations:
                if call_sign == station['call_sign']:
                    return station['color'] or None
        return None

    def plot_filelist(self, filelist, showPlot=True, eMail=None, pdf=None,
                      web=False, config=None):
        """Read the files in the filelist parameters.

        Each data are combine in one plot.
        That plot can be displayed or not (showPlot),
        sent by email (eMail provided), saved as pdf (pdf provided).
        Connection for the given days to NOAA website is possible (web) in
        order to draw vetical lines for XRA data.
        """
        emailText = []

        def Tstamp(HHMM):
            return datetime.datetime(
                year=int(day[:4]),
                month=int(day[4:6]),
                day=int(day[6:8]),
                hour=int(HHMM[:2]),
                minute=int(HHMM[2:]))

        # Sunrise and sunset shade
        # sun_rise = 6.0
        # sun_set  = 18.0
        # plt.axvspan(0.0, sun_rise, facecolor='blue', alpha=0.2)
        # plt.axvspan(sun_set, 24.0, facecolor='blue', alpha=0.2)

        if type(filelist) is str:
            # file1,file2,...,fileN given as script argument
            if filelist.find(',') >= 0:
                filelist = filelist.split(",")
            else:
                filelist = (filelist, )
        filenames = []
        # use glob for one or more files
        filenames.extend([a for a in itertools.chain.from_iterable(
                [glob.glob(os.path.expanduser(f)) for f in filelist])])
        # print(filenames)

        # plot's figure and axis
        fig = plt.figure()
        current_axes = fig.gca()
        current_axes.xaxis.set_minor_locator(matplotlib.dates.HourLocator())
        current_axes.xaxis.set_major_locator(matplotlib.dates.DayLocator())
        current_axes.xaxis.set_major_formatter(ff(self.m2yyyymmdd))
        current_axes.xaxis.set_minor_formatter(ff(self.m2hm))
        current_axes.set_xlabel("UTC Time")
        current_axes.set_ylabel("Signal Strength")

        # Get data from files
        maxData, data_length = -1, -1  # impossible values

        # flare list from NOAA
        XRAlist = []

        # date of NOAA's pages already retrieved, prevent multiple fetch
        daysList = set()

        # list of file names (w/o path and extension) as figure's title
        figTitle = []

        # one color per station
        colorList = "brgcmy"
        colorStation = {}
        colorIdx = 0

        clock()
        for filename in sorted(filenames):
            figTitle.append(os.path.basename(filename)[:-4])    # .csv assumed
            sFile = SidFile(filename)
            for station in sFile.stations:
                # Does this station already have a color? if not, reserve one
                if station not in colorStation:
                    colorStation[station] = \
                        self.get_station_color(config, station)
                    if (colorStation[station] is None):
                        # format like 'b-'
                        colorStation[station] = \
                            colorList[colorIdx % len(colorList)] + '-'
                        colorIdx += 1
                # Add points to the plot
                plt.plot_date(sFile.timestamp,
                              sFile.get_station_data(station),
                              colorStation[station],
                              label=station)
                # Extra housekeeping

                # maxData will be used later to put the XRA labels up
                maxData = max(max(sFile.get_station_data(station)), maxData)

                msg = "[{}] {} points plotted after reading {}".format(
                    station,
                    len(sFile.get_station_data(station)),
                    os.path.basename(filename))
                print(msg)
                emailText.append(msg)

                if web and sFile.startTime not in daysList:
                    # get the XRA data from NOAA website to draw corresponding
                    # lines on the plot
                    # fetch that day's flares on NOAA as not previously
                    # accessed
                    day = sFile.sid_params["utc_starttime"][:10].replace("-", "")
                    # NOAA_URL = 'http://www.swpc.noaa.gov/ftpdir/warehouse/%s/%s_events/%sevents.txt' % (day[:4], day[:4], day)
                    # ftp://ftp.swpc.noaa.gov/pub/indices/events/20141030events.txt
                    NOAA_URL = 'ftp://ftp.swpc.noaa.gov/pub/indices/events/%sevents.txt' % (day)
                    response = None
                    try:
                        response = urllib.request.urlopen(NOAA_URL)
                    except urllib.error.HTTPError as err:
                        print(err, "\n", NOAA_URL)

                    # save temporarly current number of XRA events in memory
                    lastXRAlen = len(XRAlist)
                    if response:
                        for webline in response.read().splitlines():
                            if sys.version[0] >= '3':
                                # cast bytes to str
                                webline = str(webline, 'utf-8')
                            fields = webline.split()
                            if ((len(fields) >= 9) and
                                    (not fields[0].startswith("#"))):
                                if fields[1] == '+':
                                    fields.remove('+')

                                # maybe other event types could be of interrest
                                if fields[6] in ('XRA', ):
                                    msg = fields[0] + " "   # eventName
                                    msg += fields[1] + " "  # BeginTime
                                    msg += fields[2] + " "  # MaxTime
                                    msg += fields[3] + " "  # EndTime
                                    msg += fields[8]        # Particulars
                                    emailText.append(msg)
                                    print(msg)
                                    try:
                                        # 'try' necessary as few occurences of
                                        # --:-- instead of HH:MM exist
                                        btime = Tstamp(fields[1])
                                    except Exception:
                                        pass
                                    try:
                                        mtime = Tstamp(fields[2])
                                    except Exception:
                                        mtime = btime
                                    try:
                                        etime = Tstamp(fields[3])
                                    except Exception:
                                        etime = mtime
                                    XRAlist.append((
                                        fields[0],
                                        btime,
                                        mtime,
                                        etime,
                                        fields[8]))  # as a tuple

                    msg = str(len(XRAlist) - lastXRAlen) \
                        + " XRA events recorded by NOAA on " + day
                    emailText.append(msg)
                    print(msg)
                # keep track of the days
                daysList.add(sFile.startTime)

        print("All files read in", clock(), "sec.")

        if web:  # add the lines marking the retrieved flares from NOAA
            alternate = 0
            for eventName, BeginTime, MaxTime, EndTime, Particulars in XRAlist:
                plt.vlines([BeginTime, MaxTime, EndTime], 0, maxData,
                           color=['g', 'r', 'y'], linestyles='dotted')
                plt.text(MaxTime, alternate * maxData, Particulars,
                         horizontalalignment='center',
                         bbox={'facecolor': 'w', 'alpha': 0.5, 'fill': True})
                alternate = 0 if alternate == 1 else 1

        # plot/page size / figure size with standard paper

        # exchange width and height to get landscape orientation
        height, width = PAPER_SIZE[config.get("paper_size", "")]

        if len(daysList) == 1:
            fig.set_size_inches(width, height, forward=True)
        else:
            # allow PDF poster for many days (monthly graph)
            # --> use Adobe PDF Reader --> Print --> Poster mode
            fig.set_size_inches(
                (width) * (len(daysList)/2.0), (height) / 2.0, forward=True)
        fig.subplots_adjust(bottom=0.08, left=0.05, right=0.98, top=0.95)

        # some cosmetics on the figure
        for label in current_axes.xaxis.get_majorticklabels():
            label.set_fontsize(8)
            label.set_rotation(30)  # 'vertical')
            # label.set_horizontalalignment='left'

        for label in current_axes.xaxis.get_minorticklabels():
            label.set_fontsize(12 if len(daysList) == 1 else 8)

        fig.suptitle(", ".join(figTitle))

        plt.legend()
        plt.tight_layout()

        # actions requested by user
        if pdf or eMail:
            # in case option eMail is given
            plt.savefig(pdf or 'Image.pdf')
        if showPlot:
            plt.show()
        if eMail:
            sendMail(config, eMail, "\n".join(emailText), pdf or 'Image.pdf')


# -----------------------------------------------------------------------------
"""
For running supersid_plot.py directly from command line
"""


def do_main(filelist, showPlot=True, eMail=None, pdf=None,
            web=False, config=None):
    ssp = SUPERSID_PLOT()
    ssp.plot_filelist(filelist, showPlot, eMail, pdf, web, config)


if __name__ == '__main__':
    filenames = ""
    parser = argparse.ArgumentParser(
        description="""Usage:   supersid_plot.py  filename.csv\n
     Usage:   supersid_plot.py  "filename1.csv,filename2.csv,filename3.csv"\n
     Usage:   supersid_plot.py  "filename*.csv"\n
     Note: " are optional on Windows, mandatory on *nix\n
     Other options:  supersid_plot.py -h\n""")
    parser.add_argument(
        "-c", "--config",
        dest="cfg_filename",
        type=exist_file,
        default=CONFIG_FILE_NAME,
        help="Supersid configuration file")
    parser.add_argument(
        "-f", "--file",
        dest="filename",
        help="Read SID and SuperSID csv file(s). Wildcards accepted.",
        metavar="FILE|FILE*.csv")
    parser.add_argument(
        "-p", "--pdf",
        dest="pdffilename",
        help="Write the plot in a PDF file.",
        metavar="filename.PDF")
    parser.add_argument(
        "-e", "--email",
        dest="email", nargs="?",
        help="sends PDF file to the given email",
        metavar="address@server.ex")
    parser.add_argument(
        "-n", "--noplot",
        action="store_false",
        dest="showPlot",
        default=True,
        help="do not display the plot. Usefull in batch mode.")
    parser.add_argument(
        "-w", "--web",
        action="store_true",
        dest="webData",
        default=False,
        help="Add information on flares (XRA) from NOAA website.")
    parser.add_argument(
        "-y", "--yesterday",
        action="store_true",
        dest="askYesterday",
        default=False,
        help="Yesterday's date is used for the file name.")
    parser.add_argument(
        "-t", "--today",
        action="store_true",
        dest="askToday",
        default=False,
        help="Today's date is used for the file name.")
    parser.add_argument(
        "-i", "--site_id",
        dest="site_id",
        help="Site ID to use in the file name",
        metavar="SITE_ID")
    parser.add_argument(
        "-s", "--station",
        dest="station_id",
        help="Station ID to use in the file name or * for all",
        metavar="STAID")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        dest="verbose",
        default=False,
        help="Print more messages.")
    parser.add_argument(
        'file_list',
        metavar='file.csv',
        type=exist_file,
        nargs='*',
        help='file(s) to be plotted')
    args = parser.parse_args()

    # read the configuration file or exit
    config = readConfig(args.cfg_filename)
    if args.verbose:
        printConfig(config)

    if args.filename is None:  # no --file option specified
        if len(args.file_list) > 0:
            # last non options arguments are assumed to be a list of file names
            filenames = ",".join(unk)
        else:
            # try building the file name from given options
            # or found in the provided .cfg file
            Now = datetime.datetime.now()  # by default today
            if args.askYesterday:
                Now -= datetime.timedelta(days=1)
            # stations can be given as a comma delimited string
            # SuperSID id is unique
            lstFileNames = []
            data_path = config.get("data_path")
            if args.station_id is None:  # file name like supersid file format
                lstFileNames.append("%s/%s_%04d-%02d-%02d.csv" %
                                    (data_path,
                                     args.site_id or config["site_name"],
                                     Now.year, Now.month, Now.day))
            else:
                if args.station_id == '*':
                    # all possible stations from .cfg file
                    # - must be '*' on the command line!
                    strStations = ",".join([s["call_sign"]
                                            for s in config.stations])
                else:  # only given stations - can be a comma delimited list
                    strStations = args.station_id
                # build the list of sid format file names
                for station in strStations.split(","):
                    lstFileNames.append("%s/%s_%s_%04d-%02d-%02d.csv" %
                                        (data_path,
                                         args.site_id or config["site_name"],
                                         station,
                                         Now.year, Now.month, Now.day))
            filenames = ",".join(lstFileNames)
    else:
        filenames = args.filename

    if args.verbose:
        print("List of files:", filenames)

    if filenames:
        do_main(filenames,
                showPlot=args.showPlot,
                eMail=args.email,
                pdf=args.pdffilename,
                web=args.webData,
                config=config)
    else:
        parser.error("No file to plot found.")
