# Copyright (c) 2018 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging
import smtplib
from email.mime.text import MIMEText
from email import MIMEMultipart

from steelscript.appfwk.apps.alerting.senders.base import BaseSender
from steelscript.appfwk.apps.alerting.datastructures import AlertLevels

logger = logging.getLogger(__name__)


class SMTPSender(BaseSender):
    """Base class for SMTP email notifications.

    Subclass this to override defaults and configuration
    """
    # base values for all traps of this class
    mail_host = '127.0.0.1'
    port = 25
    use_tls = False
    do_auth = False
    username = 'steelscript'
    password = 'steelscript'
    text_type = 'plain'
    from_addr = ''
    dest_addrs = []
    subject_text = 'SteelScript Alert'
    debug_level = 0

    def process_alert(self, alert):
        """Override class values with kwargs from destination in alert.

        Only predefined attributes can be overwritten, extra or unknown
        values will raise an AttributeError.
        """
        missing = []
        for k, v in (alert.options or {}).iteritems():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                missing.append(k)

        if missing:
            raise AttributeError('Invalid destination keyword arguments: %s '
                                 'for Alert %s' % (missing, alert))

    def long_form_alert(self, alert):
        msg = []
        fmt = '{0:15}: {1}'
        msg.append(fmt.format('ID', alert.id))
        msg.append(fmt.format('EventID', alert.event.eventid))
        msg.append(fmt.format('Timestamp', alert.timestamp))
        msg.append(fmt.format('Level', alert.level))
        msg.append('Message:')
        msg.append(alert.message)
        return '\n'.join(msg)

    def send(self, alert):
        self.process_alert(alert)
        try:
            msg = MIMEMultipart.MIMEMultipart()
            msg['Subject'] = self.subject_text
            msg['From'] = self.from_addr
            msg['To'] = ','.join(self.dest_addrs)
            msg.attach(MIMEText(self.long_form_alert(alert), self.text_type))

            s = smtplib.SMTP(self.mail_host, self.port)
            s.set_debuglevel(self.debug_level)
            s.ehlo()
            if self.use_tls:
                s.starttls()
            if self.do_auth:
                s.login(self.username, self.password)
            try:
                s.sendmail(self.from_addr, self.dest_addrs, msg.as_string())
            finally:
                s.quit()
        except Exception as e:
            logger.error("SMTP sender failed to send with: {}"
                         "".format(e.message))
            raise e
