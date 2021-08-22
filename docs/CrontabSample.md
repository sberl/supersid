# This is the line to add to crontab file (crontab -e command)
$ It will upload files to stanford via ftp at 5:05pm every day
# m h  dom mon dow   command
5 17 * * * python3 /home/steve/supersid/supersid/ftp_to_Standford.py -y -c /home/steve/supersid/Config/supersid.cfg
